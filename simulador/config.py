"""Configuración y carga del escenario JSON (informe, sección 6.2)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .modelos import PCB, Instruccion

OPERACIONES = {"cpu", "read", "syscall", "div0", "exit"}
PLANIFICADORES = {"RR", "FCFS"}
REEMPLAZOS = {"LRU", "FIFO"}


class ErrorEscenario(ValueError):
    """El escenario no cumple el formato esperado."""


@dataclass
class Config:
    planificador: str = "RR"
    quantum: int = 4
    marcos: int = 3
    reemplazo: str = "LRU"
    periodo_timer: int = 1
    latencia_read: int = 4
    latencia_fallo: int = 3
    pagina_0_residente_al_admitir: bool = True
    max_ticks: int = 10_000


@dataclass
class EventoExterno:
    tick: int
    tipo: str          # por ahora solo "NMI"


@dataclass
class Escenario:
    nombre: str
    config: Config
    procesos: list[PCB]
    eventos: list[EventoExterno] = field(default_factory=list)


def parsear_instruccion(texto: str) -> Instruccion:
    """Convierte 'cpu:0', 'read:0', 'syscall:0:getpid', 'div0:0' o 'exit:1'."""
    partes = texto.split(":")
    if len(partes) < 2 or partes[0] not in OPERACIONES:
        raise ErrorEscenario(f"instrucción inválida '{texto}' (use operación:página)")
    try:
        pagina = int(partes[1])
    except ValueError as exc:
        raise ErrorEscenario(f"página no numérica en '{texto}'") from exc
    if pagina < 0:
        raise ErrorEscenario(f"página negativa en '{texto}'")
    nombre = partes[2] if len(partes) > 2 else ""
    if partes[0] == "syscall" and not nombre:
        raise ErrorEscenario(f"falta el nombre del servicio en '{texto}'")
    return Instruccion(partes[0], pagina, nombre)


def desde_dict(datos: dict[str, Any], **sobrescribir: Any) -> Escenario:
    """Valida un escenario ya leído y aplica los parámetros de la línea de comandos."""
    cfg_datos = dict(datos.get("config", {}))
    cfg_datos.update({k: v for k, v in sobrescribir.items() if v is not None})
    desconocidos = set(cfg_datos) - set(Config.__dataclass_fields__)
    if desconocidos:
        raise ErrorEscenario(f"parámetros de configuración desconocidos: {sorted(desconocidos)}")
    cfg = Config(**cfg_datos)
    if cfg.planificador not in PLANIFICADORES:
        raise ErrorEscenario(f"planificador '{cfg.planificador}' no soportado; use {sorted(PLANIFICADORES)}")
    if cfg.reemplazo not in REEMPLAZOS:
        raise ErrorEscenario(f"reemplazo '{cfg.reemplazo}' no soportado; use {sorted(REEMPLAZOS)}")
    for nombre in ("quantum", "marcos", "periodo_timer", "latencia_read", "latencia_fallo"):
        if getattr(cfg, nombre) < 1:
            raise ErrorEscenario(f"'{nombre}' debe ser >= 1")

    procesos: list[PCB] = []
    for p in datos.get("procesos", []):
        pid = p.get("pid")
        if not pid:
            raise ErrorEscenario("todo proceso necesita 'pid'")
        if any(q.pid == pid for q in procesos):
            raise ErrorEscenario(f"PID repetido: {pid}")
        guion = [parsear_instruccion(i) for i in p.get("guion", [])]
        if not guion or guion[-1].op not in ("exit", "div0"):
            raise ErrorEscenario(f"el guion de {pid} debe terminar en exit o div0")
        if int(p.get("llegada", 0)) < 0:
            raise ErrorEscenario(f"llegada negativa en {pid}")
        procesos.append(PCB(pid=pid, llegada=int(p.get("llegada", 0)), guion=guion,
                            prioridad=int(p.get("prioridad", 1))))
    if not procesos:
        raise ErrorEscenario("el escenario no tiene procesos")

    eventos = []
    for e in datos.get("eventos_externos", []):
        if e.get("tipo") != "NMI" or int(e.get("tick", -1)) < 0:
            raise ErrorEscenario(f"evento externo inválido: {e}")
        eventos.append(EventoExterno(int(e["tick"]), "NMI"))
    return Escenario(datos.get("nombre", "sin nombre"), cfg, procesos, eventos)


def cargar_escenario(ruta: str | Path, **sobrescribir: Any) -> Escenario:
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorEscenario(f"JSON inválido en {ruta}: {exc}") from exc
    return desde_dict(datos, **sobrescribir)
