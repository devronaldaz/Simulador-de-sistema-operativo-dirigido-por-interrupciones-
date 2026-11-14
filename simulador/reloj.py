"""Reloj lógico y temporizador (IRQ0). Ver informe, secciones 2.4.12 y 4.3.1."""
from __future__ import annotations


class Reloj:
    def __init__(self, periodo_timer: int = 1) -> None:
        self.tick = 0
        self.periodo_timer = periodo_timer

    def avanzar(self) -> int:
        self.tick += 1
        return self.tick

    def hay_timer(self) -> bool:
        """IRQ0 se levanta cada `periodo_timer` ticks (por defecto, en cada tick)."""
        return self.tick > 0 and self.tick % self.periodo_timer == 0
