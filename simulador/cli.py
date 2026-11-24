"""Interfaz de línea de comandos (sección 6.3)."""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .config import OPCIONES, ErrorEscenario, cargar_escenario
from .consola import recorrer
from .metricas import resumen
from .nucleo import Simulador

RAIZ = Path(__file__).resolve().parent.parent


def _bool(texto: str) -> bool:
    if texto.lower() in ("si", "sí", "true", "1", "yes"):
        return True
    if texto.lower() in ("no", "false", "0"):
        return False
    raise argparse.ArgumentTypeError("use si o no")


def construir_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m simulador",
        description="Simulador de SO dirigido por interrupciones: procesos, memoria y bitácora paso a paso.")
    ap.add_argument("escenario", help="archivo JSON del escenario (ver escenarios/)")
    ap.add_argument("--modo", choices=["paso", "tick", "auto", "resumen"], default="paso",
                    help="paso: un paso por Enter (principal) · tick: un tick por Enter · "
                         "auto: todo seguido · resumen: solo el resumen final")
    ap.add_argument("--velocidad", type=float, default=0.0, help="pasos por segundo en modo auto (0 = sin pausa)")
    ap.add_argument("--traza", metavar="RUTA", help="guarda la bitácora en JSON")
    ap.add_argument("--visor", action="store_true", help="prepara la traza para visor/index.html")
    ap.add_argument("--abrir", action="store_true", help="con --visor, abre el visor en el navegador")
    g = ap.add_argument_group("sustituir la configuración del escenario (todas las opciones del JSON)")
    for nombre, opciones in OPCIONES.items():
        g.add_argument(f"--{nombre.replace('_', '-')}", dest=nombre, choices=sorted(opciones))
    for nombre in ("quantum", "aging", "worst_time", "recolector_ticks", "grado_multiprogramacion", "marcos",
                   "marcos_so", "tamano_marco", "tlb", "periodo_timer", "memoria_total", "memoria_so", "ws_delta"):
        g.add_argument(f"--{nombre.replace('_', '-')}", dest=nombre, type=int)
    g.add_argument("--expropiativo", type=_bool, metavar="si|no")
    return ap


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = construir_parser().parse_args(argv)
    parametros = {k: v for k, v in vars(args).items()
                  if k not in ("escenario", "modo", "velocidad", "traza", "visor", "abrir")}
    try:
        escenario = cargar_escenario(args.escenario, **parametros)
    except (OSError, ErrorEscenario) as exc:
        print(f"Error en el escenario: {exc}", file=sys.stderr)
        return 2

    sim = Simulador(escenario).ejecutar()
    res = resumen(sim)

    if args.traza:
        print(f"Bitácora guardada en {sim.bitacora.exportar(args.traza, res)}")
    if args.visor:
        datos = json.dumps(sim.bitacora.como_dict(res), ensure_ascii=False)
        destino = RAIZ / "visor" / "traza_actual.js"
        destino.write_text(f"window.TRAZA = {datos};\n", encoding="utf-8")
        indice = RAIZ / "visor" / "index.html"
        print(f"Visor listo: abra {indice}")
        if args.abrir:
            webbrowser.open(indice.as_uri())
        if args.modo == "paso":
            args.modo = "resumen"
    recorrer(sim, args.modo, args.velocidad, res)
    return 0
