"""Algoritmos de reemplazo de páginas (Sesión 8, diap. 16 y 19).

Cada política recibe los marcos candidatos (ocupados y sin DMA en curso)
y devuelve la víctima. El desempate por número de marco la hace determinista.
"""
from __future__ import annotations

from typing import Callable

from ..modelos import Marco


def victima_lru(candidatos: list[Marco]) -> Marco:
    """La página menos recientemente usada."""
    return min(candidatos, key=lambda m: (m.ultimo_uso, m.id))


def victima_fifo(candidatos: list[Marco]) -> Marco:
    """La página que lleva más tiempo en memoria."""
    return min(candidatos, key=lambda m: (m.cargado_en, m.id))


POLITICAS: dict[str, Callable[[list[Marco]], Marco]] = {"LRU": victima_lru, "FIFO": victima_fifo}
