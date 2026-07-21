"""Shim: ``ashare_lab.data.tushare_source`` → ``ashare_infra.data.tushare_source``."""

from __future__ import annotations

import sys

from ashare_infra.data import tushare_source as _impl

sys.modules[__name__] = _impl
