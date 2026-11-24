"""Gestión de memoria: paginada (MMU, TLB, reemplazo) o contigua (base y límite)."""
from .contigua import GestorMemoriaContigua
from .gestor import GestorMemoria


def crear_gestor(sim):
    return GestorMemoriaContigua(sim) if sim.config.mmu == "contigua" else GestorMemoria(sim)


__all__ = ["GestorMemoria", "GestorMemoriaContigua", "crear_gestor"]
