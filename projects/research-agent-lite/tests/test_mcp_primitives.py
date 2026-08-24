import asyncio
import json

import pytest
from mcp import Client

from app.mcp_contracts import MCPPrimitive, PRIMITIVE_POLICIES, recommend_primitive
from app.mcp_research_server import mcp


def test_v61_primitive_policy_separates_model_application_and_user_control() -> None:
    assert recommend_primitive(executes_action=True) is MCPPrimitive.TOOL
    assert recommend_primitive(addressed_context=True) is MCPPrimitive.RESOURCE
    assert recommend_primitive(reusable_user_workflow=True) is MCPPrimitive.PROMPT

    assert PRIMITIVE_POLICIES[MCPPrimitive.TOOL].control_owner.value == "model"
    assert PRIMITIVE_POLICIES[MCPPrimitive.RESOURCE].control_owner.value == "application"
    assert PRIMITIVE_POLICIES[MCPPrimitive.PROMPT].control_owner.value == "user"

    with pytest.raises(ValueError, match="exactly one control intent"):
        recommend_primitive(executes_action=True, addressed_context=True)


def test_v62_in_process_client_discovers_real_mcp_capabilities() -> None:
    async def scenario() -> None:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            prompts = await client.list_prompts()

            assert client.protocol_version
            assert client.server_capabilities.tools is not None
            assert client.server_capabilities.resources is not None
            assert client.server_capabilities.prompts is not None
            assert {tool.name for tool in tools.tools} == {"search_papers"}
            assert {str(resource.uri) for resource in resources.resources} == {"research://catalog"}
            assert {template.uri_template for template in templates.resource_templates} == {
                "research://paper/{paper_id}"
            }
            assert {prompt.name for prompt in prompts.prompts} == {"compare_papers"}

            search = next(tool for tool in tools.tools if tool.name == "search_papers")
            assert search.input_schema["type"] == "object"
            assert "query" in search.input_schema["properties"]

    asyncio.run(scenario())


def test_v62_client_calls_tool_reads_resource_and_renders_prompt() -> None:
    async def scenario() -> None:
        async with Client(mcp) as client:
            tool_result = await client.call_tool(
                "search_papers",
                {"query": "domain wall disorder", "limit": 2},
            )
            assert tool_result.is_error is False
            assert tool_result.content
            assert "rfim-domain-wall" in tool_result.content[0].text

            resource_result = await client.read_resource("research://catalog")
            assert resource_result.contents
            catalog_text = resource_result.contents[0].text
            catalog = json.loads(catalog_text)
            assert catalog["count"] == 3

            paper_result = await client.read_resource("research://paper/sliding-ferroelectric")
            paper = json.loads(paper_result.contents[0].text)
            assert paper["id"] == "sliding-ferroelectric"

            prompt_result = await client.get_prompt(
                "compare_papers",
                {"left_id": "rfim-domain-wall", "right_id": "sliding-ferroelectric"},
            )
            assert prompt_result.messages
            assert "research://paper/rfim-domain-wall" in prompt_result.messages[0].content.text

    asyncio.run(scenario())
