"""Gestor de memoria: marcos, tablas de páginas y fallos (sección 4.2.8)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..modelos import PCB, Marco, PeticionDisco, TipoPaso
from .reemplazo import POLITICAS

if TYPE_CHECKING:
    from ..nucleo import Simulador


class GestorMemoria:
    def __init__(self, sim: "Simulador", n_marcos: int, politica: str) -> None:
        self.sim = sim
        self.marcos = [Marco(i) for i in range(n_marcos)]
        self.tablas: dict[str, dict[int, int]] = {}   # pid -> {página: marco} (solo páginas válidas)
        self.politica = politica
        self.elegir_victima = POLITICAS[politica]
        self.fallos = 0
        self.reemplazos = 0

    def __str__(self) -> str:
        return " ".join(str(m) for m in self.marcos)

    # ---- consultas -------------------------------------------------------
    def residente(self, pid: str, pagina: int) -> bool:
        return pagina in self.tablas.get(pid, {})

    def tocar(self, pid: str, pagina: int) -> Marco:
        """La CPU usó la página: actualiza la marca de último uso (LRU)."""
        marco = self.marcos[self.tablas[pid][pagina]]
        marco.ultimo_uso = self.sim.tick
        return marco

    # ---- operaciones -----------------------------------------------------
    def _elegir_marco(self) -> tuple[Marco, Marco | None]:
        libre = next((m for m in self.marcos if m.libre), None)
        if libre:
            return libre, None
        candidatos = [m for m in self.marcos if not m.en_transito]
        if not candidatos:
            raise RuntimeError("todos los marcos tienen una transferencia DMA en curso")
        return (v := self.elegir_victima(candidatos)), v

    def _invalidar(self, marco: Marco) -> str:
        """Saca la página víctima del marco y la marca inválida en la tabla de su dueño."""
        etiqueta, dueño = marco.etiqueta, marco.pid
        del self.tablas[dueño][marco.pagina]
        marco.pid = marco.pagina = None
        return f"{etiqueta} (de {dueño})"

    def cargar_inicial(self, p: PCB) -> None:
        """El cargador deja residente la página 0 al admitir el proceso."""
        marco, victima = self._elegir_marco()
        antes = str(marco)
        if victima:
            self.reemplazos += 1
            self._invalidar(marco)
        marco.pid, marco.pagina, marco.ultimo_uso, marco.cargado_en = p.pid, 0, self.sim.tick, self.sim.tick
        self.tablas.setdefault(p.pid, {})[0] = marco.id
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
            f"El cargador deja residente la página 0 (código inicial) de {p.pid} en el marco M{marco.id}.")

    def resolver_fallo(self, p: PCB, pagina: int) -> None:
        """Rutina del fallo de página: marco libre o víctima, y DMA desde disco."""
        self.fallos += 1
        mem_antes = str(self)
        usos = ", ".join(f"M{m.id}=" + ("en tránsito" if m.en_transito else f"t{m.ultimo_uso}") for m in self.marcos)
        marco, victima = self._elegir_marco()
        if victima:
            self.reemplazos += 1
            criterio = ("la menos recientemente usada" if self.politica == "LRU"
                        else "la que lleva más tiempo en memoria")
            etiqueta = victima.etiqueta
            dueño = victima.pid
            self._invalidar(marco)
            self.sim.bitacora.registrar(TipoPaso.MEM, f"Gestor de memoria ({self.politica})", mem_antes,
                f"M{marco.id}:{etiqueta} invalidada",
                f"Reemplazo {self.politica}: no hay marcos libres. Últimos usos: {usos}. Víctima = {etiqueta} "
                f"en M{marco.id} ({criterio}). Página limpia: se descarta sin swap-out y se marca inválida "
                f"en la tabla de {dueño}.")
        antes = f"M{marco.id}:{etiqueta} invalidada" if victima else mem_antes
        marco.pid, marco.pagina, marco.en_transito = p.pid, pagina, True
        fin = self.sim.tick + self.sim.config.latencia_fallo
        self.sim.disco.programar(PeticionDisco(p.pid, "pagina", fin, marco.id, pagina))
        libre = "" if victima else f"Hay un marco libre (M{marco.id}): no hace falta reemplazar. "
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(self),
            f"{libre}Se programa la transferencia DMA de {p.pid}.{pagina} hacia M{marco.id}; "
            f"terminará en t={fin} (IRQ14).")

    def completar_carga(self, peticion: PeticionDisco) -> None:
        """Fin del DMA: la página queda residente y válida."""
        marco = self.marcos[peticion.marco]
        antes = str(marco)
        marco.en_transito = False
        marco.ultimo_uso = marco.cargado_en = self.sim.tick
        self.tablas.setdefault(peticion.pid, {})[peticion.pagina] = marco.id
        self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
            f"La página {marco.etiqueta} queda residente; la tabla de páginas de {peticion.pid} marca válido (v).")

    def liberar(self, p: PCB) -> None:
        """El proceso terminó: el SO libera sus marcos."""
        for marco in self.marcos:
            if marco.pid == p.pid and not marco.en_transito:
                antes = str(marco)
                self._invalidar(marco)
                marco.ultimo_uso = -1
                self.sim.bitacora.registrar(TipoPaso.MEM, "Gestor de memoria", antes, str(marco),
                    f"{p.pid} terminó: el SO libera los recursos asignados; M{marco.id} queda libre.")
