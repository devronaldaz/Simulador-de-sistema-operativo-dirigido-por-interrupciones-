"""Métricas de planificación y resumen final (sección 8.1)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .modelos import Estado, TipoInt

if TYPE_CHECKING:
    from .nucleo import Simulador


def resumen(sim: "Simulador") -> dict[str, Any]:
    procesos = []
    for p in sim.procesos.pcbs:
        procesos.append({
            "pid": p.pid, "llegada": p.llegada, "primer_despacho": p.primer_despacho, "fin": p.fin,
            "retorno": None if p.fin is None else p.fin - p.llegada,
            "espera": p.tiempo_en_estado[Estado.LISTO],
            "en_cpu": p.tiempo_en_estado[Estado.EJECUTANDO],
            "bloqueado": p.tiempo_en_estado[Estado.BLOQUEADO],
            "respuesta": None if p.primer_despacho is None else p.primer_despacho - p.llegada,
            "instrucciones": p.instrucciones_completadas,
        })
    terminados = [m for m in procesos if m["fin"] is not None]

    def prom(clave: str) -> float | None:
        valores = [m[clave] for m in terminados]
        return round(sum(valores) / len(valores), 2) if valores else None

    ticks = sim.tick
    c = sim.contador
    return {
        "ticks": ticks,
        "pasos": len(sim.bitacora.pasos),
        "interrupciones": c.total,
        "por_tipo": {t.value: n for t, n in c.por_tipo.items()},
        "por_proceso": {pid: {t.value: n for t, n in tipos.items()} for pid, tipos in c.por_proceso.items()},
        "timer_resultados": dict(c.timer_resultados),
        "cambios_contexto": sim.despachador.cambios_contexto,
        "expropiaciones": sim.expropiaciones,
        "fallos_pagina": sim.memoria.fallos,
        "reemplazos": sim.memoria.reemplazos,
        "metricas": procesos,
        "promedios": {"espera": prom("espera"), "retorno": prom("retorno"), "respuesta": prom("respuesta")},
        "uso_cpu": round(100 * sum(m["instrucciones"] for m in procesos) / ticks, 1) if ticks else 0.0,
        "throughput": round(len(terminados) / ticks, 3) if ticks else 0.0,
        "invariantes": c.verificar(sim.bitacora.pasos, ticks, sim.config.periodo_timer) or ["OK"],
        "interrupciones_timer": c.por_tipo[TipoInt.TIMER],
    }
