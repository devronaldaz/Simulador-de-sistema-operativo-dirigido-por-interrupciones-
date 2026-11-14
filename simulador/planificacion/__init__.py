"""Políticas de planificación intercambiables."""
from .base import Planificador
from .fcfs import FCFS
from .rr import RoundRobin


def crear_planificador(nombre: str, quantum: int) -> Planificador:
    if nombre == "RR":
        return RoundRobin(quantum)
    if nombre == "FCFS":
        return FCFS()
    raise ValueError(f"planificador desconocido: {nombre}")
