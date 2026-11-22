# -*- coding: utf-8 -*-

"""
Copy the audit dataset's inputs into the package, ``audit/data/``, where the
runtimes read them (``mise run sync-audit-data``).

The dataset is generated outside this repository. What is copied is a fixed
list of files; the dataset's ``labels/`` directory, the ground truth an auditor
is scored against, is not on it, and nothing here walks the source directory.
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

from ..audit.store import POLICY_FILE
from ..audit.store import ORG_FILE
from ..audit.store import TOOLS_FILE
from ..audit.store import AGENTS_FILE
from ..audit.store import TRACES_FILE
from ..audit.store import AuditStore
from ..audit.store import load_audit_store

#: The files copied byte for byte.
COPIED_FILES = [POLICY_FILE, ORG_FILE, TOOLS_FILE, AGENTS_FILE]

#: The traces in the source directory, uncompressed.
SOURCE_TRACES_FILE = "traces.jsonl"


def without_intent(traces: bytes) -> bytes:
    """
    The traces with the ``intent`` of every tool call emptied.

    ``intent`` is the audited agent's own account of a call. An evaluation run
    without it shows how much an auditor's score rests on that account rather
    than on what the call did.
    """
    lines = []
    for line in traces.decode("utf-8").splitlines():
        if line.strip():
            session = json.loads(line)
            for call in session["tool_calls"]:
                call["intent"] = ""
            lines.append(json.dumps(session, ensure_ascii=False))
    return ("\n".join(lines) + "\n").encode("utf-8")


def sync_audit_data(
    dir_source: Path,
    dir_target: Path,
    drop_intent: bool = False,
) -> AuditStore:
    """
    Copy the audit inputs from ``dir_source`` into ``dir_target``, compressing
    the traces, then load the result to prove it validates. ``drop_intent``
    empties every call's ``intent`` on the way (:func:`without_intent`); the
    package's own copy is never made that way.

    The gzip header carries no file name and no timestamp, so the same source
    always produces the same bytes and an unchanged dataset is an empty diff.

    :returns: the store loaded from ``dir_target``.
    :raises FileNotFoundError: a source file is missing; nothing is half
        checked, because every file is looked for before any is written.
    """
    names = COPIED_FILES + [SOURCE_TRACES_FILE]
    missing = [name for name in names if not (dir_source / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"{dir_source} has no {', '.join(missing)}; "
            "build the dataset first, or pass its directory with --source"
        )
    dir_target.mkdir(parents=True, exist_ok=True)
    for name in COPIED_FILES:
        shutil.copyfile(dir_source / name, dir_target / name)
    content = (dir_source / SOURCE_TRACES_FILE).read_bytes()
    if drop_intent:
        content = without_intent(content)
    with open(dir_target / TRACES_FILE, "wb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
            gz.write(content)
    return load_audit_store(dir_target)


def main(argv: list[str] | None = None) -> None:
    """
    The ``sync-audit-data`` task: copy from ``--source`` (default: the
    ``datafaker/out`` directory next to this repository) into the package.
    """
    import argparse

    from ..paths import path_enum

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=path_enum.dir_project_root.parent / "datafaker" / "out",
        help="the dataset's output directory",
    )
    args = parser.parse_args(argv)
    store = sync_audit_data(args.source, path_enum.dir_audit_data)
    print(
        f"Copied {args.source} to {path_enum.dir_audit_data}: "
        f"{len(store.agents)} agents, {len(store.sessions)} sessions, "
        f"{store.num_tool_calls} tool calls"
    )
