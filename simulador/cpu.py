"""CPU simulada: ejecuta UNA instrucción por tick y solo señala (no decide política)."""
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
        ins = p.instruccion_actual
        mem = self.sim.memoria
        if not mem.residente(p.pid, ins.pagina):
            # Fault: la instrucción no se completa y el PC NO avanza (se reintentará).
            return Senal(TipoInt.FALLO_PAG, p.pid, "14", {"pagina": ins.pagina, "instruccion": str(ins)})
        marco = mem.tocar(p.pid, ins.pagina)
        reintento = (f" REINTENTO de la instrucción que falló en t={p.reintento_desde}."
                     if p.reintento_desde is not None else "")
        p.reintento_desde = None
        p.instrucciones_completadas += 1

        if ins.op == "cpu":
            self.sim.bitacora.registrar(TipoPaso.EXEC, "CPU", f"{p.pid}: PC={p.pc}", f"{p.pid}: PC={p.pc + 1}",
                f"Ejecuta {ins} (página {ins.pagina}, residente en M{marco.id}); "
                f"uso de M{marco.id} = t{self.sim.tick}.{reintento}")
            p.pc += 1
            return None
        if ins.op in ("syscall", "read"):
            p.pc += 1
            servicio = ins.nombre if ins.op == "syscall" else "read"
            return Senal(TipoInt.SYSCALL, p.pid, "0x80", {"servicio": servicio, "reintento": reintento})
        if ins.op == "exit":
            return Senal(TipoInt.SYSCALL, p.pid, "0x80", {"servicio": "exit", "reintento": reintento})
        return Senal(TipoInt.EXCEPCION, p.pid, "0", {"reintento": reintento})   # div0
