"""Bitácora transaccional, opción A (requisito R6, sección 4.7).

Cada paso guarda estado antes, estado después y causa, más una "vista" del
sistema completo para que el visor pueda mostrar cualquier paso.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .modelos import EntradaBitacora, TipoPaso

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
            contadores=self.sim.contador.instantanea(), transicion=transicion, vista=self.vista())
        self.pasos.append(entrada)
        return entrada

    def vista(self) -> dict[str, Any]:
        """Estado completo del sistema tras el paso (lo usa el visor)."""
        sim = self.sim
        actual = sim.cpu.actual
        q = sim.planificador.quantum
        return {
            "tick": sim.tick,
            "cpu": actual.pid if actual else None,
            "quantum": (f"{q - actual.quantum_restante}/{q}"
                        if actual and q and actual.quantum_restante is not None else None),
            "listos": [p.pid for p in sim.procesos.listos],
            "disco": [{"pid": d.pid, "tipo": d.tipo, "fin": d.fin} for d in sim.disco.peticiones],
            "marcos": [{"id": m.id, "pagina": m.etiqueta, "cargando": m.en_transito,
                        "ultimo_uso": m.ultimo_uso} for m in sim.memoria.marcos],
            "estados": {p.pid: p.estado.value for p in sim.procesos.pcbs},
            "motivos": {p.pid: p.motivo_ultimo_cambio for p in sim.procesos.pcbs},
            "contadores": sim.contador.instantanea(),
            "por_proceso": {pid: sum(c.values()) for pid, c in sim.contador.por_proceso.items()},
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
            "version": "1.0",
            "escenario": esc.nombre,
            "config": asdict(esc.config),
            "procesos": [p.pid for p in self.sim.procesos.pcbs],
            "pasos": [asdict(p) for p in self.pasos],
            "instantaneas": self.instantaneas,
            "resumen": resumen,
        })
