"""Shim: ``ashare_lab.sim.broker`` → ``ashare_infra.sim.broker``."""

from ashare_infra.sim.broker import PaperBroker, SimConfig

__all__ = ["PaperBroker", "SimConfig"]
