"""Bitácora transaccional, opción A (requisito R6, sección 4.7).

Cada paso guarda estado antes, estado después y causa, más una "vista" del
sistema completo (PCB, colas, memoria, MMU, contadores) para que el visor y la
consola puedan mostrar cualquier paso.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .modelos import TRANSICIONES, EntradaBitacora, Estado, TipoPaso

if TYPE_CHECKING:
    from .nucleo import Simulador


class Bitacora:
    def __init__(self, sim: "Simulador") -> None:
        self.sim = sim
        self.pasos: list[EntradaBitacora] = []
        self.instantaneas: list[dict[str, Any]] = []
        self.int_actual: int | None = None   # interrupción cuya ISR está en curso

    def registrar(self, tipo: TipoPaso, componente: str, antes: str, despues: str, causa: str,
                  transicion: dict[str, str] | None = None) -> EntradaBitacora:
        entrada = EntradaBitacora(
            paso=len(self.pasos) + 1, tick=self.sim.tick, tipo_paso=tipo, componente=componente,
            int_id=self.int_actual, antes=antes, despues=despues, causa=causa,
            contadores=self.sim.contador.instantanea(), transicion=transicion,
            int_tipo=self.sim.contador.ultimo_tipo if tipo == TipoPaso.INT else None, vista=self.vista())
        self.pasos.append(entrada)
        return entrada

    def _pcb(self, p) -> dict[str, Any]:
        sim = self.sim
        return {
            "pid": p.pid, "estado": p.estado.value, "pc": p.pc, "padre": p.padre, "hijos": [],
            "prioridad": p.prioridad, "burst": p.burst_total, "rafaga_restante": p.rafaga_restante()
            if p.estado not in (Estado.TERMINADO, Estado.ZOMBIE) else 0,
            "cpu_usado": p.cpu_usado, "quantum_restante": p.quantum_restante, "clase": p.clase,
            "espera": p.tiempo_en_estado[Estado.LISTO], "llegada": p.llegada,
            "interrupciones": sum(sim.contador.por_proceso[p.pid].values()),
            "cambios_contexto": p.cambios_contexto, "operaciones_es": p.operaciones_es,
            "base": p.base, "limite": p.limite, "senal_pendiente": p.senal_pendiente,
            "motivo": p.motivo_ultimo_cambio,
        }

    def vista(self) -> dict[str, Any]:
        """Estado completo del sistema tras el paso (lo usan el visor y la consola)."""
        sim = self.sim
        actual = sim.cpu.actual
        q = sim.planificador.quantum
        mem = sim.memoria
        return {
            "tick": sim.tick,
            "cpu": actual.pid if actual else None,
            "modo": "kernel" if self.int_actual is not None else "usuario",
            "quantum": (f"{q - actual.quantum_restante}/{q}"
                        if actual and q and actual.quantum_restante is not None else None),
            "listos": [p.pid for p in sim.procesos.listos],
            "nuevos": [p.pid for p in sim.procesos.cola_nuevos],
            "disco": [{"pid": d.pid, "tipo": d.tipo, "fin": d.fin} for d in sim.disco.peticiones],
            "marcos": [{"id": m.id, "pagina": m.etiqueta, "cargando": m.en_transito,
                        "ultimo_uso": m.ultimo_uso} for m in mem.marcos],
            "mapa": mem.filas(),
            "tablas": {p.pid: mem.tabla_paginas(p.pid) for p in sim.procesos.pcbs},
            "tlb": [f"{pid}.{pag}" for pid, pag in getattr(mem, "tlb", [])],
            "mmu": mem.ultima_traduccion,
            "estados": {p.pid: p.estado.value for p in sim.procesos.pcbs},
            "motivos": {p.pid: p.motivo_ultimo_cambio for p in sim.procesos.pcbs},
            "pcb": {p.pid: self._pcb(p) for p in sim.procesos.pcbs},
            "contadores": sim.contador.instantanea(),
            "por_proceso": {pid: sum(c.values()) for pid, c in sim.contador.por_proceso.items()},
            "cambios_contexto": sim.despachador.cambios_contexto,
        }

    def cerrar_tick(self) -> None:
        self.instantaneas.append(self.vista())

    def exportar(self, ruta: str | Path, resumen: dict[str, Any]) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(self.como_dict(resumen), ensure_ascii=False, indent=1), encoding="utf-8")
        return ruta

    def como_dict(self, resumen: dict[str, Any]) -> dict[str, Any]:
        def limpiar(valor: Any) -> Any:
            if isinstance(valor, Enum):
                return valor.value
            if isinstance(valor, dict):
                return {limpiar(k): limpiar(v) for k, v in valor.items()}
            if isinstance(valor, list):
                return [limpiar(v) for v in valor]
            return valor
        esc = self.sim.escenario
        return limpiar({
            "version": "2.0",
            "escenario": esc.nombre,
            "config": asdict(esc.config),
            "planificador": self.sim.planificador.nombre,
            "memoria": self.sim.memoria.modo,
            "procesos": [p.pid for p in self.sim.procesos.pcbs],
            "estados": [e.value for e in Estado],
            "transiciones": [{"id": i, "de": de.value, "a": a.value, "rotulo": r}
                             for (de, a), (i, r) in TRANSICIONES.items()],
            "pasos": [asdict(p) for p in self.pasos],
            "instantaneas": self.instantaneas,
            "resumen": resumen,
        })
