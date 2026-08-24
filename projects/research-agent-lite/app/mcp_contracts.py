from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MCPPrimitive(StrEnum):
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"


class ControlOwner(StrEnum):
    MODEL = "model"
    APPLICATION = "application"
    USER = "user"


@dataclass(frozen=True)
class PrimitivePolicy:
    primitive: MCPPrimitive
    control_owner: ControlOwner
    question: str
    typical_examples: tuple[str, ...]


PRIMITIVE_POLICIES: dict[MCPPrimitive, PrimitivePolicy] = {
    MCPPrimitive.TOOL: PrimitivePolicy(
        primitive=MCPPrimitive.TOOL,
        control_owner=ControlOwner.MODEL,
        question="Should the model be allowed to decide when to execute this capability?",
        typical_examples=("search papers", "create issue", "query database", "write file"),
    ),
    MCPPrimitive.RESOURCE: PrimitivePolicy(
        primitive=MCPPrimitive.RESOURCE,
        control_owner=ControlOwner.APPLICATION,
        question="Is this addressed context that the host/application should choose to load?",
        typical_examples=("paper metadata", "database schema", "project config", "document body"),
    ),
    MCPPrimitive.PROMPT: PrimitivePolicy(
        primitive=MCPPrimitive.PROMPT,
        control_owner=ControlOwner.USER,
        question="Is this a reusable workflow/template that a person should explicitly select?",
        typical_examples=("compare two papers", "review a draft", "prepare experiment summary"),
    ),
}


def recommend_primitive(
    *,
    executes_action: bool = False,
    addressed_context: bool = False,
    reusable_user_workflow: bool = False,
) -> MCPPrimitive:
    """A deliberately small exposure decision used by lesson 01.

    The inputs encode *who should control the capability*, not what language the
    implementation happens to use. Ambiguous capabilities should be split rather
    than exposed as one giant tool that mixes reading, acting and prompting.
    """

    selected = sum((executes_action, addressed_context, reusable_user_workflow))
    if selected != 1:
        raise ValueError("choose exactly one control intent; split ambiguous capabilities")
    if executes_action:
        return MCPPrimitive.TOOL
    if addressed_context:
        return MCPPrimitive.RESOURCE
    return MCPPrimitive.PROMPT
