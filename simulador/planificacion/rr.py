"""Round Robin: cabeza de la cola, turno fijo (Sesión 6 – Planificación, diap. 21)."""
from __future__ import annotations

from collections import deque

from ..modelos import PCB
from .base import Planificador


class RoundRobin(Planificador):
    nombre = "RR"

    def __init__(self, quantum: int) -> None:
        self._quantum = quantum

    @property
    def quantum(self) -> int:
        return self._quantum

    def elegir(self, listos: deque[PCB]) -> PCB:
        return listos.popleft()
