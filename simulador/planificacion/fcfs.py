"""FCFS: orden de llegada, no expropiativo (Sesión 6 – Planificación, diap. 13)."""
from __future__ import annotations

from collections import deque

from ..modelos import PCB
from .base import Planificador


class FCFS(Planificador):
    nombre = "FCFS"

    @property
    def quantum(self) -> None:
        return None

    def elegir(self, listos: deque[PCB]) -> PCB:
        return listos.popleft()
