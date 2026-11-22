# -*- coding: utf-8 -*-

from agent_app.devtools.audit_data import sync_audit_data
from agent_app.devtools.audit_data import main

import pytest

from agent_app.paths import path_enum


def test_sync_audit_data(dir_audit_source, tmp_path):
    """
    The five input files arrive, the labels do not, and a second run writes
    the same bytes.
    """
    assert (dir_audit_source / "labels" / "session_labels.jsonl").exists()
    dir_target = tmp_path / "nested" / "data"
    store = sync_audit_data(dir_audit_source, dir_target)
    assert list(store.sessions) == ["ses_001", "ses_002", "ses_003"]
    names = sorted(path.name for path in dir_target.iterdir())
    assert names == [
        "agents.jsonl",
        "org.json",
        "policy.json",
        "tools.json",
        "traces.jsonl.gz",
    ]
    first = (dir_target / "traces.jsonl.gz").read_bytes()
    sync_audit_data(dir_audit_source, dir_target)
    assert (dir_target / "traces.jsonl.gz").read_bytes() == first


def test_sync_audit_data_drop_intent(dir_audit_source, tmp_path):
    """Every call loses its intent and nothing else."""
    kept = sync_audit_data(dir_audit_source, tmp_path / "kept")
    dropped = sync_audit_data(dir_audit_source, tmp_path / "dropped", drop_intent=True)
    assert list(dropped.sessions) == list(kept.sessions)
    for session_id, session in kept.sessions.items():
        calls = dropped.sessions[session_id].tool_calls
        assert [call.intent for call in calls] == [""] * len(calls)
        assert [call.arguments for call in calls] == [
            call.arguments for call in session.tool_calls
        ]
        assert any(call.intent for call in session.tool_calls)


def test_sync_audit_data_missing_source(tmp_path):
    """Nothing is written when the source is incomplete."""
    dir_source = tmp_path / "source"
    dir_source.mkdir()
    (dir_source / "policy.json").write_text("[]")
    dir_target = tmp_path / "data"
    with pytest.raises(FileNotFoundError, match="has no org.json, tools.json"):
        sync_audit_data(dir_source, dir_target)
    assert not dir_target.exists()


def test_main(dir_audit_source, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(path_enum, "dir_audit_data", tmp_path / "data")
    main(["--source", str(dir_audit_source)])
    assert (tmp_path / "data" / "traces.jsonl.gz").exists()
    out = capsys.readouterr().out
    assert "2 agents, 3 sessions, 5 tool calls" in out


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.devtools.audit_data",
        preview=False,
    )
