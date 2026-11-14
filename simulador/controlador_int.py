"""Controlador de interrupciones (modelo funcional de un 8259A; sección 4.2.3).

Es el único punto de entrada al SO simulado: acepta las señales en orden de
prioridad, las CUENTA y las entrega a su ISR a través de la tabla de vectores.

Orden de servicio dentro de un tick (tabla 4.3):
  1. síncronas de la instrucción (fallo, syscall, excepción)
  2. llegadas de procesos (INT 0x80 spawn emitida por init)
  3. NMI (anidada dentro de la ISR en curso si la hay)
  4. IRQ0 (timer)
  5. IRQ14 (disco/DMA), que espera en el IRR hasta el EOI de la anterior
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .modelos import PCB, Interrupcion, PeticionDisco, Senal, TipoInt

if TYPE_CHECKING:
    from .nucleo import Simulador


class ControladorInterrupciones:
    def __init__(self, sim: "Simulador") -> None:
        self.sim = sim
        self.irr: list[str] = []          # peticiones pendientes
        self.imr: set[str] = set()        # IRQ enmascaradas (vacío por defecto)
        self.IF = True                    # bandera de habilitación de interrupciones
        self.nmi_pendiente = False

    def atender_frontera(self, sincrona: Senal | None, llegadas: list[PCB], hay_timer: bool,
                         fines_disco: list[PeticionDisco], nmi: bool) -> None:
        self.nmi_pendiente = nmi
        if sincrona:
            self._aceptar(sincrona.tipo, sincrona.pid, sincrona.vector, sincrona.datos)
        for p in llegadas:
            self._aceptar(TipoInt.SYSCALL, p.pid, "0x80", {"servicio": "spawn"})

        self.irr = (["IRQ0"] if hay_timer else []) + ["IRQ14"] * len(fines_disco)
        if hay_timer and "IRQ0" not in self.imr:
            irr_al_aceptar = list(self.irr)
            self.irr.remove("IRQ0")
            actual = self.sim.cpu.actual
            self.IF = False
            self._aceptar(TipoInt.TIMER, actual.pid if actual else None, "0x20", {"irr": irr_al_aceptar})
            self.eoi()
        if self.nmi_pendiente:          # sin timer en este tick: la NMI se atiende sola
            self.atender_nmi()
        for peticion in fines_disco:
            if "IRQ14" in self.imr:
                continue
            self.irr.remove("IRQ14")
            self.IF = False
            self._aceptar(TipoInt.ES_DMA, peticion.pid, "0x2E", {"peticion": peticion, "tras_timer": hay_timer})
            self.eoi()

    def atender_nmi(self) -> None:
        """La NMI no depende de IF: se atiende aunque haya una ISR en curso (anidamiento)."""
        if not self.nmi_pendiente:
            return
        self.nmi_pendiente = False
        actual = self.sim.cpu.actual
        self._aceptar(TipoInt.NMI, actual.pid if actual else None, "2", {"anidada": not self.IF})

    def eoi(self) -> None:
        """Fin de la ISR de una IRQ: el PIC libera la línea y se rehabilitan las interrupciones."""
        self.IF = True

    def _aceptar(self, tipo: TipoInt, pid: str | None, vector: str, datos: dict[str, Any]) -> None:
        sim = self.sim
        numero = sim.contador.contar(tipo, pid)            # único punto de conteo (R4)
        intr = Interrupcion(numero, tipo, vector, pid, sim.tick, datos)
        anterior, sim.bitacora.int_actual = sim.bitacora.int_actual, numero
        try:
            sim.ivt.rutina(vector)(sim, intr)
        finally:
            sim.bitacora.int_actual = anterior
