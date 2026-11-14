"""Utilidades comunes de las pruebas."""
from __future__ import annotations

from pathlib import Path

from simulador import Simulador, cargar_escenario, resumen

RAIZ = Path(__file__).resolve().parent.parent
ESCENARIOS = RAIZ / "escenarios"
DATOS = Path(__file__).resolve().parent / "datos"


def correr(nombre: str, **config):
    """Ejecuta un escenario de la carpeta escenarios/ y devuelve (simulador, resumen)."""
    sim = Simulador(cargar_escenario(ESCENARIOS / nombre, **config)).ejecutar()
    return sim, resumen(sim)
