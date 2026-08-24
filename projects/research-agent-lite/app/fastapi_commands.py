from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable

from fastapi import HTTPException, status


@dataclass(frozen=True)
class IdempotentCommandResult:
    payload: dict[str, Any]
    etag: str
    replayed: bool = False


@dataclass(frozen=True)
class _StoredCommand:
    fingerprint: str
    result: IdempotentCommandResult


class InMemoryIdempotencyStore:
    """Teaching idempotency registry for mutating HTTP commands.

    Keys are scoped by tenant + operation + Idempotency-Key. A retry with the
    same fingerprint replays the original response. Reusing the same key for a
    different command is a conflict.

    ``execute_once`` keeps lookup, execution and record creation in one critical
    section so concurrent retries in this single teaching process cannot both
    execute the command. Production needs durable shared storage with equivalent
    atomic reservation/create-if-absent semantics across all API replicas.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], _StoredCommand] = {}
        self._lock = RLock()

    def execute_once(
        self,
        *,
        tenant_id: str,
        operation: str,
        idempotency_key: str,
        fingerprint: str,
        execute: Callable[[], IdempotentCommandResult],
    ) -> IdempotentCommandResult:
        key = (tenant_id, operation, idempotency_key)
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key was already used for a different command",
                    )
                return IdempotentCommandResult(
                    payload=dict(existing.result.payload),
                    etag=existing.result.etag,
                    replayed=True,
                )

            result = execute()
            stored = IdempotentCommandResult(
                payload=dict(result.payload),
                etag=result.etag,
                replayed=False,
            )
            self._records[key] = _StoredCommand(
                fingerprint=fingerprint,
                result=stored,
            )
            return stored


def normalize_idempotency_key(raw: str) -> str:
    key = raw.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must not be blank",
        )
    if len(key) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key is too long",
        )
    return key


def etag_for_revision(revision: int) -> str:
    if revision < 1:
        raise ValueError("revision must be >= 1")
    return f'"{revision}"'


def parse_if_match(raw: str | None) -> int:
    """Parse the teaching API's strong ETag revision precondition.

    We intentionally require one exact strong ETag such as ``If-Match: "7"``.
    Wildcards, weak validators and ETag lists are outside this course baseline.
    """

    if raw is None:
        raise HTTPException(
            status_code=428,
            detail="If-Match is required for this mutating command",
        )

    value = raw.strip()
    if value.startswith("W/") or value == "*" or "," in value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='If-Match must be one strong revision ETag such as "7"',
        )
    if len(value) < 3 or not (value.startswith('"') and value.endswith('"')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='If-Match must be a quoted revision ETag such as "7"',
        )

    try:
        revision = int(value[1:-1])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='If-Match must contain an integer revision such as "7"',
        ) from exc
    if revision < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="If-Match revision must be >= 1",
        )
    return revision


def enforce_revision_precondition(*, current_revision: int, expected_revision: int) -> None:
    if current_revision != expected_revision:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=(
                f"Run revision changed: If-Match expected {expected_revision}, "
                f"current revision is {current_revision}"
            ),
        )


def command_fingerprint(
    *,
    operation: str,
    run_id: str,
    expected_revision: int,
    body: dict[str, Any] | None = None,
    target_id: str | None = None,
) -> str:
    canonical = json.dumps(
        {
            "operation": operation,
            "run_id": run_id,
            "target_id": target_id,
            "expected_revision": expected_revision,
            "body": body or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
