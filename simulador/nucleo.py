"""Núcleo del simulador: ciclo principal por tick (sección 4.4).

Regla de oro (sección 3.3): el bucle principal solo ejecuta una instrucción,
recoge las señales y se las entrega al controlador. Ningún gestor se invoca
directamente desde aquí, salvo el despachador en el retorno de interrupción.
"""
from __future__ import annotations

import copy

from .bitacora import Bitacora
from .config import Escenario
from .contadores import ContadorInterrupciones
from .controlador_int import ControladorInterrupciones
from .cpu import CPU
from .disco import Disco
from .eventos import Agenda
from .ivt import TablaVectores
from .memoria import GestorMemoria
from .planificacion import crear_planificador
from .planificacion.despachador import Despachador
from .procesos import GestorProcesos
from .reloj import Reloj


class Simulador:
    def __init__(self, escenario: Escenario) -> None:
        self.escenario = copy.deepcopy(escenario)   # la simulación no altera el escenario original
        self.config = self.escenario.config
        self.reloj = Reloj(self.config.periodo_timer)
        self.contador = ContadorInterrupciones([p.pid for p in self.escenario.procesos])
        self.bitacora = Bitacora(self)
        self.cpu = CPU(self)
        self.disco = Disco()
        self.planificador = crear_planificador(self.config.planificador, self.config.quantum)
        self.procesos = GestorProcesos(self, self.escenario.procesos)
        self.memoria = GestorMemoria(self, self.config.marcos, self.config.reemplazo)
        self.despachador = Despachador(self)
        self.ivt = TablaVectores()
        self.controlador = ControladorInterrupciones(self)
        self.agenda = Agenda(self.escenario.eventos)
        self.expropiaciones = 0
        self.iniciado = False

    @property
    def tick(self) -> int:
        return self.reloj.tick

    def terminado(self) -> bool:
        return self.iniciado and self.procesos.todos_terminados()

    def iniciar(self) -> None:
        """Frontera t=0: llegadas iniciales y primer despacho."""
        self.iniciado = True
        self.controlador.atender_frontera(None, self.procesos.llegadas(0), False, [], False)
        self.despachador.despachar()
        self.bitacora.cerrar_tick()

    def avanzar_tick(self) -> None:
        """Un tick completo: fases F1 a F6 del informe."""
        t = self.reloj.avanzar()                                    # F1
        self.procesos.acumular_tiempos()
        senal = self.cpu.ejecutar()                                 # F2
        llegadas = self.procesos.llegadas(t)                        # F3
        fines = self.disco.completadas(t)
        nmi = "NMI" in self.agenda.extraer(t)
        self.controlador.atender_frontera(senal, llegadas, self.reloj.hay_timer(), fines, nmi)   # F4
        self.disco.retirar(t)
        self.despachador.despachar()                                # F5
        self.bitacora.cerrar_tick()                                 # F6

    def ejecutar(self) -> "Simulador":
        if not self.iniciado:
            self.iniciar()
        while not self.procesos.todos_terminados() and self.tick < self.config.max_ticks:
            self.avanzar_tick()
        return self
