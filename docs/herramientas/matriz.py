"""Corre todas las combinaciones de configuración y escribe docs/MATRIZ_COMBINACIONES.md.

Uso (desde la raíz del repositorio):  python docs/herramientas/matriz.py
Sirve como material de estudio: "qué cambia entre todas las combinaciones".
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from simulador import Simulador, cargar_escenario, resumen  # noqa: E402


def correr(escenario: str, **cfg) -> dict:
    return resumen(Simulador(cargar_escenario(RAIZ / "escenarios" / escenario, **cfg)).ejecutar())


def fmt(x) -> str:
    return "—" if x is None else str(x).replace(".", ",")


def tabla_procesos() -> list[str]:
    filas = ["| Algoritmo | Exprop. por llegada | Prioridad | Aging | Zombie | Espera prom. | Retorno prom. | Respuesta prom. "
             "| Throughput | Cambios ctx | Exprop. quantum | Exprop. llegada | Interrup. | Orden de fin |",
             "|---|---|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    combinaciones = []
    for alg, exp, prio, aging in itertools.product(["FCFS", "SJF", "RR", "PRIORIDAD"], [False, True],
                                                   ["off", "fija", "dinamica"], [0, 4]):
        if alg == "RR" and exp:                     # RR ya expropia por quantum
            continue
        if alg == "FCFS" and exp and prio == "off":  # sin criterio no hay a quién preferir
            continue
        if alg == "PRIORIDAD" and prio == "off":    # PRIORIDAD siempre usa prioridad
            continue
        if aging and prio == "off" and alg != "PRIORIDAD":
            continue
        combinaciones.append((alg, exp, prio, aging, "inmediata"))
    combinaciones.append(("RR", False, "fija", 0, "recolector"))
    for alg, exp, prio, aging, zombie in combinaciones:
        r = correr("x_matriz_procesos.json", planificador=alg, expropiativo=exp, prioridad=prio, aging=aging,
                   politica_zombie=zombie)
        orden = " ".join(m["pid"] for m in sorted(r["metricas"], key=lambda m: (m["fin"], m["pid"])))
        p = r["promedios"]
        filas.append(f"| {r['planificador']} | {'sí' if exp else 'no'} "
                     f"| {prio} | {aging} | {zombie} | {fmt(p['espera'])} | {fmt(p['retorno'])} | {fmt(p['respuesta'])} "
                     f"| {fmt(r['throughput'])} | {r['cambios_contexto']} | {r['expropiaciones']} "
                     f"| {r['expropiaciones_por_llegada']} | {r['interrupciones']} | {orden} |")
    return filas


def tabla_memoria() -> list[str]:
    filas = ["| Reemplazo | Alcance | Marcos | TLB | Fallos de página | Reemplazos | Escrituras a swap | Hit ratio TLB "
             "| EAT con fallos (ns) | Ticks |", "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
    for rem, alc, marcos, tlb in itertools.product(["FIFO", "LRU", "OPTIMO", "CLOCK"], ["global", "local"], [3, 4], [0, 2]):
        r = correr("m3_tlb_bits_local.json", reemplazo=rem, alcance=alc, marcos=marcos, tlb=tlb)
        m = r["memoria"]
        filas.append(f"| {rem} | {alc} | {marcos} | {tlb} | {m['fallos']} | {m['reemplazos']} | {m['escrituras_swap']} "
                     f"| {fmt(m.get('tlb_hit_ratio'))} | {fmt(m['eat_fallos_ns'])} | {r['ticks']} |")
    return filas


def tabla_contigua() -> list[str]:
    filas = ["| Ajuste | Rechazos por memoria | Fragmentación externa final | Espera prom. | Retorno prom. | Ticks |",
             "|---|--:|--:|--:|--:|--:|"]
    for ajuste in ("primer", "mejor", "peor", "siguiente"):
        r = correr("m2_memoria_contigua.json", ajuste=ajuste)
        m = r["memoria"]
        filas.append(f"| {ajuste} | {m['rechazos_por_memoria']} | {fmt(m['fragmentacion_externa'])} "
                     f"| {fmt(r['promedios']['espera'])} | {fmt(r['promedios']['retorno'])} | {r['ticks']} |")
    return filas


def tabla_timer() -> list[str]:
    filas = ["| Período del timer | Quantum | IRQ0 | Interrupciones | Cambios ctx | Espera prom. | Resultados A/B/C/D |",
             "|--:|--:|--:|--:|--:|--:|---|"]
    for periodo, q in itertools.product([1, 2, 4], [2, 4, 8]):
        r = correr("e1_tres_procesos_rr4.json", periodo_timer=periodo, quantum=q)
        t = r["timer_resultados"]
        filas.append(f"| {periodo} | {q} | {r['interrupciones_timer']} | {r['interrupciones']} | {r['cambios_contexto']} "
                     f"| {fmt(r['promedios']['espera'])} | {t['A']}/{t['B']}/{t['C']}/{t['D']} |")
    return filas


def main() -> None:
    texto = [
        "# Matriz de combinaciones",
        "",
        "Generada con `python docs/herramientas/matriz.py`. Cada fila es una ejecución real del simulador; "
        "sirve para estudiar **qué cambia en cada combinación** antes de la exposición.",
        "",
        "## 1. Planificación de procesos",
        "",
        "Escenario `x_matriz_procesos.json`: dos procesos CPU-bound (C1 con prioridad 1, C2 con prioridad 2) y dos "
        "I/O-bound (I1 con prioridad 3, I2 con prioridad 4), quantum 3. Menor número = mayor prioridad.",
        "",
        *tabla_procesos(),
        "",
        "**Qué observar (en este escenario):** SJF expropiativo (SRTF) da la menor espera promedio porque atiende "
        "primero las ráfagas cortas de los I/O-bound; SJF no expropiativo no mejora a FCFS porque C1 llega solo y "
        "nadie lo interrumpe. RR sin prioridades da la mejor respuesta a costa de más cambios de contexto. Con "
        "prioridad fija terminan primero C1 y C2 (prioridad alta) y los I/O-bound esperan; con RR, prioridad "
        "dinámica y aging los I/O-bound terminan primero. La política zombie retiene recursos: más interrupciones "
        "y menor throughput. Las conclusiones dependen del escenario: no son reglas generales.",
        "",
        "## 2. Memoria paginada",
        "",
        "Escenario `m3_tlb_bits_local.json` (dos procesos, escrituras que activan el bit M, dos marcos del SO).",
        "",
        *tabla_memoria(),
        "",
        "## 3. Memoria contigua",
        "",
        "Escenario `m2_memoria_contigua.json` (como el ejemplo del profesor: región del SO y procesos de distinto tamaño).",
        "",
        *tabla_contigua(),
        "",
        "## 4. Temporizador y quantum",
        "",
        "Escenario `e1_tres_procesos_rr4.json`.",
        "",
        *tabla_timer(),
        "",
    ]
    destino = RAIZ / "docs" / "MATRIZ_COMBINACIONES.md"
    destino.write_text("\n".join(texto), encoding="utf-8")
    print(f"Escrito {destino}")


if __name__ == "__main__":
    main()
