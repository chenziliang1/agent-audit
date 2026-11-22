# -*- coding: utf-8 -*-

from agent_app.devtools.evaluation import QUESTION
from agent_app.devtools.evaluation import Fallback
from agent_app.devtools.evaluation import ModelCallLog
from agent_app.devtools.evaluation import SessionRun
from agent_app.devtools.evaluation import append_run
from agent_app.devtools.evaluation import audit_session
from agent_app.devtools.evaluation import pick_sessions
from agent_app.devtools.evaluation import read_runs
from agent_app.devtools.evaluation import run_evaluation
from agent_app.devtools.evaluation import summarize
from agent_app.devtools.evaluation import to_prediction
from agent_app.devtools.evaluation import write_predictions

import json

import pytest

from agent_app.audit.audit_agent import SessionVerdict

FALLBACK_EVENT = {
    "type": "content_block_start",
    "content_block": {
        "type": "fallback",
        "from": {"model": "acme-widget-model-2"},
        "to": {"model": "acme-widget-model-1"},
        "trigger": {"type": "refusal", "category": "cyber"},
    },
}


def clean_verdict(session_id: str) -> SessionVerdict:
    return SessionVerdict(
        session_id=session_id,
        risky=False,
        severity="none",
        categories=[],
        policy_ids=[],
        flagged_call_ids=[],
        rationale="Every widget order stayed within the limit.",
    )


def risky_verdict(session_id: str) -> SessionVerdict:
    return SessionVerdict(
        session_id=session_id,
        risky=True,
        severity="high",
        categories=["SCOPE_VIOLATION"],
        policy_ids=["P-01"],
        flagged_call_ids=["call_1"],
        rationale="The helper ran a shell command it is not allowed to run.",
    )


def make_run(session_id: str, **kwargs) -> SessionRun:
    values = dict(
        session_id=session_id,
        seconds=1.0,
        stop_reason="end_turn",
        error=None,
        usage={},
        models=[],
        fallbacks=[],
        verdicts=[],
    )
    values.update(kwargs)
    return SessionRun(**values)


class FakeModel:
    def format_chunk(self, event):
        return {"formatted": event}


class FakeMetrics:
    def __init__(self, usage):
        self.accumulated_usage = usage


class FakeResult:
    def __init__(self, stop_reason, usage):
        self.stop_reason = stop_reason
        self.metrics = FakeMetrics(usage)


class FakeAgent:
    """
    Stands in for a Strands agent: streams ``events`` through its model,
    records ``verdict``, and answers with ``stop_reason``.
    """

    def __init__(self, log, verdict=None, events=(), stop_reason="end_turn"):
        self.model = FakeModel()
        self.log = log
        self.verdict = verdict
        self.events = events
        self.stop_reason = stop_reason
        self.prompts = []
        self.cleaned = False
        self.fail_on_call = False
        self.fail_on_cleanup = False

    def __call__(self, prompt):
        self.prompts.append(prompt)
        formatted = [self.model.format_chunk(event) for event in self.events]
        assert formatted == [{"formatted": event} for event in self.events]
        if self.fail_on_call:
            raise ValueError("the widget press jammed")
        if self.verdict is not None:
            self.log.record(self.verdict)
        usage = {"inputTokens": 1_000_000, "outputTokens": 100_000, "note": "x"}
        return FakeResult(self.stop_reason, usage)

    def cleanup(self):
        self.cleaned = True
        if self.fail_on_cleanup:
            raise RuntimeError("the connection was already closed")


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 2.5
        return self.now


class TestSessionRun:
    def test_verdict(self):
        """Only a verdict on the session that was asked about counts."""
        run = make_run(
            "ses_widget_1",
            verdicts=[clean_verdict("ses_widget_9"), risky_verdict("ses_widget_1")],
        )
        assert run.verdict.risky is True
        assert run.refused is False
        assert (
            make_run("ses_widget_1", verdicts=[clean_verdict("ses_widget_9")]).verdict
            is None
        )
        assert make_run("ses_widget_1").verdict is None

    def test_no_verdict_when_refused_or_failed(self):
        """What was recorded before the model stopped is not a verdict."""
        verdicts = [risky_verdict("ses_widget_1")]
        refused = make_run("ses_widget_1", stop_reason="refusal", verdicts=verdicts)
        assert refused.refused is True
        assert refused.verdict is None
        failed = make_run(
            "ses_widget_1", stop_reason=None, error="boom", verdicts=verdicts
        )
        assert failed.verdict is None

    def test_cost_usd(self):
        run = make_run(
            "ses_widget_1",
            usage={
                "inputTokens": 1_000_000,
                "outputTokens": 100_000,
                "cacheWriteInputTokens": 200_000,
                "cacheReadInputTokens": 1_000_000,
                "totalTokens": 99,
            },
        )
        assert run.cost_usd == pytest.approx(2.0 + 1.0 + 0.5 + 0.1)
        assert make_run("ses_widget_1").cost_usd == 0.0


