"""Memoria contigua con registros base y límite (Semana 14).

Cada proceso ocupa una sola región. La MMU comprueba 0 ≤ d < límite y suma
la base; si no, lanza una excepción de protección. Los huecos se asignan con
primer, mejor, peor o siguiente ajuste, y al liberar se fusionan los vecinos.
Es el modelo del ejemplo del profesor (Mem. FF / BF / WF).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..modelos import PCB, Instruccion, TipoInt, TipoPaso
from .gestor import Acceso

if TYPE_CHECKING:
    from ..nucleo import Simulador


class ErrorProteccion(ValueError):
    """Desplazamiento fuera del límite de la región."""


def traducir_base_limite(base: int, limite: int, d: int) -> int:
    """PA = base + d si 0 ≤ d < límite; si no, excepción de protección."""
    if not 0 <= d < limite:
        raise ErrorProteccion(f"d={d} fuera de [0, {limite})")
    return base + d


def ajustar(huecos: list[int], tamano: int, politica: str, desde: int = 0) -> int | None:
    """Índice del hueco elegido (o None). `huecos` son tamaños en orden de dirección."""
    aptos = [i for i, h in enumerate(huecos) if h >= tamano]
    if not aptos:
        return None
    if politica == "primer":
        return aptos[0]
    if politica == "mejor":
        return min(aptos, key=lambda i: (huecos[i], i))
    if politica == "peor":
        return max(aptos, key=lambda i: (huecos[i], -i))
    if politica == "siguiente":                       # primer ajuste a partir del último asignado
        return next((i for i in aptos if i >= desde), aptos[0])
    raise ValueError(f"política de ajuste desconocida: {politica}")


@dataclass
class Region:
    inicio: int
    tamano: int
    dueño: str | None = None      # None = hueco · "SO" = sistema operativo · PID

    @property
    def fin(self) -> int:
        return self.inicio + self.tamano - 1


class GestorMemoriaContigua:
    modo = "contigua"

    def __init__(self, sim: "Simulador") -> None:
        cfg = sim.config
        self.sim = sim
        self.ajuste = cfg.ajuste
        self.regiones = [Region(0, cfg.memoria_so, "SO"), Region(cfg.memoria_so, cfg.memoria_total - cfg.memoria_so)]
        self.ultimo = 0
        self.ultima_traduccion = ""
        self.accesos = self.fallos = self.reemplazos = self.escrituras_swap = self.rechazos = 0
        self.marcos: list = []                 # sin marcos en este modo

    def __str__(self) -> str:
        return " ".join(f"[{r.inicio}-{r.fin}:{r.dueño or 'libre'}]" for r in self.regiones)

    def tamano_de(self, p: PCB) -> int:
        return p.tamano or (max(i.pagina for i in p.guion) + 1) * self.sim.config.tamano_marco

    def residente(self, pid: str, pagina: int) -> bool:
        return True

    def admitir(self, p: PCB) -> bool:
        necesario = self.tamano_de(p)
        huecos = [r for r in self.regiones if r.dueño is None]
        i = ajustar([h.tamano for h in huecos], necesario, self.ajuste, self.ultimo)
        if i is None:
            self.rechazos += 1
            libre = sum(h.tamano for h in huecos)
            self.sim.bitacora.registrar(TipoPaso.MEM, f"Gestor de memoria ({self.ajuste} ajuste)", str(self), str(self),
                f"No hay memoria suficiente para {p.pid}: necesita {necesario} B y el hueco más grande tiene "
                f"{max((h.tamano for h in huecos), default=0)} B (libre total {libre} B: fragmentación externa).")
            return False
        hueco = huecos[i]
        antes = str(self)
        self.ultimo = i
        indice = self.regiones.index(hueco)
        region = Region(hueco.inicio, necesario, p.pid)
        hueco.inicio += necesario
        hueco.tamano -= necesario
        self.regiones.insert(indice, region)
        if hueco.tamano == 0:
            self.regiones.remove(hueco)
        p.base, p.limite = region.inicio, necesario
        self.sim.bitacora.registrar(TipoPaso.MEM, f"Gestor de memoria ({self.ajuste} ajuste)", antes, str(self),
            f"{self.ajuste.capitalize()} ajuste: {p.pid} necesita {necesario} B y recibe la región "
            f"0x{region.inicio:X}–0x{region.fin:X}; base={region.inicio}, límite={necesario}"
            + (f"; sobran {hueco.tamano} B en el hueco." if hueco.tamano else "; el hueco se ocupa completo."))
        return True

    def acceder(self, p: PCB, ins: Instruccion, escritura: bool = False) -> Acceso:
        d = ins.pagina * self.sim.config.tamano_marco + (ins.desplazamiento or 0)
        self.accesos += 1
        try:
            pa = traducir_base_limite(p.base, p.limite, d)
        except ErrorProteccion:
            texto = f"MMU: d={d} ≥ límite={p.limite} → violación de protección"
            self.ultima_traduccion = texto
            return Acceso(False, texto, TipoInt.PROTECCION)
        texto = f"MMU: d={d} < límite={p.limite} → PA = base {p.base} + {d} = {pa} (0x{pa:X})"
        self.ultima_traduccion = texto
        return Acceso(True, texto)

    def vaciar_tlb(self) -> bool:
        return False

    def liberar(self, p: PCB) -> None:
        region = next((r for r in self.regiones if r.dueño == p.pid), None)
        if region is None:
            return
        antes = str(self)
        region.dueño = None
        fusionadas = []
        for r in list(self.regiones):                   # fusionar huecos vecinos
            if fusionadas and fusionadas[-1].dueño is None and r.dueño is None:
                fusionadas[-1].tamano += r.tamano
            else:
                fusionadas.append(r)
        self.regiones = fusionadas
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(self),
            f"{p.pid} terminó: su región 0x{p.base:X}–0x{p.base + p.limite - 1:X} vuelve a la lista de huecos "
            "y se fusiona con los huecos vecinos.")

    def filas(self) -> list[dict]:
        filas = []
        for n, r in enumerate(self.regiones):
            dueño = self.sim.procesos.pcb(r.dueño) if r.dueño not in (None, "SO") else None
            filas.append({"n": n, "inicio": f"0x{r.inicio:X}", "fin": f"0x{r.fin:X}", "proceso": r.dueño or "",
                          "pagina": None, "tamano": r.tamano,
                          "estado": "Libre" if r.dueño is None else "Ocupado",
                          "estado_proceso": dueño.estado.value if dueño else ("Kernel" if r.dueño == "SO" else "—"),
                          "ultimo_uso": None})
        return filas

    def tabla_paginas(self, pid: str) -> list[dict]:
        return []

    def conjunto_trabajo(self, pid: str) -> list[int]:
        return []

    def resumen(self) -> dict:
        huecos = [r.tamano for r in self.regiones if r.dueño is None]
        libre = sum(huecos)
        return {"modo": "contigua", "ajuste": self.ajuste, "accesos": self.accesos, "rechazos_por_memoria": self.rechazos,
                "memoria_libre": libre, "huecos": len(huecos),
                "fragmentacion_externa": round(1 - max(huecos) / libre, 3) if libre else 0.0}
