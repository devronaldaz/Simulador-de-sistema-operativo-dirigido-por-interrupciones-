"""Despachador: entrega la CPU al proceso que elige el planificador (T2)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..modelos import TipoPaso
from ..procesos import cola

if TYPE_CHECKING:
    from ..nucleo import Simulador


class Despachador:
    def __init__(self, sim: "Simulador") -> None:
        self.sim = sim
        self.cambios_contexto = 0

    def despachar(self) -> None:
        """Se invoca en el retorno de interrupción; solo actúa si la CPU quedó libre."""
        sim = self.sim
        if sim.cpu.actual is not None:
            return
        listos = sim.procesos.listos
        if not listos:
            sim.bitacora.registrar(TipoPaso.SCHED, "Planificador", "CPU libre · cola listos []",
                                   "CPU ociosa (proceso inactivo)",
                                   "No hay procesos listos: la CPU queda ociosa hasta la próxima interrupción.")
            return
        antes = cola(listos)
        p = sim.planificador.elegir(listos)
        self.cambios_contexto += 1
        p.quantum_restante = sim.planificador.quantum
        if p.primer_despacho is None:
            p.primer_despacho = sim.tick
        turno = (f"le asigna un quantum de {p.quantum_restante}" if p.quantum_restante
                 else "lo deja ejecutar hasta que se bloquee o termine")
        sim.procesos.poner_en_cpu(p, antes,
            f"Despacho: el planificador {sim.planificador.nombre} toma la cabeza de la cola de listos {antes}; "
            f"el despachador restaura el contexto de {p.pid} (PC={p.pc}) desde su PCB y {turno}.")
