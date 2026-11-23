# -*- coding: utf-8 -*-

from agent_app.audit import schemas
from agent_app.audit.schemas import Record
from agent_app.audit.schemas import Policy
from agent_app.audit.schemas import ToolCall

import inspect

import pytest
from pydantic import ValidationError


def get_models() -> list[type[Record]]:
    return [
        obj
        for _, obj in inspect.getmembers(schemas, inspect.isclass)
        if issubclass(obj, Record) and obj is not Record
    ]


def test_every_field_is_described():
    """The LLM reads the field descriptions as the tools' output schema."""
    models = get_models()
    assert len(models) == 18
    for model in models:
        for name, field in model.model_fields.items():
            assert field.description, f"{model.__name__}.{name}"


def test_unknown_field_is_rejected():
    """
    A record with a field no model declares does not load, so a ground-truth
    label cannot ride along into a tool result.
    """
    row = {
        "policy_id": "P-01",
        "category": "SCOPE_VIOLATION",
        "title": "Least privilege",
        "rule": "Only allowed tools.",
    }
    assert Policy.model_validate(row).policy_id == "P-01"
    with pytest.raises(ValidationError, match="risky"):
        Policy.model_validate({**row, "risky": True})
    for model in get_models():
        assert model.model_config["extra"] == "forbid"


def test_tool_call_approval_is_optional(audit_sample):
    refund = audit_sample["sessions"][1]["tool_calls"]
    assert ToolCall.model_validate(refund[0]).approval is None
    assert ToolCall.model_validate(refund[1]).approval.change_ticket == "CHG-1"


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.audit.schemas",
        preview=False,
    )