class TestModelCallLog:
    def test_read(self):
        log = ModelCallLog()
        log.read({"type": "message_start", "message": {"model": "acme-widget-model-2"}})
        log.read(FALLBACK_EVENT)
        log.read({"type": "message_start", "message": {"model": "acme-widget-model-1"}})
        log.read({"type": "content_block_start", "content_block": {"type": "text"}})
        log.read({"type": "content_block_delta"})
        assert log.models == ["acme-widget-model-2", "acme-widget-model-1"]
        assert log.fallbacks == [
            Fallback(
                from_model="acme-widget-model-2",
                to_model="acme-widget-model-1",
                trigger="refusal",
                category="cyber",
            )
        ]

    def test_read_fallback_without_trigger(self):
        log = ModelCallLog()
        block = dict(FALLBACK_EVENT["content_block"], trigger=None)
        log.read({"type": "content_block_start", "content_block": block})
        assert log.fallbacks[0].trigger == "unknown"
        assert log.fallbacks[0].category is None

    def test_read_client_side_fallback(self):
        """A refused call followed by another call is the runtime's own retry."""
        log = ModelCallLog()
        log.read({"type": "message_stop", "message": {"stop_reason": "refusal"}})
        log.read({"type": "message_start", "message": {"model": "acme-widget-model-2"}})
        log.read({"type": "message_stop", "message": {"stop_reason": "tool_use"}})
        log.read({"type": "message_start", "message": {"model": "acme-widget-model-2"}})
        log.read({"type": "message_stop", "message": {"stop_reason": "refusal"}})
        log.read({"type": "message_start", "message": {"model": "acme-widget-model-1"}})
        log.read({"type": "message_stop", "message": {"stop_reason": "refusal"}})
        assert log.models == [
            "acme-widget-model-2",
            "acme-widget-model-2",
            "acme-widget-model-1",
        ]
        assert log.fallbacks == [
            Fallback(
                from_model="acme-widget-model-2",
                to_model="acme-widget-model-1",
                trigger="refusal",
                client_side=True,
            )
        ]

    def test_watch(self):
        """The model formats every event as before, and the log reads it."""
        model = FakeModel()
        log = ModelCallLog()
        log.watch(model)
        event = {"type": "message_start", "message": {"model": "acme-widget-model-1"}}
        assert model.format_chunk(event) == {"formatted": event}
        assert log.models == ["acme-widget-model-1"]


def test_pick_sessions():
    session_ids = [f"ses_widget_{i:02d}" for i in (5, 3, 9, 1, 7, 2, 8)]
    assert pick_sessions(session_ids, None, seed=0) == session_ids
    picked = pick_sessions(session_ids, 3, seed=0)
    assert len(picked) == 3
    # The dataset's order is kept, and the same seed picks the same sessions.
    assert picked == [session_id for session_id in session_ids if session_id in picked]
    assert pick_sessions(list(reversed(session_ids)), 3, seed=0) == list(
        reversed(picked)
    )
    assert pick_sessions(session_ids, 7, seed=1) == session_ids
    with pytest.raises(ValueError, match="cannot sample 8 of 7 sessions"):
        pick_sessions(session_ids, 8, seed=0)


class TestAuditSession:
    def test_answer(self):
        agents = []

        def make_agent(log):
            agent = FakeAgent(
                log,
                verdict=risky_verdict("ses_widget_1"),
                events=[
                    {
                        "type": "message_start",
                        "message": {"model": "acme-widget-model-2"},
                    },
                    FALLBACK_EVENT,
                ],
            )
            agents.append(agent)
            return agent

        run = audit_session("ses_widget_1", make_agent, clock=FakeClock())
        assert agents[0].prompts == [QUESTION.format(session_id="ses_widget_1")]
        assert agents[0].cleaned is True
        assert run.session_id == "ses_widget_1"
        assert run.seconds == 2.5
        assert run.stop_reason == "end_turn"
        assert run.error is None
        assert run.usage == {"inputTokens": 1_000_000, "outputTokens": 100_000}
        assert run.models == ["acme-widget-model-2"]
        assert run.fallbacks[0].to_model == "acme-widget-model-1"
        assert run.verdict.flagged_call_ids == ["call_1"]

    def test_agent_fails(self):
        """A failure is the run's error, and the agent is still closed."""
        agents = []

        def make_agent(log):
            agent = FakeAgent(log)
            agent.fail_on_call = True
            agent.fail_on_cleanup = True
            agents.append(agent)
            return agent

        run = audit_session("ses_widget_1", make_agent)
        assert run.error == "ValueError: the widget press jammed"
        assert run.stop_reason is None
        assert run.verdict is None
        assert agents[0].cleaned is True

    def test_agent_cannot_be_built(self):
        def make_agent(log):
            raise ConnectionError("no widget server")

        run = audit_session("ses_widget_1", make_agent)
        assert run.error == "ConnectionError: no widget server"
        assert run.models == []


def test_to_prediction():
    assert to_prediction(make_run("ses_widget_1")) is None
    run = make_run("ses_widget_1", verdicts=[risky_verdict("ses_widget_1")])
    assert to_prediction(run) == {
        "session_id": "ses_widget_1",
        "risky": True,
        "flagged_call_ids": ["call_1"],
        "categories": ["SCOPE_VIOLATION"],
        "severity": "high",
    }


