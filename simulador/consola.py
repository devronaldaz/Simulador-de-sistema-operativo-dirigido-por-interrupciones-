"""Visor de texto paso a paso (requisitos R1 y R3; maqueta del Anexo E).

Lee la bitácora ya generada: no altera la simulación (opción A, sin retroceso del motor).
"""
from __future__ import annotations

import textwrap
import time
from typing import TYPE_CHECKING, Any

from .modelos import EntradaBitacora, TipoInt

if TYPE_CHECKING:
    from .nucleo import Simulador

ANCHO = 88
ABREV = {"TIMER": "T", "ES_DMA": "E", "SYSCALL": "S", "FALLO_PAG": "F", "EXCEPCION": "X", "NMI": "N",
         "WORST_TIME": "W", "SENAL": "K", "PROTECCION": "P"}
AYUDA = "[Enter] paso · t tick · c contadores · q colas · m memoria · g N ir al paso · a auto · x salir"


def _envolver(etiqueta: str, texto: str) -> str:
    sangria = " " * 11
    return textwrap.fill(texto, ANCHO, initial_indent=f"  {etiqueta:<8} ", subsequent_indent=sangria)


def contadores_linea(c: dict[str, int]) -> str:
    return " ".join(f"{ABREV[t]}:{c[t]}" for t in ABREV) + f" = {c['total']}"


def formatear_paso(e: EntradaBitacora, total: int) -> str:
    v = e.vista
    marca = f"  [INT #{e.int_id}]" if e.int_id else ""
    lineas = ["-" * ANCHO, f"PASO {e.paso}/{total} · t={e.tick} · {e.tipo_paso.value} · {e.componente}{marca}",
              _envolver("ANTES", e.antes), _envolver("DESPUÉS", e.despues), _envolver("PORQUÉ", e.causa)]
    if e.transicion:
        tr = e.transicion
        lineas.append(f"  >> Transición {tr['id']}: {tr['de']} -> {tr['a']} ({tr['pid']})")
    q = f" (quantum {v['quantum']})" if v["quantum"] else ""
    disco = ", ".join(f"{d['pid']} hasta t={d['fin']}" for d in v["disco"]) or "—"
    lineas += [
        f"  CPU={v['cpu'] or 'libre'}{q} · Listos=[{', '.join(v['listos'])}] · Disco: {disco}",
        "  Memoria: " + _memoria(v),
        "  Estados: " + " · ".join(f"{pid} {est}" for pid, est in v["estados"].items()),
        f"  INT: {contadores_linea(v['contadores'])} | "
        + " ".join(f"{pid}={n}" for pid, n in v["por_proceso"].items()),
    ]
    return "\n".join(lineas)


def _memoria(v: dict) -> str:
    partes = []
    for f in v["mapa"]:
        quien = f["proceso"] or "libre"
        if f.get("pagina") is not None:
            quien += f".{f['pagina']}"
        if f["estado"] == "Cargando":
            quien += "(cargando)"
        elif f["estado_proceso"] == "ZOMBIE":
            quien += "(zombie)"
        partes.append(f"{f['n']}:{quien}")
    return " ".join(partes)


