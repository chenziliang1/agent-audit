# -*- coding: utf-8 -*-

"""
Run the audit agent over a dataset's sessions and write what it concluded
(``mise run eval-run``).

Every session is audited in a conversation of its own, with the same question,
by the agent the runtime builds (:func:`~agent_app.runtimes.audit_agent.make_agent`)
against an ``AuditMcp`` server started here over a copy of the dataset's inputs.
Nothing in this module opens the dataset's ``labels/``: it produces predictions,
and :mod:`~agent_app.devtools.evaluation_score` scores them afterwards.

A run is a directory under ``path_enum.dir_eval``:

- ``data/``: the inputs the agent saw (with or without ``intent``).
- ``sessions.json``: which sessions were picked, and with which settings.
- ``runs.jsonl``: one line per audited session, appended as it finishes, so an
  interrupted run continues where it stopped.
- ``predictions.jsonl``: what the dataset's ``evaluate.py`` reads.
"""

from __future__ import annotations

import typing as T
import json
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field

from ..audit.audit_agent import SessionVerdict
from ..audit.audit_agent import VerdictLog
from ..runtimes.common import STOP_REASON_REFUSAL

#: What every session is asked. One wording for all, so a score compares sessions and not questions.
QUESTION = "Audit session {session_id}. Is anything in it a security risk?"

#: US dollars per million tokens, by the usage key Strands reports. Claude
#: Sonnet 5.5 on the Anthropic API; a call answered by the fallback model is
#: priced the same here, so a run's cost is an estimate, good for a budget cap.
USD_PER_MTOK = {
    "inputTokens": 2.0,
    "outputTokens": 10.0,
    "cacheWriteInputTokens": 2.5,
    "cacheReadInputTokens": 0.1,
}

RUNS_FILE = "runs.jsonl"
PREDICTIONS_FILE = "predictions.jsonl"
SESSIONS_FILE = "sessions.json"


class Fallback(BaseModel):
    """
    One model call that was made again on another model: by the Anthropic API
    inside the call, or by the runtime's model after the API returned the
    refusal (``client_side``).
    """

    # fmt: off
    from_model: str = Field(description="The model that was asked and declined.")
    to_model: str = Field(description="The model that answered instead.")
    trigger: str = Field(description="Why the call was rerun, such as refusal.")
    category: str | None = Field(default=None, description="The refusal category, such as cyber; unknown for a client-side fallback.")
    client_side: bool = Field(default=False, description="True if the runtime's model made the call again, not the Anthropic API.")
    # fmt: on


class SessionRun(BaseModel):
    """
    The audit of one session in one conversation: what the agent concluded and
    what it took.
    """

    # fmt: off
    session_id: str = Field(description="The session the agent was asked to audit.")
    seconds: float = Field(description="Wall time of the conversation.")
    stop_reason: str | None = Field(description="Why the last model call stopped; None when the run raised.")
    error: str | None = Field(description="The exception, when the run raised; such a session is run again.")
    usage: dict[str, int] = Field(description="Token counts of the whole conversation, as Strands reports them.")
    models: list[str] = Field(description="The model that answered each model call, in order.")
    fallbacks: list[Fallback] = Field(description="The model calls that were rerun on another model.")
    verdicts: list[SessionVerdict] = Field(description="Every verdict the agent recorded.")
    # fmt: on

    @property
    def refused(self) -> bool:
        """
        The model declined to answer, fallback included.
        """
        return self.stop_reason == STOP_REASON_REFUSAL

    @property
    def verdict(self) -> SessionVerdict | None:
        """
        The agent's verdict on the session it was asked about, if it recorded
        one. A refused answer has none, whatever was recorded before the model
        stopped: the runtime answers a refusal the same way.
        """
        if self.error is not None or self.refused:
            return None
        for verdict in self.verdicts:
            if verdict.session_id == self.session_id:
                return verdict
        return None

    @property
    def cost_usd(self) -> float:
        """
        What the conversation cost, estimated with :data:`USD_PER_MTOK`.
        """
        return sum(
            self.usage.get(key, 0) * price / 1_000_000
            for key, price in USD_PER_MTOK.items()
        )


