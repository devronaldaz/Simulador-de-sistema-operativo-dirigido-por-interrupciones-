"""Disco con DMA: cada petición termina tras una latencia fija y avisa con IRQ14."""
from __future__ import annotations

from .modelos import PeticionDisco


class Disco:
    def __init__(self) -> None:
        self.peticiones: list[PeticionDisco] = []

    def programar(self, peticion: PeticionDisco) -> None:
        self.peticiones.append(peticion)

    def completadas(self, tick: int) -> list[PeticionDisco]:
        """Peticiones que terminan en `tick`, en orden de llegada."""
        return [p for p in self.peticiones if p.fin == tick]

    def retirar(self, tick: int) -> None:
        self.peticiones = [p for p in self.peticiones if p.fin != tick]
