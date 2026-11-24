"""Configuración y carga del escenario JSON (informe, sección 6.2).

Todos los parámetros viven en `Config`; la CLI y el JSON escriben aquí y los
algoritmos se registran en un solo lugar (`planificacion.ALGORITMOS` y
`memoria.reemplazo.POLITICAS`).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .memoria.reemplazo import POLITICAS
from .modelos import PCB, Instruccion
from .planificacion import ALGORITMOS

OPERACIONES = {"cpu", "write", "read", "syscall", "div0", "exit"}
OPCIONES = {
    "planificador": set(ALGORITMOS),
    "reemplazo": set(POLITICAS),
    "prioridad": {"off", "fija", "dinamica"},
    "worst_time_modo": {"rechazar", "truncar", "cota_sjf", "defecto"},
    "politica_zombie": {"inmediata", "recolector"},
    "mmu": {"paginada", "contigua"},
    "ajuste": {"primer", "mejor", "peor", "siguiente"},
    "alcance": {"global", "local"},
}


class ErrorEscenario(ValueError):
    """El escenario no cumple el formato esperado."""


@dataclass
class Config:
    # --- planificación de corto plazo ---
    planificador: str = "RR"                 # FCFS | SJF | RR | PRIORIDAD
    quantum: int = 4
    expropiativo: bool | None = None         # None = el valor propio del algoritmo
    prioridad: str = "off"                   # off | fija | dinamica (se combina con cualquier algoritmo)
    aging: int = 0                           # ticks en LISTO para mejorar 1 nivel de prioridad (0 = sin aging)
    # --- tiempos ---
    worst_time: int = 0                      # tope de ráfaga (0 = sin tope)
    worst_time_modo: str = "rechazar"        # rechazar | truncar | cota_sjf | defecto
    periodo_timer: int = 1
    latencia_read: int = 4
    latencia_fallo: int = 3
    latencia_swap: int = 2                   # E/S extra al desalojar una página modificada
    # --- procesos ---
    politica_zombie: str = "inmediata"       # inmediata | recolector
    recolector_ticks: int = 3                # ticks que un proceso permanece zombie
    grado_multiprogramacion: int = 0         # máximo de procesos admitidos (0 = sin límite)
    # --- memoria ---
    mmu: str = "paginada"                    # paginada | contigua
    marcos: int = 3                          # marcos para procesos (paginada)
    marcos_so: int = 0                       # marcos reservados para el SO al inicio de la memoria
    tamano_marco: int = 4096                 # bytes por marco / página
    reemplazo: str = "LRU"                   # LRU | FIFO | OPTIMO | CLOCK
    alcance: str = "global"                  # global | local
    pagina_0_residente_al_admitir: bool = True
    tlb: int = 0                             # entradas de la TLB (0 = sin TLB)
    memoria_total: int = 65536               # bytes (contigua)
    memoria_so: int = 8192                   # bytes reservados al SO (contigua)
    ajuste: str = "primer"                   # primer | mejor | peor | siguiente (contigua)
    ws_delta: int = 6                        # ventana del conjunto de trabajo
    # --- tiempos de acceso para el EAT (Sesión 8) ---
    ma_ns: int = 100
    tlb_ns: int = 20
    trpf_ns: int = 25_000_000
    max_ticks: int = 10_000

    @property
    def es_expropiativo(self) -> bool:
        if self.expropiativo is not None:
            return self.expropiativo
        return ALGORITMOS[self.planificador]["expropiativo"]


@dataclass
class EventoExterno:
    tick: int
    tipo: str              # "NMI" | "KILL"
    pid: str | None = None


@dataclass
class Escenario:
    nombre: str
    config: Config
    procesos: list[PCB]
    eventos: list[EventoExterno] = field(default_factory=list)


def parsear_instruccion(texto: str, tamano_marco: int = 4096) -> Instruccion:
    """'cpu:0', 'write:1', 'read:0', 'syscall:0:getpid', 'div0:0', 'exit:1' o con dirección: 'cpu:@13322'."""
    partes = texto.split(":")
    if len(partes) < 2 or partes[0] not in OPERACIONES:
        raise ErrorEscenario(f"instrucción inválida '{texto}' (use operación:página)")
    desplazamiento = None
    try:
        if partes[1].startswith("@"):
            direccion = int(partes[1][1:])
            pagina, desplazamiento = divmod(direccion, tamano_marco)
        else:
            pagina = int(partes[1])
    except ValueError as exc:
        raise ErrorEscenario(f"página o dirección no numérica en '{texto}'") from exc
    if pagina < 0:
        raise ErrorEscenario(f"página negativa en '{texto}'")
    nombre = partes[2] if len(partes) > 2 else ""
    if partes[0] == "syscall" and not nombre:
        raise ErrorEscenario(f"falta el nombre del servicio en '{texto}'")
    return Instruccion(partes[0], pagina, nombre, desplazamiento)


def guion_desde_burst(burst: int, paginas: int, es: list[int]) -> list[str]:
    """Notación corta: genera un guion de `burst` ticks de CPU repartidos en `paginas` páginas.

    `es` lista los ticks de su ráfaga tras los cuales el proceso hace una lectura de disco.
    """
    guion = []
    for k in range(burst - 1):
        guion.append(f"cpu:{k * paginas // burst}")
        if k + 1 in es:
            guion.append(f"read:{k * paginas // burst}")
    guion.append(f"exit:{(burst - 1) * paginas // burst}")
    return guion


def desde_dict(datos: dict[str, Any], **sobrescribir: Any) -> Escenario:
    """Valida un escenario ya leído y aplica los parámetros de la línea de comandos."""
    cfg_datos = dict(datos.get("config", {}))
    cfg_datos.update({k: v for k, v in sobrescribir.items() if v is not None})
    validos = {f.name for f in fields(Config)}
    desconocidos = set(cfg_datos) - validos
    if desconocidos:
        raise ErrorEscenario(f"parámetros de configuración desconocidos: {sorted(desconocidos)}")
    cfg = Config(**cfg_datos)
    for nombre, opciones in OPCIONES.items():
        if getattr(cfg, nombre) not in opciones:
            raise ErrorEscenario(f"{nombre} = '{getattr(cfg, nombre)}' no válido; use {sorted(opciones)}")
    for nombre in ("quantum", "marcos", "periodo_timer", "latencia_read", "latencia_fallo", "tamano_marco",
                   "recolector_ticks", "ws_delta"):
        if getattr(cfg, nombre) < 1:
            raise ErrorEscenario(f"'{nombre}' debe ser >= 1")
    for nombre in ("aging", "worst_time", "grado_multiprogramacion", "marcos_so", "tlb", "latencia_swap"):
        if getattr(cfg, nombre) < 0:
            raise ErrorEscenario(f"'{nombre}' no puede ser negativo")

    procesos: list[PCB] = []
    for p in datos.get("procesos", []):
        pid = p.get("pid")
        if not pid:
            raise ErrorEscenario("todo proceso necesita 'pid'")
        if any(q.pid == pid for q in procesos):
            raise ErrorEscenario(f"PID repetido: {pid}")
        burst, tamano = p.get("burst"), p.get("tamano")
        if "guion" in p:
            textos = p["guion"]
        else:                                         # notación corta: burst y tamaño
            if burst is None:
                if cfg.worst_time and cfg.worst_time_modo == "defecto":
                    burst = cfg.worst_time
                else:
                    raise ErrorEscenario(f"{pid}: indique 'guion' o 'burst'")
            if int(burst) < 1:
                raise ErrorEscenario(f"{pid}: el burst debe ser >= 1")
            paginas = max(1, math.ceil(int(tamano) / cfg.tamano_marco)) if tamano else 1
            textos = guion_desde_burst(int(burst), paginas, [int(x) for x in p.get("es", [])])
        guion = [parsear_instruccion(i, cfg.tamano_marco) for i in textos]
        if not guion or guion[-1].op not in ("exit", "div0"):
            raise ErrorEscenario(f"el guion de {pid} debe terminar en exit o div0")
        if int(p.get("llegada", 0)) < 0:
            raise ErrorEscenario(f"llegada negativa en {pid}")
        prioridad = int(p.get("prioridad", 1))
        procesos.append(PCB(pid=pid, llegada=int(p.get("llegada", 0)), guion=guion, prioridad=prioridad,
                            prioridad_inicial=prioridad, burst=int(burst) if burst is not None else None,
                            tamano=int(tamano) if tamano is not None else None))
    if not procesos:
        raise ErrorEscenario("el escenario no tiene procesos")

    eventos = []
    for e in datos.get("eventos_externos", []):
        tipo, tick = e.get("tipo"), int(e.get("tick", -1))
        if tipo not in ("NMI", "KILL") or tick < 0:
            raise ErrorEscenario(f"evento externo inválido: {e}")
        if tipo == "KILL" and not any(q.pid == e.get("pid") for q in procesos):
            raise ErrorEscenario(f"KILL a un PID inexistente: {e}")
        eventos.append(EventoExterno(tick, tipo, e.get("pid")))
    return Escenario(datos.get("nombre", "sin nombre"), cfg, procesos, eventos)


def cargar_escenario(ruta: str | Path, **sobrescribir: Any) -> Escenario:
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorEscenario(f"JSON inválido en {ruta}: {exc}") from exc
    return desde_dict(datos, **sobrescribir)