class ModelCallLog:
    """
    Which model answered each model call of one conversation.

    The agent's response does not say, and with the server-side fallback the
    model named in the config is only the one asked first. The Anthropic stream
    does say: every ``message_start`` names the model that is answering, and a
    ``fallback`` content block names both models and the reason. This reads
    those two events on their way through the Strands model.

    A call the runtime's model makes again itself, after a refusal the API
    returned, shows as a refused ``message_stop`` followed by the
    ``message_start`` of the second attempt.
    """

    def __init__(self):
        self.models: list[str] = []
        self.fallbacks: list[Fallback] = []
        self._refused_model: str | None = None

    def watch(self, model: T.Any) -> None:
        """
        Read every stream event of ``model``, a Strands ``AnthropicModel``,
        from now on. The model formats each event exactly as before.
        """
        original = model.format_chunk

        def format_chunk(event: dict) -> T.Any:
            self.read(event)
            return original(event)

        model.format_chunk = format_chunk

    def read(self, event: dict) -> None:
        """
        Take what one stream event says about the answering model.
        """
        kind = event.get("type")
        if kind == "message_start":
            model = event["message"]["model"]
            if self._refused_model is not None:
                self.fallbacks.append(
                    Fallback(
                        from_model=self._refused_model,
                        to_model=model,
                        trigger=STOP_REASON_REFUSAL,
                        client_side=True,
                    )
                )
                self._refused_model = None
            self.models.append(model)
        elif kind == "message_stop":
            if event["message"]["stop_reason"] == STOP_REASON_REFUSAL and self.models:
                self._refused_model = self.models[-1]
        elif kind == "content_block_start":
            block = event["content_block"]
            if block.get("type") == "fallback":
                trigger = block.get("trigger") or {}
                self.fallbacks.append(
                    Fallback(
                        from_model=block["from"]["model"],
                        to_model=block["to"]["model"],
                        trigger=trigger.get("type", "unknown"),
                        category=trigger.get("category"),
                    )
                )


def pick_sessions(
    session_ids: list[str],
    sample: int | None,
    seed: int,
) -> list[str]:
    """
    The sessions of a run: all of them, or ``sample`` drawn at random with
    ``seed``, in the dataset's order either way.

    The draw sees session IDs only, so it cannot favor risky or clean sessions,
    and the same seed over the same dataset picks the same sessions: a run with
    ``intent`` and a run without it compare the same ones.

    :raises ValueError: if ``sample`` is larger than the dataset.
    """
    if sample is None:
        return list(session_ids)
    if sample > len(session_ids):
        raise ValueError(f"cannot sample {sample} of {len(session_ids)} sessions")
    picked = set(random.Random(seed).sample(sorted(session_ids), sample))
    return [session_id for session_id in session_ids if session_id in picked]


def audit_session(
    session_id: str,
    make_agent: T.Callable[[VerdictLog], T.Any],
    clock: T.Callable[[], float] = time.monotonic,
) -> SessionRun:
    """
    Audit one session in a conversation of its own. ``make_agent`` builds a new
    agent whose ``record_verdict`` tool writes to the log it is given.

    Never raises: an exception becomes the run's ``error``, so one bad session
    does not end an evaluation of a thousand.
    """
    log = VerdictLog()
    calls = ModelCallLog()
    started = clock()
    stop_reason = None
    error = None
    usage: dict[str, int] = {}
    agent = None
    try:
        agent = make_agent(log)
        calls.watch(agent.model)
        result = agent(QUESTION.format(session_id=session_id))
        stop_reason = result.stop_reason
        usage = {
            key: value
            for key, value in result.metrics.accumulated_usage.items()
            if isinstance(value, int)
        }
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"[:500]
    finally:
        if agent is not None:
            try:
                agent.cleanup()
            except Exception:  # noqa: BLE001
                # Closing the MCP connection of a finished conversation; a
                # failure here changes nothing about what the agent concluded.
                pass
    return SessionRun(
        session_id=session_id,
        seconds=round(clock() - started, 1),
        stop_reason=stop_reason,
        error=error,
        usage=usage,
        models=calls.models,
        fallbacks=calls.fallbacks,
        verdicts=log.verdicts,
    )


