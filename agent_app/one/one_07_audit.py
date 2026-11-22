# -*- coding: utf-8 -*-

"""
The audit data part of ``one``: :attr:`~agent_app.one.one_07_audit.OneAuditMixin.audit_store`.
"""

from __future__ import annotations

import typing as T
from functools import cached_property

from ..paths import path_enum
from ..audit.store import AuditStore
from ..audit.store import load_audit_store

if T.TYPE_CHECKING:  # pragma: no cover
    from .one_00_main import One


class OneAuditMixin:
    """
    The lazily loaded audit data.
    """

    @cached_property
    def audit_store(self: One) -> AuditStore:
        """
        The audit data bundled with the package (``path_enum.dir_audit_data``),
        loaded and validated once per process on first access.

        It is read only and never changes while a process runs, so one copy
        serves every request of the process.
        """
        return load_audit_store(path_enum.dir_audit_data)