def formatear_resumen(r: dict[str, Any]) -> str:
    tipos = [t.value for t in TipoInt]
    filas = ["=" * ANCHO, "RESUMEN FINAL", "=" * ANCHO,
             f"Planificador: {r['planificador']} · Ticks: {r['ticks']} · Pasos: {r['pasos']} · "
             f"Interrupciones: {r['interrupciones']}",
             f"Cambios de contexto: {r['cambios_contexto']} · Expropiaciones: {r['expropiaciones']} por quantum + "
             f"{r['expropiaciones_por_llegada']} por llegada/prioridad · Fallos de página: {r['fallos_pagina']} · "
             f"Reemplazos: {r['reemplazos']} · Rechazados: {r['rechazados']}",
             "Memoria: " + " · ".join(f"{k}={v}" for k, v in r["memoria"].items()), "",
             "Interrupciones por proceso y tipo (R4):",
             f"  {'Proceso':<10}" + "".join(f"{t:>11}" for t in tipos) + f"{'Total':>8}"]
    for pid, c in r["por_proceso"].items():
        filas.append(f"  {pid:<10}" + "".join(f"{c[t]:>11}" for t in tipos) + f"{sum(c.values()):>8}")
    filas.append(f"  {'TOTAL':<10}" + "".join(f"{r['por_tipo'][t]:>11}" for t in tipos) + f"{r['interrupciones']:>8}")
    tr = r["timer_resultados"]
    filas += ["", f"ISR del timer: A continúa {tr['A']} · B expropia {tr['B']} · C renueva {tr['C']} · "
                  f"D sin proceso {tr['D']}", "",
              "Métricas por proceso:",
              f"  {'Proceso':<8}{'Llegada':>8}{'Fin':>6}{'Retorno':>9}{'Espera':>8}{'Respuesta':>11}"
              f"{'Prioridad':>11}  Clase"]
    for m in r["metricas"]:
        filas.append(f"  {m['pid']:<8}{m['llegada']:>8}{str(m['fin']):>6}{str(m['retorno']):>9}"
                     f"{m['espera']:>8}{str(m['respuesta']):>11}{m['prioridad_final']:>11}  {m['clase']}"
                     + ("  (rechazado)" if m["rechazado"] else ""))
    p = r["promedios"]
    filas += [f"  Promedios: espera {p['espera']} · retorno {p['retorno']} · respuesta {p['respuesta']}",
              f"  Uso de CPU: {r['uso_cpu']} % · Rendimiento: {r['throughput']} procesos/tick",
              f"Invariantes del contador: {', '.join(r['invariantes'])}", "=" * ANCHO]
    return "\n".join(filas)


def _colas(e: EntradaBitacora) -> str:
    v = e.vista
    return (f"  Listos: [{', '.join(v['listos'])}] · Disco: "
            f"{[d['pid'] for d in v['disco']]} · Motivos: "
            + " | ".join(f"{pid}: {m or '—'}" for pid, m in v["motivos"].items()))


def recorrer(sim: "Simulador", modo: str, velocidad: float = 0.0, resumen_final: dict | None = None) -> None:
    """Muestra la bitácora: modo 'paso', 'tick', 'auto' o 'resumen'."""
    pasos = sim.bitacora.pasos
    total = len(pasos)
    print(f"Escenario: {sim.escenario.nombre}")
    cfg = sim.config
    quantum = f" (quantum {sim.planificador.quantum})" if sim.planificador.quantum else ""
    memoria = (f"MMU paginada · {cfg.marcos} marcos {cfg.reemplazo} {cfg.alcance}" if cfg.mmu == "paginada"
               else f"MMU contigua · {cfg.ajuste} ajuste")
    print(f"Planificador {sim.planificador.nombre}{quantum} · {memoria} · timer cada {cfg.periodo_timer} tick(s)")
    if modo == "resumen":
        print(formatear_resumen(resumen_final))
        return
    if modo == "paso":
        print(AYUDA)
    i, interactivo = 0, modo in ("paso", "tick")
    while i < total:
        e = pasos[i]
        print(formatear_paso(e, total))
        i += 1
        fin_de_tick = i == total or pasos[i].tick != e.tick
        if not interactivo:
            if velocidad > 0:
                time.sleep(1 / velocidad)
            continue
        if modo == "tick" and not fin_de_tick:
            continue
        while True:
            try:
                orden = input("> ").strip().lower()
            except EOFError:                       # sin teclado (p. ej. tubería): sigue en automático
                interactivo = False
                break
            if orden == "":
                break
            if orden == "x":
                print(formatear_resumen(resumen_final))
                return
            if orden == "a":
                interactivo = False
                break
            if orden == "t":
                while i < total and pasos[i].tick == e.tick:
                    print(formatear_paso(pasos[i], total))
                    i += 1
                break
            if orden == "c":
                print("  " + contadores_linea(e.contadores))
            elif orden == "q":
                print(_colas(e))
            elif orden == "m":
                for f in e.vista["mapa"]:
                    print(f"  {f['n']:>3}  {f['inicio']:>10}–{f['fin']:<10} {f['proceso'] or '—':<5} "
                          f"pág={f['pagina'] if f['pagina'] is not None else '—'}  {f['estado']:<9} {f['estado_proceso']}")
            elif orden.startswith("g"):
                try:
                    i = max(0, min(total, int(orden[1:].strip())) - 1)
                    break
                except ValueError:
                    print("  uso: g N")
            else:
                print("  " + AYUDA)
    print(formatear_resumen(resumen_final))
