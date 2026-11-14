"""Gestor de procesos: PCB, colas y máquina de estados (sección 4.6).

Es el ÚNICO módulo que cambia `pcb.estado`, siempre a través de `_transicion()`,
que valida la transición contra la tabla T1–T6 y la registra en la bitácora.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from .modelos import PCB, TRANSICIONES, Estado, TipoPaso

if TYPE_CHECKING:
    from .nucleo import Simulador


class TransicionInvalida(RuntimeError):
    """Se intentó un cambio de estado que no está en el mapa de la Sesión 6."""


def cola(procesos) -> str:
    return "[" + ", ".join(p.pid for p in procesos) + "]"


class GestorProcesos:
    def __init__(self, sim: "Simulador", pcbs: list[PCB]) -> None:
        self.sim = sim
        self.pcbs = pcbs                    # lista de procesos (job queue)
        self.listos: deque[PCB] = deque()   # cola de listos
        self.cola_disco: list[PCB] = []     # cola de espera del disco

    # ---- consultas ----------------------------------------------------------
    def pcb(self, pid: str) -> PCB:
        return next(p for p in self.pcbs if p.pid == pid)

    def llegadas(self, tick: int) -> list[PCB]:
        return [p for p in self.pcbs if p.estado == Estado.NUEVO and p.llegada == tick]

    def todos_terminados(self) -> bool:
        return all(p.estado == Estado.TERMINADO for p in self.pcbs)

    def acumular_tiempos(self) -> None:
        for p in self.pcbs:
            if p.estado in p.tiempo_en_estado:
                p.tiempo_en_estado[p.estado] += 1

    # ---- transiciones (T1–T6) ------------------------------------------------
    def _transicion(self, p: PCB, destino: Estado, componente: str, causa: str,
                    antes: str, despues: str) -> None:
        clave = (p.estado, destino)
        if clave not in TRANSICIONES:
            raise TransicionInvalida(f"{p.pid}: {p.estado.value} → {destino.value} no existe en el mapa de estados")
        origen = p.estado
        p.estado, p.motivo_ultimo_cambio, p.tick_ultimo_cambio = destino, causa, self.sim.tick
        self.sim.bitacora.registrar(
            TipoPaso.TRANS, componente,
            f"{p.pid}: {origen.value} · {antes}", f"{p.pid}: {destino.value} · {despues}", causa,
            transicion={"pid": p.pid, "de": origen.value, "a": destino.value, "id": TRANSICIONES[clave]})
        self.verificar_invariantes()

    def admitir(self, p: PCB) -> None:                                   # T1
        antes = cola(self.listos)
        self.listos.append(p)
        self._transicion(p, Estado.LISTO, "Gestor de procesos",
                         f"Admisión: el SO creó el PCB de {p.pid} y completó su preparación; "
                         "entra al final de la cola de listos.",
                         f"en creación · cola listos {antes}", f"cola listos {cola(self.listos)}")

    def poner_en_cpu(self, p: PCB, cola_antes: str, causa: str) -> None:  # T2
        self.sim.cpu.actual = p
        self._transicion(p, Estado.EJECUTANDO, "Despachador (cambio de contexto)", causa,
                         f"cola listos {cola_antes}", f"CPU={p.pid} · cola listos {cola(self.listos)}")

    def expropiar(self, p: PCB, causa: str) -> None:                     # T3
        antes = cola(self.listos)
        self.listos.append(p)
        self.sim.cpu.actual = None
        self._transicion(p, Estado.LISTO, f"Planificador {self.sim.planificador.nombre} (cambio de contexto)",
                         causa, f"CPU={p.pid} · cola listos {antes}", f"CPU libre · cola listos {cola(self.listos)}")

    def bloquear(self, p: PCB, causa: str) -> None:                      # T4
        antes = cola(self.cola_disco)
        self.cola_disco.append(p)
        p.espera_en = "disco"
        self.sim.cpu.actual = None
        self._transicion(p, Estado.BLOQUEADO, "Gestor de procesos", causa,
                         f"CPU={p.pid} · cola disco {antes}", f"CPU libre · cola disco {cola(self.cola_disco)}")

    def desbloquear(self, p: PCB, causa: str) -> None:                   # T5
        antes_d, antes_l = cola(self.cola_disco), cola(self.listos)
        self.cola_disco.remove(p)
        p.espera_en = None
        self.listos.append(p)
        self._transicion(p, Estado.LISTO, "Gestor de procesos", causa,
                         f"cola disco {antes_d} · cola listos {antes_l}",
                         f"cola disco {cola(self.cola_disco)} · cola listos {cola(self.listos)}")

    def terminar(self, p: PCB, causa: str) -> None:                      # T6
        p.fin = self.sim.tick
        self.sim.cpu.actual = None
        self._transicion(p, Estado.TERMINADO, "Gestor de procesos", causa, f"CPU={p.pid}", "CPU libre")
        self.sim.memoria.liberar(p)

    # ---- invariantes E1–E5 ---------------------------------------------------
    def verificar_invariantes(self) -> None:
        ejecutando = [p for p in self.pcbs if p.estado == Estado.EJECUTANDO]
        actual = self.sim.cpu.actual
        assert len(ejecutando) <= 1, "E1: más de un proceso en EJECUTANDO"
        assert (ejecutando[0] if ejecutando else None) is actual, "E1: la CPU no coincide con el proceso EJECUTANDO"
        for p in self.pcbs:
            en_listos = sum(1 for q in self.listos if q is p)
            en_disco = sum(1 for q in self.cola_disco if q is p)
            if p.estado == Estado.LISTO:
                assert en_listos == 1 and en_disco == 0, f"E2: {p.pid} LISTO no está una vez en la cola de listos"
            elif p.estado == Estado.BLOQUEADO:
                assert en_disco == 1 and en_listos == 0, f"E3: {p.pid} BLOQUEADO no está en una cola de espera"
            else:
                assert en_listos == 0 and en_disco == 0, f"E4: {p.pid} {p.estado.value} no debe estar en colas"
