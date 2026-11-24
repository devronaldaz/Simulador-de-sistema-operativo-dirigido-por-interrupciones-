"""Planificador de corto plazo enchufable (Sesión 6 – Planificación).

Un algoritmo se define por tres ejes que se combinan libremente:
  - criterio de orden: llegada (FCFS/RR), ráfaga (SJF) o prioridad;
  - quantum: sí (RR) o no;
  - expropiación por llegada: sí o no (SJF expropiativo, prioridades).
La prioridad (fija o dinámica) se puede sumar a cualquier algoritmo: así
"RR + prioridades" es solo un parámetro.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from ..modelos import PCB

if TYPE_CHECKING:
    from ..config import Config

# Registro ÚNICO de algoritmos: config, CLI y visor leen de aquí.
ALGORITMOS: dict[str, dict] = {
    "FCFS": {"criterio": "llegada", "quantum": False, "expropiativo": False,
             "descripcion": "Primero en llegar, primero en ser atendido (no expropiativo)"},
    "SJF": {"criterio": "rafaga", "quantum": False, "expropiativo": False,
            "descripcion": "Menor próxima ráfaga de CPU; con expropiativo=true es SRTF"},
    "RR": {"criterio": "llegada", "quantum": True, "expropiativo": False,
           "descripcion": "Turno fijo (quantum); al agotarse vuelve al final de la cola"},
    "PRIORIDAD": {"criterio": "prioridad", "quantum": False, "expropiativo": True,
                  "descripcion": "Mayor prioridad (menor número); expropiativo por defecto"},
}


class Planificador:
    def __init__(self, cfg: "Config") -> None:
        alg = ALGORITMOS[cfg.planificador]
        self.algoritmo = cfg.planificador
        self.criterio = alg["criterio"]
        self.usa_prioridad = cfg.prioridad != "off" or self.criterio == "prioridad"
        self.prioridad_modo = cfg.prioridad if cfg.prioridad != "off" else ("fija" if self.usa_prioridad else "off")
        self.quantum: int | None = cfg.quantum if alg["quantum"] else None
        self.expropiativo = cfg.es_expropiativo
        self.cota = cfg.worst_time if cfg.worst_time and cfg.worst_time_modo == "cota_sjf" else None

    @property
    def nombre(self) -> str:
        partes = [self.algoritmo]
        if self.usa_prioridad and self.criterio != "prioridad":
            partes.append(f"+prioridad {self.prioridad_modo}")
        elif self.criterio == "prioridad" and self.prioridad_modo == "dinamica":
            partes.append(" dinámica")
        if self.expropiativo and not ALGORITMOS[self.algoritmo]["expropiativo"]:
            partes.append(" expropiativo")
        return "".join(partes)

    def rafaga(self, p: PCB) -> int:
        r = p.rafaga_restante()
        return min(r, self.cota) if self.cota else r

    def clave(self, p: PCB) -> tuple:
        """Clave de orden (menor = primero), sin el desempate por orden de llegada a la cola."""
        k: list[int] = []
        if self.usa_prioridad:
            k.append(p.prioridad)
        if self.criterio == "rafaga":
            k.append(self.rafaga(p))
        return tuple(k)

    def describir(self, p: PCB) -> str:
        datos = []
        if self.usa_prioridad:
            datos.append(f"prio={p.prioridad}")
        if self.criterio == "rafaga":
            datos.append(f"ráfaga={self.rafaga(p)}")
        return f"{p.pid}({', '.join(datos)})" if datos else p.pid

    def criterio_texto(self) -> str:
        if self.usa_prioridad and self.criterio == "rafaga":
            return "mayor prioridad y, a igualdad, menor ráfaga"
        if self.usa_prioridad:
            return "mayor prioridad (menor número) y, a igualdad, orden de llegada"
        if self.criterio == "rafaga":
            return "menor próxima ráfaga de CPU (desempate: orden de llegada)"
        return "orden de llegada a la cola (la cabeza)"

    def elegir(self, listos: deque[PCB]) -> PCB:
        """Saca y devuelve el proceso elegido. `min` es estable: a igual clave gana el más antiguo en la cola."""
        elegido = min(listos, key=self.clave)
        listos.remove(elegido)
        return elegido

    def mejor_que(self, candidato: PCB, actual: PCB) -> bool:
        """¿Debe `candidato` expropiar a `actual`? Solo si el algoritmo es expropiativo y su clave es estrictamente menor."""
        return self.expropiativo and bool(self.clave(candidato)) and self.clave(candidato) < self.clave(actual)
