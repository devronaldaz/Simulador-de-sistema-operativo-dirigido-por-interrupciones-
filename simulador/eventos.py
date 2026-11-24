"""Generador de eventos externos (agenda ordenada por tick)."""
from __future__ import annotations

import heapq

from .config import EventoExterno


class Agenda:
    """Cola de prioridad de eventos externos; el desempate por orden de inserción la hace determinista."""

    def __init__(self, eventos: list[EventoExterno]) -> None:
        self._heap: list[tuple[int, int, EventoExterno]] = []
        for orden, e in enumerate(eventos):
            heapq.heappush(self._heap, (e.tick, orden, e))

    def extraer(self, tick: int) -> list[EventoExterno]:
        """Devuelve (y retira) los eventos programados para `tick`."""
        salida = []
        while self._heap and self._heap[0][0] <= tick:
            t, _, e = heapq.heappop(self._heap)
            if t == tick:
                salida.append(e)
        return salida
