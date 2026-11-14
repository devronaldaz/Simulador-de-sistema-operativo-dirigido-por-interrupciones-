"""Rutinas de servicio de interrupción (ISR).

Cada ISR registra su aceptación (paso INT) y DELEGA en los gestores; la
política (a quién despachar, qué página reemplazar) vive en los gestores.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .modelos import Interrupcion, PeticionDisco, TipoPaso

if TYPE_CHECKING:
    from .nucleo import Simulador

CI = "Ctrl. de interrupciones"


def _int(sim: "Simulador", intr: Interrupcion, antes: str, despues: str, causa: str) -> None:
    sim.bitacora.registrar(TipoPaso.INT, CI, antes, despues, f"{causa} {intr.etiqueta}")


# ---------------------------------------------------------------------------
# IRQ0 · temporizador: la interrupción fundamental (secciones 2.4.12 y 4.3.1)
# ---------------------------------------------------------------------------
def isr_timer(sim: "Simulador", intr: Interrupcion) -> None:
    irr = "IRR={" + ", ".join(intr.datos["irr"]) + "}"
    espera = "; IRQ14 espera en el IRR (IF=0 durante la ISR)" if len(intr.datos["irr"]) > 1 else ""
    p = sim.cpu.actual
    res = sim.contador.timer_resultados
    if p is None:                                                   # D. sin proceso
        res["D"] += 1
        _int(sim, intr, f"{irr} · CPU libre", "IRQ0 → ISR timer; sin proceso en CPU",
             f"Timer: no hay proceso en CPU en este instante; la interrupción se atribuye al Sistema{espera}.")
        sim.controlador.atender_nmi()
        return

    q = sim.planificador.quantum
    if q is None:                                                   # algoritmo sin quantum (FCFS)
        res["A"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: {sim.planificador.nombre} no usa quantum; la ISR retorna al mismo proceso "
             f"(sin cambio de proceso){espera}.")
        sim.controlador.atender_nmi()
        return

    p.quantum_restante -= sim.reloj.periodo_timer
    usado = q - p.quantum_restante
    if p.quantum_restante > 0:                                      # A. continúa
        res["A"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: {p.pid} lleva {usado}/{q} del quantum; no se agota y la ISR retorna al mismo "
             f"proceso (sin cambio de proceso){espera}.")
        sim.controlador.atender_nmi()
    elif sim.procesos.listos and sim.planificador.debe_expropiar_por_quantum(p):   # B. expropia
        res["B"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", "IRQ0 → ISR timer; quantum agotado",
             f"Timer: quantum de {p.pid} agotado ({usado}/{q}){espera}.")
        sim.controlador.atender_nmi()
        sim.expropiaciones += 1
        listos = "[" + ", ".join(x.pid for x in sim.procesos.listos) + "]"
        sim.procesos.expropiar(p,
            f"Interrupción del timer (IRQ0); quantum agotado ({usado}/{q}); hay listos {listos}, así que el "
            f"planificador {sim.planificador.nombre} expropia la CPU y guarda el contexto de {p.pid} "
            f"(PC={p.pc}) en su PCB.")
    else:                                                           # C. renueva
        res["C"] += 1
        p.quantum_restante = q
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: quantum de {p.pid} agotado ({usado}/{q}), pero la cola de listos está vacía: el "
             f"planificador decide NO cambiar de proceso y renueva el quantum{espera}.")
        sim.controlador.atender_nmi()


# ---------------------------------------------------------------------------
# IRQ14 · fin de E/S o de transferencia DMA
# ---------------------------------------------------------------------------
def isr_disco(sim: "Simulador", intr: Interrupcion) -> None:
    pet: PeticionDisco = intr.datos["peticion"]
    p = sim.procesos.pcb(pet.pid)
    que = "la lectura pedida por" if pet.tipo == "read" else "la transferencia DMA de la página de"
    _int(sim, intr, "IRQ14 pendiente; llegó el EOI de IRQ0" if intr.datos["tras_timer"] else "IRQ14 en el IRR",
         "IRQ14 → ISR de fin de E/S/DMA", f"El disco avisa que terminó {que} {p.pid}.")
    if pet.tipo == "pagina":
        sim.memoria.completar_carga(pet)
        causa = (f"Fin de E/S/DMA (IRQ14): la página {pet.pagina} de {p.pid} ya está en memoria; "
                 f"{p.pid} podrá reintentar la instrucción que falló.")
    else:
        causa = f"Fin de E/S (IRQ14): ocurrió el evento que {p.pid} esperaba; vuelve a la cola de listos, no a la CPU."
    sim.procesos.desbloquear(p, causa)
    actual = sim.cpu.actual
    if actual is not None:
        q = sim.planificador.quantum
        resto = f" y le quedan {actual.quantum_restante}/{q} del quantum" if q else ""
        sim.bitacora.registrar(TipoPaso.SCHED, "Planificador", f"CPU={actual.pid}", f"CPU={actual.pid} (sin cambio)",
            f"{sim.planificador.nombre} no expropia cuando un proceso pasa a listos: {actual.pid} conserva la CPU"
            f"{resto}. Interrupción atendida sin cambio de proceso.")


# ---------------------------------------------------------------------------
# INT 0x80 · llamadas al sistema
# ---------------------------------------------------------------------------
def isr_syscall(sim: "Simulador", intr: Interrupcion) -> None:
    servicio = intr.datos["servicio"]
    p = sim.procesos.pcb(intr.pid)
    if servicio == "spawn":
        _int(sim, intr, f"init ejecuta INT 0x80 (spawn {p.pid})", "Vector 0x80 → ISR de llamada al sistema",
             f"Trap síncrono: se pide crear {p.pid} (equivale a fork+exec).")
        if sim.config.pagina_0_residente_al_admitir:
            sim.memoria.cargar_inicial(p)
        sim.procesos.admitir(p)
        return

    _int(sim, intr, f"{p.pid} ejecuta INT 0x80 ({servicio})", "Vector 0x80 → ISR de llamada al sistema",
         f"Trap síncrono: {p.pid} pide {servicio}(); cambio de modo usuario→kernel.{intr.datos.get('reintento', '')}")
    if servicio == "read":
        fin = sim.tick + sim.config.latencia_read
        sim.disco.programar(PeticionDisco(p.pid, "read", fin))
        sim.procesos.bloquear(p, f"read() bloqueante: el disco tarda {sim.config.latencia_read} ticks; {p.pid} "
                                 f"espera el evento «fin de E/S» (llegará en t={fin}).")
    elif servicio == "exit":
        sim.procesos.terminar(p, f"exit(): {p.pid} ejecutó su última instrucción; salida normal.")
    else:
        sim.bitacora.registrar(TipoPaso.SCHED, "Planificador", f"CPU={p.pid}", f"CPU={p.pid} (sin cambio)",
            f"{servicio}() se resolvió dentro del kernel sin esperar: la ISR retorna (IRET) al mismo proceso. "
            "Hubo cambio de modo, no cambio de contexto.")


# ---------------------------------------------------------------------------
# Vector 14 · fallo de página (fault: el PC no avanza)
# ---------------------------------------------------------------------------
def isr_fallo_pagina(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    pagina = intr.datos["pagina"]
    p.reintento_desde = sim.tick
    _int(sim, intr, f"{p.pid} ejecuta {intr.datos['instruccion']} (PC={p.pc})", "Vector 14 → ISR de fallo de página",
         f"Excepción síncrona (fault): {p.pid} referencia su página {pagina}, que no es residente "
         f"(bit válido-inválido = i). La instrucción no se completa y PC={p.pc} se conserva para reintentarla.")
    sim.memoria.resolver_fallo(p, pagina)
    sim.procesos.bloquear(p, f"Fallo de página en {p.pid}.{pagina}: {p.pid} debe esperar a que el DMA cargue "
                             "la página (evento de E/S).")


# ---------------------------------------------------------------------------
# Vector 0 · excepción irrecuperable
# ---------------------------------------------------------------------------
def isr_excepcion(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    _int(sim, intr, f"{p.pid} ejecuta una división por cero", "Vector 0 → ISR de excepción",
         f"Excepción síncrona: error aritmético irrecuperable en {p.pid}.{intr.datos.get('reintento', '')}")
    sim.procesos.terminar(p, f"Excepción (vector 0): el SO termina a {p.pid} de forma anormal.")


# ---------------------------------------------------------------------------
# NMI · no enmascarable
# ---------------------------------------------------------------------------
def isr_nmi(sim: "Simulador", intr: Interrupcion) -> None:
    if intr.datos["anidada"]:
        _int(sim, intr, "ISR(IRQ0) en curso, IF=0", "NMI atendida (anidada) y ISR(IRQ0) reanudada",
             "Llega una NMI durante la ISR del timer. IF=0 enmascara las IRQ normales pero NO la NMI: se atiende "
             "de inmediato (anidamiento); la rutina de emergencia solo registra el evento y retorna con IRET.")
    else:
        _int(sim, intr, "ejecución normal", "NMI atendida",
             "Llega una NMI: la rutina de emergencia registra el evento y retorna con IRET; no cambia estados.")
