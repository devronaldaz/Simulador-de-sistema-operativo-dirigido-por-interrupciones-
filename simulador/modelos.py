"""Modelos de datos del simulador (informe, sección 4.5).

Solo estructuras: ninguna clase de este módulo toma decisiones de política.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Estado(str, Enum):
    """Estados del proceso: los cinco de la Sesión 6 más ZOMBIE."""
    NUEVO = "NUEVO"
    LISTO = "LISTO"
    EJECUTANDO = "EJECUTANDO"
    BLOQUEADO = "BLOQUEADO"
    ZOMBIE = "ZOMBIE"          # finalizó, pero aún conserva PCB y memoria
    TERMINADO = "TERMINADO"


class TipoInt(str, Enum):
    """Categorías del contador de interrupciones (requisito R4)."""
    TIMER = "TIMER"
    ES_DMA = "ES_DMA"
    SYSCALL = "SYSCALL"
    FALLO_PAG = "FALLO_PAG"
    EXCEPCION = "EXCEPCION"
    NMI = "NMI"
    WORST_TIME = "WORST_TIME"   # el proceso alcanzó su tope de ráfaga
    SENAL = "SENAL"             # señal kill
    PROTECCION = "PROTECCION"   # dirección fuera del espacio del proceso


class TipoPaso(str, Enum):
    """Clases de paso significativo de la bitácora (sección 4.7.3)."""
    INT = "INT"        # aceptación de una interrupción
    TRANS = "TRANS"    # cambio de estado de un proceso
    MEM = "MEM"        # cambio en marcos, regiones o tablas de páginas
    EXEC = "EXEC"      # instrucción de cómputo completada
    SCHED = "SCHED"    # decisión de planificación sin cambio de proceso
    PLAN = "PLAN"      # el planificador elige (corto o largo plazo)


# ---------------------------------------------------------------------------
# Máquina de estados como TABLA DE DATOS: (origen, destino) -> (id, rótulo).
# Agregar un estado o una transición es agregar filas aquí; el gestor de
# procesos valida contra esta tabla y el visor la dibuja desde la traza.
# ---------------------------------------------------------------------------
TRANSICIONES: dict[tuple[Estado, Estado], tuple[str, str]] = {
    (Estado.NUEVO, Estado.LISTO): ("T1", "Admitido"),
    (Estado.LISTO, Estado.EJECUTANDO): ("T2", "Despacho del planificador"),
    (Estado.EJECUTANDO, Estado.LISTO): ("T3", "Interrupción / expropiación"),
    (Estado.EJECUTANDO, Estado.BLOQUEADO): ("T4", "Espera de E/S o evento"),
    (Estado.BLOQUEADO, Estado.LISTO): ("T5", "Fin de E/S o evento"),
    (Estado.EJECUTANDO, Estado.TERMINADO): ("T6", "Salida"),
    (Estado.EJECUTANDO, Estado.ZOMBIE): ("T7", "Salida sin liberar"),
    (Estado.ZOMBIE, Estado.TERMINADO): ("T8", "Recolección"),
    (Estado.NUEVO, Estado.TERMINADO): ("T9", "Rechazado en la admisión"),
}


@dataclass(frozen=True)
class Instruccion:
    """Una instrucción del guion: cada una consume un tick y referencia una página."""
    op: str              # cpu | write | read | syscall | div0 | exit
    pagina: int
    nombre: str = ""     # servicio de syscall (p. ej. "getpid")
    desplazamiento: int | None = None   # si se da una dirección explícita: d = VA mod tamaño

    def __str__(self) -> str:
        return f"{self.op}:{self.pagina}" + (f":{self.nombre}" if self.nombre else "")


@dataclass
class PCB:
    """Bloque de control de proceso (tabla 4.4 y diapositivas de la Sesión 6)."""
    pid: str
    llegada: int
    guion: list[Instruccion]
    prioridad: int = 1                 # menor número = mayor prioridad
    burst: int | None = None           # ráfaga total declarada (notación corta)
    tamano: int | None = None          # bytes (MMU contigua y protección)
    padre: str = "init"
    estado: Estado = Estado.NUEVO
    pc: int = 0
    quantum_restante: int | None = None
    motivo_ultimo_cambio: str = ""
    tick_ultimo_cambio: int = 0
    espera_en: str | None = None
    reintento_desde: int | None = None
    primer_despacho: int | None = None
    fin: int | None = None
    zombie_desde: int | None = None
    instrucciones_completadas: int = 0
    cpu_usado: int = 0                 # ticks de CPU con instrucción completada
    ticks_seguidos: int = 0            # ticks de CPU desde el último despacho (prioridad dinámica)
    espera_aging: int = 0              # ticks en LISTO desde el último ajuste de aging
    prioridad_inicial: int = 1
    senal_pendiente: str | None = None
    operaciones_es: int = 0
    cambios_contexto: int = 0
    base: int | None = None            # MMU contigua
    limite: int | None = None
    tiempo_en_estado: dict[Estado, int] = field(
        default_factory=lambda: {Estado.LISTO: 0, Estado.EJECUTANDO: 0, Estado.BLOQUEADO: 0,
                                 Estado.ZOMBIE: 0})

    @property
    def instruccion_actual(self) -> Instruccion:
        return self.guion[self.pc]

    @property
    def burst_total(self) -> int:
        """Ráfaga total de CPU: la declarada o el número de instrucciones del guion."""
        return self.burst if self.burst is not None else len(self.guion)

    def rafaga_restante(self) -> int:
        """Próxima ráfaga de CPU: instrucciones hasta el próximo bloqueo (read) o el final, inclusive."""
        n = 0
        for ins in self.guion[self.pc:]:
            n += 1
            if ins.op in ("read", "exit", "div0"):
                break
        return n

    @property
    def clase(self) -> str:
        """CPU-bound o I/O-bound según la proporción de lecturas en su guion (Sesión 6 – Planificación, diap. 7)."""
        lecturas = sum(1 for i in self.guion if i.op == "read")
        return "I/O-bound" if lecturas and len(self.guion) / lecturas <= 6 else "CPU-bound"


@dataclass
class EntradaTP:
    """Entrada de la tabla de páginas: marco y bits R (referenciada) y M (modificada)."""
    marco: int
    r: bool = False
    m: bool = False


@dataclass
class Marco:
    """Marco de memoria física."""
    id: int
    pid: str | None = None
    pagina: int | None = None
    ultimo_uso: int = -1       # lo lee LRU
    cargado_en: int = -1       # lo lee FIFO
    en_transito: bool = False  # DMA en curso: no puede ser víctima
    del_so: bool = False       # reservado para el sistema operativo

    @property
    def libre(self) -> bool:
        return self.pid is None and not self.en_transito and not self.del_so

    @property
    def etiqueta(self) -> str | None:
        if self.del_so:
            return "SO"
        return None if self.pid is None else f"{self.pid}.{self.pagina}"

    def __str__(self) -> str:
        if self.del_so:
            return f"M{self.id}:SO"
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
    int_tipo: str | None = None
    vista: dict[str, Any] = field(default_factory=dict)
