"""Algoritmos de reemplazo de páginas (Sesión 8 y Semana 14).

Cada política recibe el gestor de memoria y los marcos candidatos (ocupados,
sin DMA en curso y, con alcance local, del propio proceso) y devuelve la
víctima. El desempate por número de marco la hace determinista.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ..modelos import Marco

if TYPE_CHECKING:
    from .gestor import GestorMemoria

INFINITO = 10 ** 9


def victima_lru(gestor: "GestorMemoria", candidatos: list[Marco]) -> Marco:
    """La página menos recientemente usada."""
    return min(candidatos, key=lambda m: (m.ultimo_uso, m.id))


def victima_fifo(gestor: "GestorMemoria", candidatos: list[Marco]) -> Marco:
    """La página que lleva más tiempo en memoria."""
    return min(candidatos, key=lambda m: (m.cargado_en, m.id))


def victima_optimo(gestor: "GestorMemoria", candidatos: list[Marco]) -> Marco:
    """La página que tardará más en volver a usarse (o que no se volverá a usar).

    La distancia se mide en instrucciones del guion de su dueño a partir de su PC.
    Con varios procesos es una aproximación (cada uno avanza a su ritmo).
    """
    def distancia(m: Marco) -> int:
        dueño = gestor.sim.procesos.pcb(m.pid)
        for k, ins in enumerate(dueño.guion[dueño.pc:]):
            if ins.pagina == m.pagina:
                return k
        return INFINITO
    return max(candidatos, key=lambda m: (distancia(m), -m.id))


def victima_clock(gestor: "GestorMemoria", candidatos: list[Marco]) -> Marco:
    """Reloj / segunda oportunidad: la manecilla recorre los marcos; si R=1 lo pone en 0 y sigue."""
    ids = {m.id for m in candidatos}
    orden = [m for m in gestor.marcos if not m.del_so]
    n = len(orden)
    i = next(k for k, m in enumerate(orden) if m.id == gestor.manecilla)
    for _ in range(2 * n + 1):
        m = orden[i % n]
        if m.id in ids:
            entrada = gestor.tablas[m.pid][m.pagina]
            if entrada.r:
                entrada.r = False                  # segunda oportunidad
            else:
                return m
        i += 1
    return min(candidatos, key=lambda m: m.id)    # no debería ocurrir


# Registro ÚNICO de políticas: config, CLI y documentación leen de aquí.
POLITICAS: dict[str, Callable[["GestorMemoria", list[Marco]], Marco]] = {
    "LRU": victima_lru, "FIFO": victima_fifo, "OPTIMO": victima_optimo, "CLOCK": victima_clock,
}

CRITERIOS = {
    "LRU": "la menos recientemente usada",
    "FIFO": "la que lleva más tiempo en memoria",
    "OPTIMO": "la que tardará más en volver a usarse",
    "CLOCK": "la primera con bit R=0 que encuentra la manecilla",
}
