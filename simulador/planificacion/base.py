"""Interfaz común de los planificadores (política intercambiable)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque

from ..modelos import PCB


class Planificador(ABC):
    nombre: str = "?"

    @property
    @abstractmethod
    def quantum(self) -> int | None:
        """Duración del turno en ticks, o None si el algoritmo no usa quantum."""

    @abstractmethod
    def elegir(self, listos: deque[PCB]) -> PCB:
        """Saca y devuelve de la cola de listos el proceso que recibirá la CPU."""

    def debe_expropiar_por_quantum(self, actual: PCB) -> bool:
        """Lo consulta la ISR del timer cuando el quantum de `actual` se agotó."""
        return self.quantum is not None
