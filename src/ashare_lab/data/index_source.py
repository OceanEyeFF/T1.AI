"""Shim: ``ashare_lab.data.index_source`` → ``ashare_infra.data.index_source``."""

from __future__ import annotations

import sys

from ashare_infra.data import index_source as _impl

sys.modules[__name__] = _impl
