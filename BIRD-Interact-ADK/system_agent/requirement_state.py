"""Validated, session-scoped requirement updates. No environment tools or IO."""

from __future__ import annotations

import copy
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

STATE_KEY = "requirement_state"


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^r[1-9][0-9]*$")
    requirement: str = Field(min_length=1, max_length=2000)
    category: Literal["schema", "knowledge", "user_semantics", "unknown"]
    status: Literal["unresolved", "candidate", "conflict", "resolved"]
    value: str = Field(max_length=12000)
    priority: StrictInt = Field(ge=0, le=3)

    @model_validator(mode="after")
    def check_status(self):
        if not self.requirement.strip():
            raise ValueError("requirement must not be blank")
        if (self.status == "resolved") != (self.priority == 0):
            raise ValueError("resolved requires priority 0; other statuses require 1..3")
        if self.status != "unresolved" and not self.value.strip():
            raise ValueError("candidate/conflict/resolved requires a value")
        if self.status == "conflict" and "|" not in self.value:
            raise ValueError("conflict must retain conflicting values separated by |")
        return self


class Change(Requirement):
    # Transport/audit explanation, not a sixth requirement field.
    reason: str = Field(min_length=1, max_length=4000)


class Update(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    upserts: list[Change] = Field(max_length=200)


def empty_state(task_id: str) -> dict:
    return {"task_id": task_id, "revision": 0, "requirements": []}


def normalized(text: str) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).casefold())


def apply_update(current: dict, payload: dict, task_id: str) -> tuple[dict, list[dict]]:
    """Validate an entire patch before returning a new snapshot. Never mutate input.

    No deletion/renaming: explicit constraints survive partial patches. Meaning-level
    deduplication and evidence sufficiency remain model responsibilities.
    """
    patch = Update.model_validate(payload)
    if current["task_id"] != task_id:
        raise ValueError("requirement state belongs to another task")
    result = copy.deepcopy(current)
    records = {r["id"]: Requirement.model_validate(r).model_dump() for r in result["requirements"]}
    seen = set()
    audit = []
    for change in patch.upserts:
        if change.id in seen:
            raise ValueError("duplicate id in patch")
        seen.add(change.id)
        item = change.model_dump(exclude={"reason"})
        previous = records.get(change.id)
        if previous and previous["requirement"] != item["requirement"]:
            raise ValueError("reuse the original requirement text and id; do not rename")
        if previous != item:
            audit.append({"id": change.id, "before": previous, "after": item, "reason": change.reason})
        records[change.id] = item
    names = [normalized(r["requirement"]) for r in records.values()]
    if len(names) != len(set(names)):
        raise ValueError("duplicate requirement; update its existing id")
    if not records:
        raise ValueError("initialization must record all task constraints, including explicit ones")
    result["requirements"] = list(records.values())
    if audit:
        result["revision"] += 1
    return result, audit
