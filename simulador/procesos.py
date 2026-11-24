"""Gestor de procesos: PCB, colas, máquina de estados y planificador de largo plazo.

Es el ÚNICO módulo que cambia `pcb.estado`, siempre a través de `_transicion()`,
que valida contra la tabla `TRANSICIONES` y deja el porqué en la bitácora.
También anota cuál de los cinco momentos de la Sesión 6 – Planificación
(diap. 9) dispara la próxima planificación.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from .modelos import PCB, TRANSICIONES, Estado, TipoPaso

if TYPE_CHECKING:
    from .nucleo import Simulador


class TransicionInvalida(RuntimeError):
    """Se intentó un cambio de estado que no está en el mapa de estados."""


def cola(procesos) -> str:
    return "[" + ", ".join(p.pid for p in procesos) + "]"


ACTIVOS = (Estado.LISTO, Estado.EJECUTANDO, Estado.BLOQUEADO, Estado.ZOMBIE)


class GestorProcesos:
    def __init__(self, sim: "Simulador", pcbs: list[PCB]) -> None:
        self.sim = sim
        self.pcbs = pcbs                    # lista de procesos (job queue)
        self.listos: deque[PCB] = deque()   # cola de listos
        self.cola_disco: list[PCB] = []     # cola de espera del disco
        self.cola_nuevos: list[PCB] = []    # esperan admisión del planificador de largo plazo
        self.momento = "4 · se crean los procesos iniciales"   # momento de planificación (Sesión 6, diap. 9)
        self.rechazados = 0

    # ---- consultas ----------------------------------------------------------
    def pcb(self, pid: str) -> PCB:
        return next(p for p in self.pcbs if p.pid == pid)

    def llegadas(self, tick: int) -> list[PCB]:
        return [p for p in self.pcbs if p.estado == Estado.NUEVO and p.llegada == tick and p not in self.cola_nuevos]

    def todos_terminados(self) -> bool:
        return all(p.estado == Estado.TERMINADO for p in self.pcbs)

    def admitidos(self) -> int:
        return sum(1 for p in self.pcbs if p.estado in ACTIVOS)

    def acumular_tiempos(self) -> None:
        for p in self.pcbs:
            if p.estado in p.tiempo_en_estado:
                p.tiempo_en_estado[p.estado] += 1

    # ---- transiciones ----------------------------------------------------------
    def _transicion(self, p: PCB, destino: Estado, componente: str, causa: str, antes: str, despues: str) -> None:
        clave = (p.estado, destino)
        if clave not in TRANSICIONES:
            raise TransicionInvalida(f"{p.pid}: {p.estado.value} → {destino.value} no existe en el mapa de estados")
        origen = p.estado
        p.estado, p.motivo_ultimo_cambio, p.tick_ultimo_cambio = destino, causa, self.sim.tick
        ident, rotulo = TRANSICIONES[clave]
        self.sim.bitacora.registrar(
            TipoPaso.TRANS, componente, f"{p.pid}: {origen.value} · {antes}", f"{p.pid}: {destino.value} · {despues}",
            causa, transicion={"pid": p.pid, "de": origen.value, "a": destino.value, "id": ident, "rotulo": rotulo})
        self.verificar_invariantes()

    # ---- planificador de largo plazo (admisión) -------------------------------
    def solicitar_admision(self, p: PCB) -> None:
        """Lo llama la ISR de spawn: decide si el proceso entra, espera o se rechaza."""
        cfg = self.sim.config
        if cfg.worst_time and cfg.worst_time_modo == "rechazar" and p.burst_total > cfg.worst_time:
            self.rechazados += 1
            p.fin = self.sim.tick
            self._transicion(p, Estado.TERMINADO, "Planificador de largo plazo",
                             f"Rechazado: su ráfaga ({p.burst_total}) supera el worst time ({cfg.worst_time}); "
                             "no se admite al sistema.", "pide admisión", "no admitido")
            return
        if cfg.grado_multiprogramacion and self.admitidos() >= cfg.grado_multiprogramacion:
            self.cola_nuevos.append(p)
            self.sim.bitacora.registrar(TipoPaso.PLAN, "Planificador de largo plazo",
                f"admitidos: {self.admitidos()}", f"{p.pid} espera en NUEVO · cola de nuevos {cola(self.cola_nuevos)}",
                f"Grado de multiprogramación {cfg.grado_multiprogramacion} alcanzado: {p.pid} no se admite todavía; "
                "entrará cuando termine otro proceso.")
            return
        if not self.sim.memoria.admitir(p):
            self.cola_nuevos.append(p)
            return
        self.admitir(p)

    def admitir_pendientes(self) -> None:
        """Al terminar un proceso, el planificador de largo plazo revisa la cola de nuevos."""
        cfg = self.sim.config
        while self.cola_nuevos:
            if cfg.grado_multiprogramacion and self.admitidos() >= cfg.grado_multiprogramacion:
                return
            p = self.cola_nuevos[0]
            if not self.sim.memoria.admitir(p):
                return
            self.cola_nuevos.pop(0)
            self.sim.bitacora.registrar(TipoPaso.PLAN, "Planificador de largo plazo",
                f"cola de nuevos {cola([p] + self.cola_nuevos)}", f"admite a {p.pid}",
                f"Se liberó lugar (grado de multiprogramación o memoria): el planificador de largo plazo admite a {p.pid}.")
            self.admitir(p)

    def admitir(self, p: PCB) -> None:                                   # T1
        antes = cola(self.listos)
        self.listos.append(p)
        self.momento = f"4 · se creó {p.pid}"
        self._transicion(p, Estado.LISTO, "Gestor de procesos",
                         f"Admisión: el SO creó el PCB de {p.pid} y completó su preparación; "
                         "entra al final de la cola de listos.",
                         f"en creación · cola listos {antes}", f"cola listos {cola(self.listos)}")

    # ---- corto plazo -----------------------------------------------------------
    def poner_en_cpu(self, p: PCB, cola_antes: str, causa: str) -> None:  # T2
        self.sim.cpu.actual = p
        self._transicion(p, Estado.EJECUTANDO, "Despachador (cambio de contexto)", causa,
                         f"cola listos {cola_antes}", f"CPU={p.pid} · cola listos {cola(self.listos)}")

    def expropiar(self, p: PCB, causa: str, componente: str | None = None) -> None:   # T3
        antes = cola(self.listos)
        self.listos.append(p)
        self.sim.cpu.actual = None
        self.momento = f"2 · {p.pid} pasó de ejecutando a listo"
        self._transicion(p, Estado.LISTO, componente or f"Planificador {self.sim.planificador.nombre} (cambio de contexto)",
                         causa, f"CPU={p.pid} · cola listos {antes}", f"CPU libre · cola listos {cola(self.listos)}")

    def bloquear(self, p: PCB, causa: str) -> None:                      # T4
        antes = cola(self.cola_disco)
        self.cola_disco.append(p)
        p.espera_en = "disco"
        self.sim.cpu.actual = None
        self.momento = f"1 · {p.pid} se bloqueó"
        self._transicion(p, Estado.BLOQUEADO, "Gestor de procesos", causa,
                         f"CPU={p.pid} · cola disco {antes}", f"CPU libre · cola disco {cola(self.cola_disco)}")

    def desbloquear(self, p: PCB, causa: str) -> None:                   # T5
        antes_d, antes_l = cola(self.cola_disco), cola(self.listos)
        self.cola_disco.remove(p)
        p.espera_en = None
        self.listos.append(p)
        self.momento = f"3 · {p.pid} pasó de bloqueado a listo por fin de E/S"
        self._transicion(p, Estado.LISTO, "Gestor de procesos", causa,
                         f"cola disco {antes_d} · cola listos {antes_l}",
                         f"cola disco {cola(self.cola_disco)} · cola listos {cola(self.listos)}")

    # ---- finalización: inmediata (T6) o pasando por zombie (T7 + T8) -----------
    def terminar(self, p: PCB, causa: str) -> None:
        p.fin = self.sim.tick
        self.sim.cpu.actual = None
        self.momento = f"5 · {p.pid} finalizó"
        if self.sim.config.politica_zombie == "inmediata":
            self._transicion(p, Estado.TERMINADO, "Gestor de procesos", causa, f"CPU={p.pid}", "CPU libre")
            self.sim.memoria.liberar(p)
            self.admitir_pendientes()
        else:
            p.zombie_desde = self.sim.tick
            self._transicion(p, Estado.ZOMBIE, "Gestor de procesos",
                             f"{causa} Pasa a ZOMBIE: deja de competir por la CPU pero conserva su PCB y su memoria "
                             f"hasta que init recoja su estado de salida (en {self.sim.config.recolector_ticks} ticks).",
                             f"CPU={p.pid}", "CPU libre · recursos retenidos")

    def recolectar(self, p: PCB) -> None:                                # T8
        self._transicion(p, Estado.TERMINADO, "Recolector (init)",
                         f"init recoge el estado de salida de {p.pid} (equivale a wait) tras "
                         f"{self.sim.tick - p.zombie_desde} ticks como zombie: ahora sí se liberan su PCB y su memoria.",
                         "recursos retenidos", "recursos liberados")
        self.sim.memoria.liberar(p)
        self.admitir_pendientes()

    # ---- invariantes E1–E5 -------------------------------------------------------
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
