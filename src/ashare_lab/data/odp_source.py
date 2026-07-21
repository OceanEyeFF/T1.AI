"""Shim: ``ashare_lab.data.odp_source`` → ``ashare_infra.data.odp_source``."""

from __future__ import annotations

import sys

from ashare_infra.data import odp_source as _impl

sys.modules[__name__] = _impl
