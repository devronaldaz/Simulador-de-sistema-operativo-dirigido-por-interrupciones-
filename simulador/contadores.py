"""Contador de interrupciones (requisito R4, sección 4.8).

`contar()` es el ÚNICO punto de incremento: lo llama el controlador al aceptar
una interrupción. Así los totales se pueden verificar contra la bitácora.
"""
from __future__ import annotations

from .modelos import TipoInt, TipoPaso

SISTEMA = "SISTEMA"


class ContadorInterrupciones:
    def __init__(self, pids: list[str]) -> None:
        self.total = 0
        self.por_tipo = {t: 0 for t in TipoInt}
        self.por_proceso = {pid: {t: 0 for t in TipoInt} for pid in [*pids, SISTEMA]}
        # Resultados de la ISR del timer (tabla 4.3-C): A continúa, B expropia, C renueva, D sin proceso
        self.timer_resultados = {"A": 0, "B": 0, "C": 0, "D": 0}
        self.ultimo_tipo: str | None = None

    def contar(self, tipo: TipoInt, pid: str | None) -> int:
        """Registra una interrupción aceptada y devuelve su número (el 'INT #n')."""
        self.total += 1
        self.ultimo_tipo = tipo.value
        self.por_tipo[tipo] += 1
        self.por_proceso[pid or SISTEMA][tipo] += 1
        return self.total

    def instantanea(self) -> dict[str, int]:
        return {"total": self.total, **{t.value: n for t, n in self.por_tipo.items()}}

    def total_de(self, pid: str) -> int:
        return sum(self.por_proceso[pid].values())

    def verificar(self, pasos: list, ticks: int, periodo_timer: int) -> list[str]:
        """Comprueba los invariantes I1, I2, I3, I5 e I6. Devuelve la lista de errores."""
        errores = []
        if self.total != sum(self.por_tipo.values()):
            errores.append("I1: el total no es la suma de los tipos")
        for t in TipoInt:
            if sum(c[t] for c in self.por_proceso.values()) != self.por_tipo[t]:
                errores.append(f"I2: la suma por proceso de {t.value} no cuadra")
        filas_int = sum(1 for p in pasos if p.tipo_paso == TipoPaso.INT)
        if filas_int != self.total:
            errores.append(f"I3: {filas_int} filas INT en la bitácora frente a {self.total} contadas")
        if self.por_tipo[TipoInt.TIMER] != ticks // periodo_timer:
            errores.append("I5: las IRQ0 no son ⌊ticks / período⌋")
        if sum(self.timer_resultados.values()) != self.por_tipo[TipoInt.TIMER]:
            errores.append("I6: los resultados de la ISR del timer no suman las IRQ0")
        return errores