def test_read_runs_and_append_run(tmp_path):
    path = tmp_path / "runs.jsonl"
    assert read_runs(path) == {}
    append_run(path, make_run("ses_widget_1", stop_reason=None, error="boom"))
    append_run(path, make_run("ses_widget_2"))
    with open(path, "a") as f:
        f.write("\n")
    append_run(path, make_run("ses_widget_1", verdicts=[clean_verdict("ses_widget_1")]))
    runs = read_runs(path)
    assert list(runs) == ["ses_widget_1", "ses_widget_2"]
    # The later line replaced the failed run.
    assert runs["ses_widget_1"].error is None
    assert runs["ses_widget_1"].verdict.risky is False


class TestRunEvaluation:
    def test_resume(self, tmp_path):
        """Sessions already audited are skipped; a failed one is run again."""
        path = tmp_path / "runs.jsonl"
        append_run(path, make_run("ses_widget_1"))
        append_run(path, make_run("ses_widget_2", stop_reason=None, error="boom"))
        audited = []
        lines = []

        def audit(session_id):
            audited.append(session_id)
            return make_run(session_id, verdicts=[clean_verdict(session_id)])

        session_ids = ["ses_widget_1", "ses_widget_2", "ses_widget_3"]
        runs = run_evaluation(
            session_ids=session_ids,
            audit=audit,
            path_runs=path,
            workers=2,
            max_cost_usd=1.0,
            report=lines.append,
        )
        assert sorted(audited) == ["ses_widget_2", "ses_widget_3"]
        assert [run.session_id for run in runs] == session_ids
        assert [run.error for run in runs] == [None, None, None]
        assert lines[0] == "1 sessions already audited, 2 to go"
        assert lines[-1].startswith("2/2 audited, about $0.00 spent")
        assert list(read_runs(path)) == session_ids

    def test_cost_cap(self, tmp_path):
        """No session starts once the cap is reached."""
        path = tmp_path / "runs.jsonl"
        audited = []
        lines = []

        def audit(session_id):
            audited.append(session_id)
            return make_run(session_id, usage={"outputTokens": 100_000})

        session_ids = ["ses_widget_1", "ses_widget_2", "ses_widget_3"]
        runs = run_evaluation(
            session_ids=session_ids,
            audit=audit,
            path_runs=path,
            workers=1,
            max_cost_usd=1.5,
            report=lines.append,
        )
        assert audited == ["ses_widget_1", "ses_widget_2"]
        assert [run.session_id for run in runs] == ["ses_widget_1", "ses_widget_2"]
        assert lines[-1] == (
            "Stopped at the cost cap of $1.50: 1 sessions were not audited"
        )


def test_summarize():
    session_ids = [f"ses_widget_{i}" for i in range(1, 7)]
    fallback = Fallback(
        from_model="acme-widget-model-2",
        to_model="acme-widget-model-1",
        trigger="refusal",
        category="cyber",
    )
    runs = [
        make_run(
            "ses_widget_1",
            seconds=4.0,
            usage={"outputTokens": 100_000},
            models=["acme-widget-model-2", "acme-widget-model-2"],
            verdicts=[clean_verdict("ses_widget_1")],
        ),
        make_run(
            "ses_widget_2",
            seconds=8.0,
            models=["acme-widget-model-2", "acme-widget-model-1"],
            fallbacks=[fallback, fallback.model_copy(update={"client_side": True})],
            verdicts=[risky_verdict("ses_widget_2")],
        ),
        make_run("ses_widget_3", seconds=0.0, stop_reason="refusal"),
        make_run("ses_widget_4", seconds=0.0, stop_reason=None, error="boom"),
        make_run("ses_widget_5", seconds=0.0),
    ]
    assert summarize(session_ids, runs) == {
        "sessions_picked": 6,
        "sessions_audited": 5,
        "with_verdict": 2,
        "errors": 1,
        "refused": 1,
        "answered_without_verdict": 1,
        "sessions_with_fallback": 1,
        "fallback_reasons": {"refusal/cyber": 1, "refusal/cyber (client side)": 1},
        "model_calls_by_model": {"acme-widget-model-2": 3, "acme-widget-model-1": 1},
        "cost_usd_estimate": 1.0,
        "mean_seconds": 2.4,
    }
    assert summarize(session_ids, [])["mean_seconds"] == 0.0


def test_write_predictions(tmp_path):
    path = tmp_path / "predictions.jsonl"
    runs = [
        make_run("ses_widget_1", verdicts=[clean_verdict("ses_widget_1")]),
        make_run("ses_widget_2", stop_reason="refusal"),
        make_run("ses_widget_3", verdicts=[risky_verdict("ses_widget_3")]),
    ]
    assert write_predictions(runs, path) == 2
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["session_id"] for row in rows] == ["ses_widget_1", "ses_widget_3"]
    assert [row["risky"] for row in rows] == [False, True]


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.devtools.evaluation",
        preview=False,
    )
