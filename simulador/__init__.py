"""Simulador de sistema operativo dirigido por interrupciones (SI421U, UNI-FIIS)."""
from .config import Config, Escenario, ErrorEscenario, cargar_escenario, desde_dict
from .metricas import resumen
from .nucleo import Simulador

__all__ = ["Config", "Escenario", "ErrorEscenario", "Simulador", "cargar_escenario", "desde_dict", "resumen"]
__version__ = "0.1.0"
