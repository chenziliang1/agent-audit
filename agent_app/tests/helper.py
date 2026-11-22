# -*- coding: utf-8 -*-

from ..paths import path_enum
from ..vendor.pytest_cov_helper import run_unit_test as _run_unit_test
from ..vendor.pytest_cov_helper import run_cov_test as _run_cov_test


def run_unit_test(
    script: str,
):
    _run_unit_test(
        script=script,
        root_dir=f"{path_enum.dir_project_root}",
    )


def run_cov_test(
    script: str,
    module: str,
    preview: bool = False,
    is_folder: bool = False,
):
    _run_cov_test(
        script=script,
        module=module,
        root_dir=f"{path_enum.dir_project_root}",
        htmlcov_dir=f"{path_enum.dir_htmlcov}",
        preview=preview,
        is_folder=is_folder,
    )


class FakeAgentResult:
    """
    What a fake agent of a test returns, standing in for the result of a
    Strands agent: its text is ``str(result)``, and it says why the run stopped
    (``end_turn`` for an answer, ``refusal`` when the model declined).
    """

    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.text = text
        self.stop_reason = stop_reason

    def __str__(self) -> str:
        return self.text