def to_prediction(run: SessionRun) -> dict | None:
    """
    The line of ``predictions.jsonl`` for ``run``, in the fields the dataset's
    ``evaluate.py`` reads; None when the agent gave no verdict on the session.
    ``evaluate.py`` counts a session without a line as not risky.
    """
    verdict = run.verdict
    if verdict is None:
        return None
    return {
        "session_id": verdict.session_id,
        "risky": verdict.risky,
        "flagged_call_ids": verdict.flagged_call_ids,
        "categories": verdict.categories,
        "severity": verdict.severity,
    }


def read_runs(path: Path) -> dict[str, SessionRun]:
    """
    The runs recorded in ``path``, by session; the last line of a session wins,
    which is how a session that failed and was run again is replaced.
    """
    runs: dict[str, SessionRun] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                run = SessionRun.model_validate_json(line)
                runs[run.session_id] = run
    return runs


def append_run(path: Path, run: SessionRun) -> None:
    """
    Add ``run`` to ``path`` as one line.
    """
    with open(path, "a", encoding="utf-8") as f:
        f.write(run.model_dump_json() + "\n")


def run_evaluation(
    session_ids: list[str],
    audit: T.Callable[[str], SessionRun],
    path_runs: Path,
    workers: int,
    max_cost_usd: float,
    report: T.Callable[[str], None] = print,
) -> list[SessionRun]:
    """
    Audit every session of ``session_ids`` that ``path_runs`` does not already
    hold without an error, ``workers`` at a time, appending each run as it
    finishes.

    Stops starting sessions once the runs in ``path_runs`` are estimated to
    have cost ``max_cost_usd``; sessions already started finish, so the cap is
    passed by at most ``workers`` sessions.

    :returns: the runs of ``session_ids`` that exist now, in that order.
    """
    runs = read_runs(path_runs)
    todo = [
        session_id
        for session_id in session_ids
        if session_id not in runs or runs[session_id].error is not None
    ]
    lock = threading.Lock()
    state = {"spent": sum(run.cost_usd for run in runs.values()), "done": 0}
    report(
        f"{len(session_ids) - len(todo)} sessions already audited, {len(todo)} to go"
    )

    def work(session_id: str) -> None:
        with lock:
            if state["spent"] >= max_cost_usd:
                return
        run = audit(session_id)
        with lock:
            append_run(path_runs, run)
            runs[session_id] = run
            state["spent"] += run.cost_usd
            state["done"] += 1
            if state["done"] % 25 == 0 or state["done"] == len(todo):
                report(
                    f"{state['done']}/{len(todo)} audited, "
                    f"about ${state['spent']:.2f} spent in this run directory"
                )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    if state["spent"] >= max_cost_usd and state["done"] < len(todo):
        report(
            f"Stopped at the cost cap of ${max_cost_usd:.2f}: "
            f"{len(todo) - state['done']} sessions were not audited"
        )
    return [runs[session_id] for session_id in session_ids if session_id in runs]


def summarize(session_ids: list[str], runs: list[SessionRun]) -> dict:
    """
    The counts a report of the run needs, next to its scores: how many sessions
    got a verdict, how many did not and why, and how often another model than
    the one configured did the judging.
    """
    fallback_runs = [run for run in runs if run.fallbacks]
    return {
        "sessions_picked": len(session_ids),
        "sessions_audited": len(runs),
        "with_verdict": sum(run.verdict is not None for run in runs),
        "errors": sum(run.error is not None for run in runs),
        "refused": sum(run.refused for run in runs),
        "answered_without_verdict": sum(
            run.error is None and not run.refused and run.verdict is None
            for run in runs
        ),
        "sessions_with_fallback": len(fallback_runs),
        "fallback_reasons": dict(
            Counter(
                f"{fallback.trigger}/{fallback.category}"
                + (" (client side)" if fallback.client_side else "")
                for run in fallback_runs
                for fallback in run.fallbacks
            )
        ),
        "model_calls_by_model": dict(
            Counter(model for run in runs for model in run.models)
        ),
        "cost_usd_estimate": round(sum(run.cost_usd for run in runs), 2),
        "mean_seconds": round(sum(run.seconds for run in runs) / len(runs), 1)
        if runs
        else 0.0,
    }


def write_predictions(runs: list[SessionRun], path: Path) -> int:
    """
    Write ``predictions.jsonl`` for ``runs``; returns how many lines it has.
    """
    predictions = [to_prediction(run) for run in runs]
    lines = [
        json.dumps(prediction) for prediction in predictions if prediction is not None
    ]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return len(lines)


