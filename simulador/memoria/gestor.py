"""Gestor de memoria paginada: MMU, tabla de páginas, TLB, marcos y fallos (Sesión 8, Semana 14)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..modelos import PCB, EntradaTP, Instruccion, Marco, PeticionDisco, TipoInt, TipoPaso
from .reemplazo import CRITERIOS, POLITICAS

if TYPE_CHECKING:
    from ..nucleo import Simulador


@dataclass
class Acceso:
    """Resultado de pedirle a la MMU una dirección."""
    ok: bool
    texto: str
    falla: TipoInt | None = None
    marco: int | None = None


def traducir_paginada(va: int, tamano: int, marco: int) -> tuple[int, int, int]:
    """p = ⌊VA / tamaño⌋, d = VA mod tamaño, PA = marco × tamaño + d."""
    p, d = divmod(va, tamano)
    return p, d, marco * tamano + d


class GestorMemoria:
    modo = "paginada"

    def __init__(self, sim: "Simulador") -> None:
        cfg = sim.config
        self.sim = sim
        self.tam = cfg.tamano_marco
        self.marcos = [Marco(i, del_so=i < cfg.marcos_so) for i in range(cfg.marcos_so + cfg.marcos)]
        self.tablas: dict[str, dict[int, EntradaTP]] = {}   # pid -> {página: entrada} (solo páginas presentes)
        self.politica = cfg.reemplazo
        self.elegir_victima = POLITICAS[cfg.reemplazo]
        self.alcance = cfg.alcance
        self.manecilla = cfg.marcos_so                       # Clock: empieza en el primer marco de procesos
        self.tlb_capacidad = cfg.tlb
        self.tlb: list[tuple[str, int]] = []                 # (pid, página), en orden de uso (LRU)
        self.referencias: dict[str, list[int]] = {}          # historial de páginas por proceso (conjunto de trabajo)
        self.ultima_traduccion = ""
        self.fallos = self.reemplazos = self.escrituras_swap = self.accesos = 0
        self.tlb_aciertos = self.tlb_fallos = self.tlb_vaciados = 0

    def __str__(self) -> str:
        return " ".join(str(m) for m in self.marcos if not m.del_so)

    # ---- consultas -------------------------------------------------------
    def residente(self, pid: str, pagina: int) -> bool:
        return pagina in self.tablas.get(pid, {})

    def paginas_de(self, p: PCB) -> int | None:
        return math.ceil(p.tamano / self.tam) if p.tamano else None

    # ---- MMU ---------------------------------------------------------------
    def acceder(self, p: PCB, ins: Instruccion, escritura: bool = False) -> Acceso:
        """La MMU traduce la dirección lógica; si la página no está, avisa fallo de página."""
        d = ins.desplazamiento or 0
        va = ins.pagina * self.tam + d
        n = self.paginas_de(p)
        if n is not None and ins.pagina >= n:
            return Acceso(False, f"MMU: VA={va} → p={ins.pagina} fuera del espacio de {p.pid} "
                                 f"({n} páginas) → violación de protección", TipoInt.PROTECCION)
        self.accesos += 1
        self.referencias.setdefault(p.pid, []).append(ins.pagina)
        tlb = ""
        if self.tlb_capacidad:
            clave = (p.pid, ins.pagina)
            if clave in self.tlb:
                self.tlb_aciertos += 1
                self.tlb.remove(clave)
                self.tlb.append(clave)
                tlb = "TLB: acierto · "
            else:
                self.tlb_fallos += 1
                tlb = "TLB: fallo → tabla de páginas · "
        if not self.residente(p.pid, ins.pagina):
            texto = (f"MMU: VA={va} → p={ins.pagina}, d={d} · {tlb}PTE de la página {ins.pagina}: "
                     "presente=0 → fallo de página")
            self.ultima_traduccion = texto
            return Acceso(False, texto, TipoInt.FALLO_PAG)
        entrada = self.tablas[p.pid][ins.pagina]
        if self.tlb_capacidad and (p.pid, ins.pagina) not in self.tlb:
            self.tlb.append((p.pid, ins.pagina))
            if len(self.tlb) > self.tlb_capacidad:
                self.tlb.pop(0)
        entrada.r = True
        if escritura:
            entrada.m = True
        marco = self.marcos[entrada.marco]
        marco.ultimo_uso = self.sim.tick
        _, _, pa = traducir_paginada(va, self.tam, marco.id)
        texto = (f"MMU: VA={va} → p={ins.pagina}, d={d} · {tlb}marco {marco.id} → PA={pa} (0x{pa:X})"
                 + (" · escritura: M=1" if escritura else ""))
        self.ultima_traduccion = texto
        return Acceso(True, texto, marco=marco.id)

    def vaciar_tlb(self) -> bool:
        """Cambio de contexto sin ASID: la TLB se vacía (Sesión 8, diap. 30)."""
        if self.tlb:
            self.tlb.clear()
            self.tlb_vaciados += 1
            return True
        return False

    # ---- marcos ------------------------------------------------------------
    def _candidatos(self, solicitante: str) -> list[Marco]:
        ocupados = [m for m in self.marcos if m.pid is not None and not m.en_transito and not m.del_so]
        if self.alcance == "local":
            propios = [m for m in ocupados if m.pid == solicitante]
            return propios or ocupados       # sin marcos propios no hay a quién reemplazar localmente
        return ocupados

    def _elegir_marco(self, solicitante: str) -> tuple[Marco, Marco | None]:
        libre = next((m for m in self.marcos if m.libre), None)
        if libre:
            return libre, None
        candidatos = self._candidatos(solicitante)
        if not candidatos:
            raise RuntimeError("todos los marcos tienen una transferencia DMA en curso")
        return (v := self.elegir_victima(self, candidatos)), v

    def _invalidar(self, marco: Marco) -> EntradaTP:
        dueño, pagina = marco.pid, marco.pagina
        entrada = self.tablas[dueño].pop(pagina)
        if (dueño, pagina) in self.tlb:
            self.tlb.remove((dueño, pagina))
        marco.pid = marco.pagina = None
        return entrada

    def _ocupar(self, marco: Marco, pid: str, pagina: int, en_transito: bool) -> None:
        marco.pid, marco.pagina, marco.en_transito = pid, pagina, en_transito
        if not en_transito:
            marco.ultimo_uso = marco.cargado_en = self.sim.tick
            self.tablas.setdefault(pid, {})[pagina] = EntradaTP(marco.id, r=True)
        orden = [m.id for m in self.marcos if not m.del_so]
        self.manecilla = orden[(orden.index(marco.id) + 1) % len(orden)]

    def admitir(self, p: PCB) -> bool:
        """El cargador deja residente la página 0 al admitir el proceso (si está configurado)."""
        self.tablas.setdefault(p.pid, {})
        if not self.sim.config.pagina_0_residente_al_admitir:
            return True
        marco, victima = self._elegir_marco(p.pid)
        antes = str(marco)
        if victima:
            self.reemplazos += 1
            self._invalidar(marco)
        self._ocupar(marco, p.pid, 0, en_transito=False)
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
            f"El cargador deja residente la página 0 (código inicial) de {p.pid} en el marco M{marco.id} "
            f"(direcciones físicas 0x{marco.id * self.tam:X}–0x{(marco.id + 1) * self.tam - 1:X}).")
        return True

    def resolver_fallo(self, p: PCB, pagina: int) -> None:
        """Rutina del fallo de página: validar → obtener marco → cargar (DMA) → reanudar (Semana 14)."""
        self.fallos += 1
        mem_antes = str(self)
        usos = ", ".join(f"M{m.id}=" + ("en tránsito" if m.en_transito else f"t{m.ultimo_uso}")
                         for m in self.marcos if not m.del_so)
        marco, victima = self._elegir_marco(p.pid)
        extra, etiqueta = 0, None
        if victima:
            self.reemplazos += 1
            etiqueta, dueño = victima.etiqueta, victima.pid
            entrada = self._invalidar(marco)
            if entrada.m:
                extra = self.sim.config.latencia_swap
                self.escrituras_swap += 1
                destino = f"Página modificada (M=1): se escribe en swap (+{extra} ticks de E/S)."
            else:
                destino = "Página limpia (M=0): se descarta sin escribir en swap."
            detalle = f" Últimos usos: {usos}." if self.politica == "LRU" else ""
            local = " (alcance local: solo entre sus propios marcos)" if self.alcance == "local" else ""
            self.sim.bitacora.registrar(TipoPaso.MEM, f"Gestor de memoria ({self.politica})", mem_antes,
                f"M{marco.id}:{etiqueta} invalidada",
                f"Reemplazo {self.politica}{local}: no hay marcos libres.{detalle} Víctima = {etiqueta} en "
                f"M{marco.id} ({CRITERIOS[self.politica]}). {destino} Se marca ausente en la tabla de {dueño}.")
        antes = f"M{marco.id}:{etiqueta} invalidada" if victima else mem_antes
        self._ocupar(marco, p.pid, pagina, en_transito=True)
        fin = self.sim.tick + self.sim.config.latencia_fallo + extra
        self.sim.disco.programar(PeticionDisco(p.pid, "pagina", fin, marco.id, pagina))
        libre = "" if victima else f"Hay un marco libre (M{marco.id}): no hace falta reemplazar. "
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(self),
            f"{libre}Se programa la transferencia DMA de {p.pid}.{pagina} hacia M{marco.id}; "
            f"terminará en t={fin} (IRQ14).")

    def completar_carga(self, peticion: PeticionDisco) -> None:
        """Fin del DMA: la página queda presente en la tabla de páginas."""
        marco = self.marcos[peticion.marco]
        antes = str(marco)
        marco.en_transito = False
        marco.ultimo_uso = marco.cargado_en = self.sim.tick
        self.tablas.setdefault(peticion.pid, {})[peticion.pagina] = EntradaTP(marco.id, r=True)
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
            f"La página {marco.etiqueta} queda residente; la tabla de páginas de {peticion.pid} marca presente=1.")

    def liberar(self, p: PCB) -> None:
        """El proceso terminó: el SO libera sus marcos."""
        for marco in self.marcos:
            if marco.pid == p.pid and not marco.en_transito:
                antes = str(marco)
                self._invalidar(marco)
                marco.ultimo_uso = -1
                self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
                    f"{p.pid} terminó: el SO libera los recursos asignados; M{marco.id} queda libre.")
        self.tlb = [e for e in self.tlb if e[0] != p.pid]

    # ---- vistas ------------------------------------------------------------
    def conjunto_trabajo(self, pid: str) -> list[int]:
        """W(t, Δ): páginas distintas entre las últimas Δ referencias del proceso."""
        return sorted(set(self.referencias.get(pid, [])[-self.sim.config.ws_delta:]))

    def filas(self) -> list[dict]:
        """Mapa por frames: N.º, registro inicial y final (hex), proceso o SO, página, estado del frame y del proceso."""
        filas = []
        for m in self.marcos:
            dueño = self.sim.procesos.pcb(m.pid) if m.pid else None
            filas.append({
                "n": m.id, "inicio": f"0x{m.id * self.tam:X}", "fin": f"0x{(m.id + 1) * self.tam - 1:X}",
                "proceso": "SO" if m.del_so else (m.pid or ""), "pagina": m.pagina,
                "estado": "Ocupado" if (m.del_so or m.pid) and not m.en_transito else
                          ("Cargando" if m.en_transito else "Libre"),
                "estado_proceso": dueño.estado.value if dueño else ("—" if not m.del_so else "Kernel"),
                "ultimo_uso": m.ultimo_uso if m.pid and not m.en_transito else None,
            })
        return filas

    def tabla_paginas(self, pid: str) -> list[dict]:
        return [{"pagina": pag, "marco": e.marco, "r": int(e.r), "m": int(e.m)}
                for pag, e in sorted(self.tablas.get(pid, {}).items())]

    def resumen(self) -> dict:
        cfg = self.sim.config
        p = self.fallos / self.accesos if self.accesos else 0.0
        datos = {"modo": "paginada", "accesos": self.accesos, "fallos": self.fallos, "reemplazos": self.reemplazos,
                 "escrituras_swap": self.escrituras_swap, "tasa_fallos": round(p, 4),
                 "eat_fallos_ns": round((1 - p) * cfg.ma_ns + p * cfg.trpf_ns, 1)}
        if self.tlb_capacidad:
            total = self.tlb_aciertos + self.tlb_fallos
            h = self.tlb_aciertos / total if total else 0.0
            datos.update({"tlb_aciertos": self.tlb_aciertos, "tlb_fallos": self.tlb_fallos,
                          "tlb_hit_ratio": round(h, 3), "tlb_vaciados": self.tlb_vaciados,
                          "eat_tlb_ns": round(eat_tlb(cfg.tlb_ns, h, cfg.ma_ns), 1)})
        return datos


def eat_tlb(busqueda_tlb: float, hit_ratio: float, ma: float) -> float:
    """EAT = búsqueda en TLB + h × ma + (1 − h) × 2 × ma (Sesión 8, diap. 31)."""
    return busqueda_tlb + hit_ratio * ma + (1 - hit_ratio) * 2 * ma


def eat_fallos(p: float, ma: float, trpf: float) -> float:
    """EAT = (1 − p) × ma + p × TRPF (Sesión 8, diap. 12)."""
    return (1 - p) * ma + p * trpf


def conjunto_de_trabajo(referencias: list[int], t: int, delta: int) -> set[int]:
    """W(t, Δ) sobre una cadena de referencias (t es 1-indexado)."""
    return set(referencias[max(0, t - delta):t])
