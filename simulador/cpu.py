"""CPU simulada: ejecuta UNA instrucción por tick a través de la MMU y solo señala (no decide política)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .modelos import PCB, Senal, TipoInt, TipoPaso

if TYPE_CHECKING:
    from .nucleo import Simulador


class CPU:
    def __init__(self, sim: "Simulador") -> None:
        self.sim = sim
        self.actual: PCB | None = None

    def ejecutar(self) -> Senal | None:
        """Fase F2 del tick. Devuelve la señal síncrona que produjo la instrucción, si hubo."""
        p = self.actual
        if p is None:
            return None
        if p.senal_pendiente:                 # la señal se entrega al volver a modo usuario
            return Senal(TipoInt.SENAL, p.pid, "SIG", {"entrega": True, "senal": p.senal_pendiente})
        ins = p.instruccion_actual
        acceso = self.sim.memoria.acceder(p, ins, escritura=ins.op == "write")
        if not acceso.ok:
            if acceso.falla == TipoInt.FALLO_PAG:
                # Fault: la instrucción no se completa y el PC NO avanza (se reintentará).
                return Senal(TipoInt.FALLO_PAG, p.pid, "14",
                             {"pagina": ins.pagina, "instruccion": str(ins), "mmu": acceso.texto})
            return Senal(TipoInt.PROTECCION, p.pid, "13", {"instruccion": str(ins), "mmu": acceso.texto})

        reintento = (f" REINTENTO de la instrucción que falló en t={p.reintento_desde}."
                     if p.reintento_desde is not None else "")
        p.reintento_desde = None
        p.instrucciones_completadas += 1
        p.cpu_usado += 1
        cfg = self.sim.config

        if ins.op in ("cpu", "write"):
            self.sim.bitacora.registrar(TipoPaso.EXEC, "CPU", f"{p.pid}: PC={p.pc}", f"{p.pid}: PC={p.pc + 1}",
                f"Ejecuta {ins}. {acceso.texto}; uso del marco = t{self.sim.tick}.{reintento}")
            p.pc += 1
            if cfg.worst_time and cfg.worst_time_modo == "truncar" and p.cpu_usado >= cfg.worst_time:
                return Senal(TipoInt.WORST_TIME, p.pid, "WT", {"usado": p.cpu_usado})
            return None
        if ins.op in ("syscall", "read"):
            p.pc += 1
            servicio = ins.nombre if ins.op == "syscall" else "read"
            return Senal(TipoInt.SYSCALL, p.pid, "0x80", {"servicio": servicio, "reintento": reintento})
        if ins.op == "exit":
            return Senal(TipoInt.SYSCALL, p.pid, "0x80", {"servicio": "exit", "reintento": reintento})
        return Senal(TipoInt.EXCEPCION, p.pid, "0", {"reintento": reintento})   # div0