def serve_mcp(dir_data: Path, port: int) -> None:  # pragma: no cover
    """
    Serve ``AuditMcp`` over the data in ``dir_data`` on ``port``; runs until the
    process is stopped. The runtime module is used as it is: only the store it
    reads is this run's instead of the package's.
    """
    import os

    from ..one.api import one
    from ..audit.store import load_audit_store
    from ..runtimes.common import MCP_PORT_VAR

    one.__dict__["audit_store"] = load_audit_store(dir_data)
    os.environ[MCP_PORT_VAR] = str(port)

    from ..runtimes.audit_mcp import main as serve

    serve()


def wait_for_port(port: int, seconds: float = 30.0) -> None:  # pragma: no cover
    """
    Return once something accepts connections on the local ``port``.

    :raises TimeoutError: if nothing does within ``seconds``.
    """
    import socket

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise TimeoutError(f"nothing listens on port {port} after {seconds:.0f} seconds")


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    """
    The ``eval-run`` task. Not covered by unit tests: it starts a server and
    calls the model. Everything it calls is.
    """
    import argparse
    import multiprocessing

    from ..paths import path_enum
    from ..one.api import one
    from ..runtimes.audit_agent import make_agent
    from .audit_data import sync_audit_data

    parser = argparse.ArgumentParser(description=main.__doc__)
    # fmt: off
    parser.add_argument("--source", type=Path, required=True, help="the dataset's output directory; its labels/ is never opened")
    parser.add_argument("--name", required=True, help="the run's directory name under tmp/eval/; an existing run is continued")
    parser.add_argument("--max-cost", type=float, required=True, help="stop starting sessions at this estimated cost in US dollars")
    parser.add_argument("--sample", type=int, default=None, help="audit this many sessions drawn at random; default: all")
    parser.add_argument("--seed", type=int, default=0, help="the seed of the draw")
    parser.add_argument("--drop-intent", action="store_true", help="empty every call's intent before the agent sees it")
    parser.add_argument("--workers", type=int, default=8, help="conversations at a time")
    parser.add_argument("--port", type=int, default=18739, help="local port of this run's MCP server")
    # fmt: on
    args = parser.parse_args(argv)

    dir_run = path_enum.dir_eval / args.name
    dir_data = dir_run / "data"
    store = sync_audit_data(args.source, dir_data, drop_intent=args.drop_intent)
    session_ids = pick_sessions(list(store.sessions), args.sample, args.seed)
    model_id = one.config.audit_agent_model_id
    fallback_model_id = one.config.audit_agent_fallback_model_id
    settings = {
        "source": str(args.source.resolve()),
        "drop_intent": args.drop_intent,
        "sample": args.sample,
        "seed": args.seed,
        "model_id": model_id,
        "fallback_model_id": fallback_model_id,
        "question": QUESTION,
        "session_ids": session_ids,
    }
    (dir_run / SESSIONS_FILE).write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )
    print(
        f"Run {dir_run}: {len(session_ids)} of {len(store.sessions)} sessions, model {model_id}"
    )

    server = multiprocessing.Process(
        target=serve_mcp, args=(dir_data, args.port), daemon=True
    )
    server.start()
    try:
        wait_for_port(args.port)
        api_key = one.config.anthropic_api_key
        mcp_url = f"http://127.0.0.1:{args.port}/mcp"

        def audit(session_id: str) -> SessionRun:
            return audit_session(
                session_id,
                lambda log: make_agent(
                    model_id=model_id,
                    api_key=api_key,
                    mcp_url=mcp_url,
                    log=log,
                    fallback_model_id=fallback_model_id,
                ),
            )

        runs = run_evaluation(
            session_ids=session_ids,
            audit=audit,
            path_runs=dir_run / RUNS_FILE,
            workers=args.workers,
            max_cost_usd=args.max_cost,
        )
    finally:
        server.terminate()
    count = write_predictions(runs, dir_run / PREDICTIONS_FILE)
    print(f"Wrote {count} predictions to {dir_run / PREDICTIONS_FILE}")
    print(json.dumps(summarize(session_ids, runs), indent=2))
