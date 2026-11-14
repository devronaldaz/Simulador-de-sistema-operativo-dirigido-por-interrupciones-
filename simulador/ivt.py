"""Tabla de vectores de interrupción: vector -> ISR (tabla 4.2)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import isr
from .modelos import TipoInt


@dataclass(frozen=True)
class EntradaIVT:
    vector: str
    nombre: str
    tipo: TipoInt
    prioridad: int | None      # None = síncrona (no compite por prioridad)
    enmascarable: bool
    rutina: Callable


class TablaVectores:
    def __init__(self) -> None:
        entradas = [
            EntradaIVT("2", "NMI", TipoInt.NMI, 0, False, isr.isr_nmi),
            EntradaIVT("0x20", "IRQ0 timer", TipoInt.TIMER, 1, True, isr.isr_timer),
            EntradaIVT("0x2E", "IRQ14 disco/DMA", TipoInt.ES_DMA, 3, True, isr.isr_disco),
            EntradaIVT("0x80", "llamada al sistema", TipoInt.SYSCALL, None, False, isr.isr_syscall),
            EntradaIVT("14", "fallo de página", TipoInt.FALLO_PAG, None, False, isr.isr_fallo_pagina),
            EntradaIVT("0", "error de división", TipoInt.EXCEPCION, None, False, isr.isr_excepcion),
        ]
        self.entradas = {e.vector: e for e in entradas}

    def rutina(self, vector: str) -> Callable:
        if vector not in self.entradas:
            raise KeyError(f"vector {vector} sin ISR registrada")
        return self.entradas[vector].rutina
