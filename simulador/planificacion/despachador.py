"""Retorno de interrupción: el planificador de corto plazo ELIGE y el despachador ENTREGA la CPU.

Son dos pasos distintos en la bitácora (Sesión 6 – Planificación, diap. 6):
  1. PLAN: el planificador muestra el momento que lo invocó, su criterio y los candidatos.
  2. TRANS (T2): el despachador guarda/carga contextos, pasa a modo usuario y salta al PC.
"""
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
        self.expropiaciones_llegada = 0

    def despachar(self) -> None:
        sim = self.sim
        plan = sim.planificador
        listos = sim.procesos.listos
        actual = sim.cpu.actual

        # Expropiación por llegada (SJF expropiativo, prioridades): momentos 3 y 4.
        if actual is not None and listos and plan.expropiativo:
            mejor = min(listos, key=plan.clave)
            if plan.mejor_que(mejor, actual):
                self.expropiaciones_llegada += 1
                sim.procesos.expropiar(actual,
                    f"Momento {sim.procesos.momento}. Con {plan.nombre} (expropiativo), {plan.describir(mejor)} es mejor "
                    f"que {plan.describir(actual)}, así que se le quita la CPU a {actual.pid} y se guarda su contexto "
                    f"(PC={actual.pc}) en su PCB.", componente=f"Planificador {plan.nombre} (expropiación)")
        if sim.cpu.actual is not None:
            return
        if not listos:
            sim.bitacora.registrar(TipoPaso.SCHED, "Planificador", "CPU libre · cola listos []",
                                   "CPU ociosa (proceso inactivo)",
                                   "No hay procesos listos: la CPU queda ociosa hasta la próxima interrupción.")
            return

        # 1) El planificador de corto plazo elige.
        antes = cola(listos)
        candidatos = ", ".join(plan.describir(q) for q in listos)
        p = plan.elegir(listos)
        sim.bitacora.registrar(TipoPaso.PLAN, f"Planificador de corto plazo ({plan.nombre})",
            f"cola listos {antes}", f"elegido: {p.pid}",
            f"Momento de planificación {sim.procesos.momento}. Criterio: {plan.criterio_texto()}. "
            f"Candidatos: {candidatos} → elige a {p.pid}.")

        # 2) El despachador hace el cambio de contexto.
        self.cambios_contexto += 1
        p.cambios_contexto += 1
        p.quantum_restante = plan.quantum
        p.ticks_seguidos = p.espera_aging = 0
        if p.primer_despacho is None:
            p.primer_despacho = sim.tick
        tlb = " La TLB se vacía (no hay ASID)." if sim.memoria.vaciar_tlb() else ""
        ptbr = f", PTBR → tabla de páginas de {p.pid}" if sim.memoria.modo == "paginada" else \
               f", base={p.base}, límite={p.limite}"
        turno = (f" Quantum asignado: {p.quantum_restante}." if p.quantum_restante
                 else " Sin quantum: ejecuta hasta bloquearse, terminar o ser expropiado.")
        sim.procesos.poner_en_cpu(p, antes,
            f"Despacho: (1) el contexto del proceso saliente ya quedó guardado en su PCB; (2) carga el contexto de "
            f"{p.pid} desde su PCB (PC={p.pc}{ptbr}); (3) cambia el bit de modo a usuario; (4) salta a la "
            f"instrucción PC={p.pc}.{turno}{tlb}")
