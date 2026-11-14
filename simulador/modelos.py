"""Modelos de datos del simulador (informe, sección 4.5).

Solo estructuras: ninguna clase de este módulo toma decisiones de política.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Estado(str, Enum):
    """Los cinco estados del mapa de la Sesión 6."""
    NUEVO = "NUEVO"
    LISTO = "LISTO"
    EJECUTANDO = "EJECUTANDO"
    BLOQUEADO = "BLOQUEADO"
    TERMINADO = "TERMINADO"


class TipoInt(str, Enum):
    """Categorías del contador de interrupciones (requisito R4)."""
    TIMER = "TIMER"
    ES_DMA = "ES_DMA"
    SYSCALL = "SYSCALL"
    FALLO_PAG = "FALLO_PAG"
    EXCEPCION = "EXCEPCION"
    NMI = "NMI"


class TipoPaso(str, Enum):
    """Clases de paso significativo de la bitácora (sección 4.7.3)."""
    INT = "INT"        # aceptación de una interrupción
    TRANS = "TRANS"    # cambio de estado de un proceso
    MEM = "MEM"        # cambio en marcos o tablas de páginas
    EXEC = "EXEC"      # instrucción de cómputo completada
    SCHED = "SCHED"    # decisión de planificación sin cambio


# Transiciones permitidas del mapa de estados (tabla 4.6) -> identificador.
TRANSICIONES: dict[tuple[Estado, Estado], str] = {
    (Estado.NUEVO, Estado.LISTO): "T1",
    (Estado.LISTO, Estado.EJECUTANDO): "T2",
    (Estado.EJECUTANDO, Estado.LISTO): "T3",
    (Estado.EJECUTANDO, Estado.BLOQUEADO): "T4",
    (Estado.BLOQUEADO, Estado.LISTO): "T5",
    (Estado.EJECUTANDO, Estado.TERMINADO): "T6",
}


@dataclass(frozen=True)
class Instruccion:
    """Una instrucción del guion: cada una consume un tick y referencia una página."""
    op: str              # cpu | read | syscall | div0 | exit
    pagina: int
    nombre: str = ""     # servicio de syscall (p. ej. "getpid")

    def __str__(self) -> str:
        return f"{self.op}:{self.pagina}" + (f":{self.nombre}" if self.nombre else "")


@dataclass
class PCB:
    """Bloque de control de proceso (tabla 4.4)."""
    pid: str
    llegada: int
    guion: list[Instruccion]
    prioridad: int = 1
    estado: Estado = Estado.NUEVO
    pc: int = 0
    quantum_restante: int | None = None
    motivo_ultimo_cambio: str = ""
    tick_ultimo_cambio: int = 0
    espera_en: str | None = None
    reintento_desde: int | None = None
    primer_despacho: int | None = None
    fin: int | None = None
    instrucciones_completadas: int = 0
    tiempo_en_estado: dict[Estado, int] = field(
        default_factory=lambda: {Estado.LISTO: 0, Estado.EJECUTANDO: 0, Estado.BLOQUEADO: 0})

    @property
    def instruccion_actual(self) -> Instruccion:
        return self.guion[self.pc]


@dataclass
class Marco:
    """Marco de memoria física."""
    id: int
    pid: str | None = None
    pagina: int | None = None
    ultimo_uso: int = -1      # lo lee LRU
    cargado_en: int = -1      # lo lee FIFO
    en_transito: bool = False  # DMA en curso: no puede ser víctima

    @property
    def libre(self) -> bool:
        return self.pid is None and not self.en_transito

    @property
    def etiqueta(self) -> str | None:
        return None if self.pid is None else f"{self.pid}.{self.pagina}"

    def __str__(self) -> str:
        if self.pid is None:
            return f"M{self.id}:libre"
        return f"M{self.id}:{self.etiqueta}" + ("(cargando)" if self.en_transito else "")


@dataclass
class Senal:
    """Señal síncrona producida por la instrucción en ejecución."""
    tipo: TipoInt
    pid: str
    vector: str
    datos: dict[str, Any] = field(default_factory=dict)


@dataclass
class Interrupcion:
    """Interrupción aceptada por el controlador (ya contada)."""
    id: int
    tipo: TipoInt
    vector: str
    pid: str | None          # proceso al que se atribuye; None = Sistema
    tick: int
    datos: dict[str, Any] = field(default_factory=dict)

    @property
    def etiqueta(self) -> str:
        return f"[INT #{self.id}]"


@dataclass
class PeticionDisco:
    """Operación de disco en curso (lectura o carga de página por DMA)."""
    pid: str
    tipo: str                 # "read" | "pagina"
    fin: int
    marco: int | None = None
    pagina: int | None = None


@dataclass
class EntradaBitacora:
    """Un paso atómico de la bitácora transaccional (tabla 4.7)."""
    paso: int
    tick: int
    tipo_paso: TipoPaso
    componente: str
    int_id: int | None
    antes: str
    despues: str
    causa: str
    contadores: dict[str, int]
    transicion: dict[str, str] | None = None
    vista: dict[str, Any] = field(default_factory=dict)
