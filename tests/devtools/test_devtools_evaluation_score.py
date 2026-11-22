# -*- coding: utf-8 -*-

from agent_app.devtools.evaluation_score import GROUP_ALL
from agent_app.devtools.evaluation_score import GROUP_CONFIGURED
from agent_app.devtools.evaluation_score import GROUP_FALLBACK
from agent_app.devtools.evaluation_score import filter_jsonl
from agent_app.devtools.evaluation_score import group_sessions
from agent_app.devtools.evaluation_score import main
from agent_app.devtools.evaluation_score import score_group
from agent_app.devtools.evaluation_score import score_run

import json
import subprocess

import pytest

from agent_app.paths import path_enum
from agent_app.devtools.evaluation import Fallback
from agent_app.devtools.evaluation import SessionRun
from agent_app.devtools.evaluation import append_run

# Stands in for the dataset's eval/evaluate.py: same arguments, and it prints
# how many lines of each file it was given.
EVALUATE = """
import argparse
import os

ap = argparse.ArgumentParser()
ap.add_argument("predictions")
ap.add_argument("--labels")
a = ap.parse_args()


def count(path):
    with open(path) as f:
        return sum(1 for line in f if line.strip())


print(
    "sessions", count(os.path.join(a.labels, "session_labels.jsonl")),
    "calls", count(os.path.join(a.labels, "tool_call_labels.jsonl")),
    "predictions", count(a.predictions),
)
"""


def make_run(session_id: str, error=None, fallback=False) -> SessionRun:
    fallbacks = []
    if fallback:
        fallbacks.append(
            Fallback(
                from_model="acme-widget-model-2",
                to_model="acme-widget-model-1",
                trigger="refusal",
            )
        )
    return SessionRun(
        session_id=session_id,
        seconds=1.0,
        stop_reason=None if error else "end_turn",
        error=error,
        usage={},
        models=[],
        fallbacks=fallbacks,
        verdicts=[],
    )


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.fixture
def dir_dataset(tmp_path):
    """
    A fictional dataset project: ``out/labels`` for five sessions of two calls
    each, and the stand-in ``eval/evaluate.py`` next to ``out``.
    """
    dir_out = tmp_path / "acme" / "out"
    (dir_out / "labels").mkdir(parents=True)
    (tmp_path / "acme" / "eval").mkdir()
    (tmp_path / "acme" / "eval" / "evaluate.py").write_text(EVALUATE)
    session_ids = [f"ses_widget_{i}" for i in range(1, 6)]
    write_jsonl(
        dir_out / "labels" / "session_labels.jsonl",
        [{"session_id": session_id, "risky": False} for session_id in session_ids],
    )
    write_jsonl(
        dir_out / "labels" / "tool_call_labels.jsonl",
        [
            {"call_id": f"call_{session_id}_{n}", "session_id": session_id}
            for session_id in session_ids
            for n in (1, 2)
        ],
    )
    return dir_out


@pytest.fixture
def dir_run(tmp_path):
    """
    A run over four of the five sessions: one plain, two with a fallback (one
    of them without a prediction), one whose run raised.
    """
    dir_run = tmp_path / "eval" / "widget-run"
    dir_run.mkdir(parents=True)
    append_run(dir_run / "runs.jsonl", make_run("ses_widget_1"))
    append_run(dir_run / "runs.jsonl", make_run("ses_widget_2", fallback=True))
    append_run(dir_run / "runs.jsonl", make_run("ses_widget_3", fallback=True))
    append_run(dir_run / "runs.jsonl", make_run("ses_widget_4", error="boom"))
    write_jsonl(
        dir_run / "predictions.jsonl",
        [
            {"session_id": "ses_widget_1", "risky": False},
            {"session_id": "ses_widget_2", "risky": True},
        ],
    )
    return dir_run


def test_group_sessions():
    runs = [
        make_run("ses_widget_1"),
        make_run("ses_widget_2", fallback=True),
        make_run("ses_widget_4", error="boom"),
    ]
    assert group_sessions(runs) == {
        GROUP_ALL: ["ses_widget_1", "ses_widget_2"],
        GROUP_CONFIGURED: ["ses_widget_1"],
        GROUP_FALLBACK: ["ses_widget_2"],
    }


def test_filter_jsonl(tmp_path):
    path_source = tmp_path / "source.jsonl"
    path_source.write_text(
        '{"session_id": "ses_widget_1", "n": 1}\n\n'
        '{"session_id": "ses_widget_2", "n": 2}\n'
        '{"session_id": "ses_widget_1", "n": 3}\n'
    )
    path_target = tmp_path / "target.jsonl"
    assert filter_jsonl(path_source, path_target, {"ses_widget_1"}) == 2
    rows = [json.loads(line) for line in path_target.read_text().splitlines()]
    assert [row["n"] for row in rows] == [1, 3]


def test_score_group(dir_dataset, dir_run):
    """The script sees the labels and the predictions of the group only."""
    out = score_group(
        path_evaluate=dir_dataset.parent / "eval" / "evaluate.py",
        path_predictions=dir_run / "predictions.jsonl",
        dir_labels=dir_dataset / "labels",
        session_ids=["ses_widget_2", "ses_widget_3"],
    )
    assert out == "sessions 2 calls 4 predictions 1\n"


def test_score_group_script_fails(dir_dataset, dir_run):
    path_evaluate = dir_dataset.parent / "eval" / "evaluate.py"
    path_evaluate.write_text("raise SystemExit(3)")
    with pytest.raises(subprocess.CalledProcessError):
        score_group(
            path_evaluate=path_evaluate,
            path_predictions=dir_run / "predictions.jsonl",
            dir_labels=dir_dataset / "labels",
            session_ids=["ses_widget_1"],
        )


def test_score_run(dir_dataset, dir_run):
    report = score_run(dir_run, dir_dataset)
    assert (dir_run / "scores.txt").read_text() == report
    lines = report.splitlines()
    assert lines[0].startswith("Run widget-run, scored against ")
    assert lines[1] == "1 sessions whose run raised are in no score"
    assert f"===== {GROUP_ALL}: 3 =====" in lines
    assert "sessions 3 calls 6 predictions 2" in lines
    assert f"===== {GROUP_CONFIGURED}: 1 =====" in lines
    assert "sessions 1 calls 2 predictions 1" in lines
    assert f"===== {GROUP_FALLBACK}: 2 =====" in lines
    assert "sessions 2 calls 4 predictions 1" in lines


def test_score_run_empty_group(dir_dataset, tmp_path):
    """A group without sessions is named and not scored."""
    dir_run = tmp_path / "eval" / "plain-run"
    dir_run.mkdir(parents=True)
    append_run(dir_run / "runs.jsonl", make_run("ses_widget_1"))
    write_jsonl(dir_run / "predictions.jsonl", [])
    lines = score_run(dir_run, dir_dataset).splitlines()
    assert "whose run raised" not in lines[1]
    assert lines[-1] == f"===== {GROUP_FALLBACK}: 0 ====="


def test_main(dir_dataset, dir_run, monkeypatch, capsys):
    monkeypatch.setattr(path_enum, "dir_eval", dir_run.parent)
    main(["--name", "widget-run", "--dataset", str(dir_dataset)])
    assert "sessions 3 calls 6 predictions 2" in capsys.readouterr().out
    # Without --dataset, the run's own settings say which dataset it audited.
    (dir_run / "sessions.json").write_text(json.dumps({"source": str(dir_dataset)}))
    main(["--name", "widget-run"])
    assert "sessions 3 calls 6 predictions 2" in capsys.readouterr().out


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.devtools.evaluation_score",
        preview=False,
    )
