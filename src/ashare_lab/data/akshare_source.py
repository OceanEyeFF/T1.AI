"""Shim: ``ashare_lab.data.akshare_source`` → ``ashare_infra.data.akshare_source``."""

from __future__ import annotations

import sys

from ashare_infra.data import akshare_source as _impl

sys.modules[__name__] = _impl
