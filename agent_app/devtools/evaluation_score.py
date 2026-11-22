# -*- coding: utf-8 -*-

"""
Score a run of ``eval-run`` against the dataset's labels (``mise run eval-score``).

The scoring itself is the dataset's own ``eval/evaluate.py``, run as it is, so
a score here means what the dataset's documentation says it means. This module
only decides which sessions each score is about:

- ``evaluate.py`` counts every labeled session that has no prediction as "not
  risky", so a run over a sample must be scored against the labels of that
  sample only.
- A session that quotes an attack is often judged by the fallback model, not
  by the configured one, so the run is scored a second and a third time: once
  over the sessions the configured model judged alone, once over those where
  the fallback model answered at least one call.

This is the only module that opens ``labels/``, and only to hand a filtered
copy to ``evaluate.py`` in a temporary directory that is removed afterwards.
Nothing here is imported by a runtime.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .evaluation import PREDICTIONS_FILE
from .evaluation import RUNS_FILE
from .evaluation import SESSIONS_FILE
from .evaluation import SessionRun
from .evaluation import read_runs

#: The label files ``evaluate.py`` reads; every line of both names its session.
LABEL_FILES = ["session_labels.jsonl", "tool_call_labels.jsonl"]

SCORES_FILE = "scores.txt"

GROUP_ALL = "all audited sessions"
GROUP_CONFIGURED = "sessions the configured model judged alone"
GROUP_FALLBACK = "sessions where the fallback model answered a call"


def group_sessions(runs: list[SessionRun]) -> dict[str, list[str]]:
    """
    The sessions each score is about, by group name.

    A session whose run raised is in no group: that is a failure of the
    harness, not a judgement of the agent, and :func:`score_run` reports how
    many there were. A session the agent answered without a verdict, or
    refused, stays in: it has no prediction, so ``evaluate.py`` counts it as
    "not risky", which is what an auditor that says nothing amounts to.
    """
    answered = [run for run in runs if run.error is None]
    return {
        GROUP_ALL: [run.session_id for run in answered],
        GROUP_CONFIGURED: [run.session_id for run in answered if not run.fallbacks],
        GROUP_FALLBACK: [run.session_id for run in answered if run.fallbacks],
    }


def filter_jsonl(path_source: Path, path_target: Path, session_ids: set[str]) -> int:
    """
    Copy the lines of ``path_source`` whose ``session_id`` is in ``session_ids``
    to ``path_target``; returns how many there were.
    """
    lines = [
        line
        for line in path_source.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line)["session_id"] in session_ids
    ]
    path_target.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return len(lines)


def score_group(
    path_evaluate: Path,
    path_predictions: Path,
    dir_labels: Path,
    session_ids: list[str],
) -> str:
    """
    What ``evaluate.py`` prints for the predictions and the labels of
    ``session_ids`` alone.

    The predictions are filtered too: ``evaluate.py`` counts a flagged call it
    has no label for as a false positive.

    :raises subprocess.CalledProcessError: if ``evaluate.py`` fails.
    """
    wanted = set(session_ids)
    with tempfile.TemporaryDirectory() as tmp:
        dir_tmp = Path(tmp)
        dir_tmp_labels = dir_tmp / "labels"
        dir_tmp_labels.mkdir()
        for name in LABEL_FILES:
            filter_jsonl(dir_labels / name, dir_tmp_labels / name, wanted)
        path_tmp_predictions = dir_tmp / PREDICTIONS_FILE
        filter_jsonl(path_predictions, path_tmp_predictions, wanted)
        result = subprocess.run(
            [
                sys.executable,
                f"{path_evaluate}",
                f"{path_tmp_predictions}",
                "--labels",
                f"{dir_tmp_labels}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    return result.stdout


def score_run(dir_run: Path, dir_dataset: Path) -> str:
    """
    Score the run in ``dir_run`` against the labels of the dataset output
    directory ``dir_dataset``, once per group of :func:`group_sessions`, and
    write the report to ``scores.txt`` in ``dir_run``.

    ``evaluate.py`` is taken from the dataset's project: ``eval/evaluate.py``
    next to the output directory.

    :returns: the report.
    """
    path_evaluate = dir_dataset.parent / "eval" / "evaluate.py"
    runs = list(read_runs(dir_run / RUNS_FILE).values())
    errors = sum(run.error is not None for run in runs)
    parts = [f"Run {dir_run.name}, scored against {dir_dataset / 'labels'}"]
    if errors:
        parts.append(f"{errors} sessions whose run raised are in no score")
    for name, session_ids in group_sessions(runs).items():
        parts.append(f"\n===== {name}: {len(session_ids)} =====")
        if session_ids:
            parts.append(
                score_group(
                    path_evaluate=path_evaluate,
                    path_predictions=dir_run / PREDICTIONS_FILE,
                    dir_labels=dir_dataset / "labels",
                    session_ids=session_ids,
                ).rstrip()
            )
    report = "\n".join(parts) + "\n"
    (dir_run / SCORES_FILE).write_text(report, encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    """
    The ``eval-score`` task: score one run of ``eval-run``.
    """
    import argparse

    from ..paths import path_enum

    parser = argparse.ArgumentParser(description=main.__doc__)
    # fmt: off
    parser.add_argument("--name", required=True, help="the run's directory name under tmp/eval/")
    parser.add_argument("--dataset", type=Path, default=None, help="the dataset's output directory; default: the one the run audited")
    # fmt: on
    args = parser.parse_args(argv)

    dir_run = path_enum.dir_eval / args.name
    dir_dataset = args.dataset
    if dir_dataset is None:
        settings = json.loads((dir_run / SESSIONS_FILE).read_text(encoding="utf-8"))
        dir_dataset = Path(settings["source"])
    print(score_run(dir_run, dir_dataset))
