"""Rutinas de servicio de interrupción (ISR).

Cada ISR registra su aceptación (paso INT) y DELEGA en los gestores; la
política (a quién despachar, qué página reemplazar) vive en los gestores.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .modelos import Estado, Interrupcion, PeticionDisco, TipoPaso

if TYPE_CHECKING:
    from .modelos import PCB
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
    plan = sim.planificador
    res = sim.contador.timer_resultados
    periodo = sim.reloj.periodo_timer

    if p is None:                                                   # D. sin proceso
        res["D"] += 1
        _int(sim, intr, f"{irr} · CPU libre", "IRQ0 → ISR timer; sin proceso en CPU",
             f"Timer: no hay proceso en CPU en este instante; la interrupción se atribuye al Sistema{espera}.")
        sim.controlador.atender_nmi()
        _tareas_periodicas(sim, None)
        return

    q = plan.quantum
    if q is None:                                                   # algoritmo sin quantum (FCFS, SJF, prioridades)
        res["A"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: {plan.nombre} no usa quantum; la ISR retorna al mismo proceso (sin cambio de proceso){espera}.")
        sim.controlador.atender_nmi()
        _tareas_periodicas(sim, p)
        return

    p.quantum_restante -= periodo
    usado = q - p.quantum_restante
    if p.quantum_restante > 0:                                      # A. continúa
        res["A"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: {p.pid} lleva {usado}/{q} del quantum; no se agota y la ISR retorna al mismo "
             f"proceso (sin cambio de proceso){espera}.")
        sim.controlador.atender_nmi()
        _tareas_periodicas(sim, p)
    elif sim.procesos.listos:                                       # B. expropia
        res["B"] += 1
        _int(sim, intr, f"{irr} · CPU={p.pid}", "IRQ0 → ISR timer; quantum agotado",
             f"Timer: quantum de {p.pid} agotado ({usado}/{q}){espera}.")
        sim.controlador.atender_nmi()
        _tareas_periodicas(sim, p)
        sim.expropiaciones += 1
        siguiente = min(sim.procesos.listos, key=plan.clave).pid
        listos = "[" + ", ".join(x.pid for x in sim.procesos.listos) + "]"
        sim.procesos.expropiar(p,
            f"Interrupción del timer (IRQ0); quantum agotado ({usado}/{q}); hay listos {listos} (el próximo "
            f"según {plan.nombre} es {siguiente}), así que se expropia la CPU y se guarda el contexto de "
            f"{p.pid} (PC={p.pc}) en su PCB.")
    else:                                                           # C. renueva
        res["C"] += 1
        p.quantum_restante = q
        _int(sim, intr, f"{irr} · CPU={p.pid}", f"IRQ0 → ISR timer; {p.pid} continúa",
             f"Timer: quantum de {p.pid} agotado ({usado}/{q}), pero la cola de listos está vacía: el "
             f"planificador decide NO cambiar de proceso y renueva el quantum{espera}.")
        sim.controlador.atender_nmi()
        _tareas_periodicas(sim, p)


def _tareas_periodicas(sim: "Simulador", p: "PCB | None") -> None:
    """Lo que el reloj sostiene además del quantum: prioridad dinámica, aging y recolección de zombies."""
    plan, cfg, periodo = sim.planificador, sim.config, sim.reloj.periodo_timer
    if p is not None and plan.prioridad_modo == "dinamica":
        p.ticks_seguidos += periodo
        ventana = plan.quantum or 4
        if p.ticks_seguidos >= ventana and p.prioridad < 9:
            p.ticks_seguidos = 0
            antes = p.prioridad
            p.prioridad += 1
            sim.bitacora.registrar(TipoPaso.SCHED, "Planificador (prioridad dinámica)", f"{p.pid}: prioridad {antes}",
                f"{p.pid}: prioridad {p.prioridad}",
                f"{p.pid} usó {ventana} ticks de CPU seguidos (comportamiento CPU-bound): su prioridad BAJA de "
                f"{antes} a {p.prioridad}. La prioridad es inversa al uso de CPU, para no castigar a los demás.")
    if cfg.aging and plan.usa_prioridad:
        for q in sim.procesos.listos:
            q.espera_aging += periodo
            if q.espera_aging >= cfg.aging and q.prioridad > 0:
                q.espera_aging = 0
                antes = q.prioridad
                q.prioridad -= 1
                sim.bitacora.registrar(TipoPaso.SCHED, "Planificador (aging)", f"{q.pid}: prioridad {antes}",
                    f"{q.pid}: prioridad {q.prioridad}",
                    f"Aging: {q.pid} lleva {cfg.aging} ticks esperando en LISTO; su prioridad SUBE de {antes} a "
                    f"{q.prioridad} para evitar la posposición indefinida.")
    for z in [x for x in sim.procesos.pcbs if x.estado == Estado.ZOMBIE]:
        if sim.tick - z.zombie_desde >= cfg.recolector_ticks:
            sim.procesos.recolectar(z)


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
    actual, plan = sim.cpu.actual, sim.planificador
    if actual is not None and not plan.mejor_que(p, actual):
        q = plan.quantum
        resto = f" y le quedan {actual.quantum_restante}/{q} del quantum" if q else ""
        razon = "no expropia cuando un proceso pasa a listos" if not plan.expropiativo else \
                f"no expropia porque {plan.describir(p)} no es mejor que {plan.describir(actual)}"
        sim.bitacora.registrar(TipoPaso.SCHED, "Planificador", f"CPU={actual.pid}", f"CPU={actual.pid} (sin cambio)",
            f"{plan.nombre} {razon}: {actual.pid} conserva la CPU{resto}. Interrupción atendida sin cambio de proceso.")


# ---------------------------------------------------------------------------
# INT 0x80 · llamadas al sistema
# ---------------------------------------------------------------------------
def isr_syscall(sim: "Simulador", intr: Interrupcion) -> None:
    servicio = intr.datos["servicio"]
    p = sim.procesos.pcb(intr.pid)
    if servicio == "spawn":
        _int(sim, intr, f"init ejecuta INT 0x80 (spawn {p.pid})", "Vector 0x80 → ISR de llamada al sistema",
             f"Trap síncrono: se pide crear {p.pid} (equivale a fork+exec; su padre es init).")
        sim.procesos.solicitar_admision(p)
        return

    _int(sim, intr, f"{p.pid} ejecuta INT 0x80 ({servicio})", "Vector 0x80 → ISR de llamada al sistema",
         f"Trap síncrono: {p.pid} pide {servicio}(); cambio de modo usuario→kernel.{intr.datos.get('reintento', '')}")
    if servicio == "read":
        fin = sim.tick + sim.config.latencia_read
        p.operaciones_es += 1
        sim.disco.programar(PeticionDisco(p.pid, "read", fin))
        if sim.planificador.prioridad_modo == "dinamica" and p.prioridad > 0:
            antes = p.prioridad
            p.prioridad -= 1
            sim.bitacora.registrar(TipoPaso.SCHED, "Planificador (prioridad dinámica)", f"{p.pid}: prioridad {antes}",
                f"{p.pid}: prioridad {p.prioridad}",
                f"{p.pid} se bloquea por E/S antes de agotar su turno (comportamiento I/O-bound): su prioridad SUBE "
                f"de {antes} a {p.prioridad}.")
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
         f"Excepción síncrona (fault): {intr.datos['mmu']}. La instrucción no se completa y PC={p.pc} se conserva "
         f"para reintentarla. Pasos: validar → obtener marco → cargar → reanudar.")
    sim.memoria.resolver_fallo(p, pagina)
    sim.procesos.bloquear(p, f"Fallo de página en {p.pid}.{pagina}: {p.pid} debe esperar a que el DMA cargue "
                             "la página (evento de E/S).")


# ---------------------------------------------------------------------------
# Excepciones que terminan el proceso
# ---------------------------------------------------------------------------
def isr_excepcion(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    _int(sim, intr, f"{p.pid} ejecuta una división por cero", "Vector 0 → ISR de excepción",
         f"Excepción síncrona: error aritmético irrecuperable en {p.pid}.{intr.datos.get('reintento', '')}")
    sim.procesos.terminar(p, f"Excepción (vector 0): el SO termina a {p.pid} de forma anormal.")


def isr_proteccion(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    _int(sim, intr, f"{p.pid} ejecuta {intr.datos['instruccion']}", "Vector 13 → ISR de violación de protección",
         f"Excepción síncrona: {intr.datos['mmu']}.")
    sim.procesos.terminar(p, f"Violación de protección: {p.pid} intentó acceder fuera de su espacio de direcciones.")


def isr_worst_time(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    wt = sim.config.worst_time
    _int(sim, intr, f"{p.pid}: {intr.datos['usado']} ticks de CPU", "Worst time → ISR de tope de ráfaga",
         f"{p.pid} alcanzó el worst time ({wt} ticks de CPU) sin terminar su ráfaga ({p.burst_total}).")
    sim.procesos.terminar(p, f"Worst time excedido: el SO corta a {p.pid} al llegar a {wt} ticks de CPU.")


def isr_senal(sim: "Simulador", intr: Interrupcion) -> None:
    p = sim.procesos.pcb(intr.pid)
    if intr.datos.get("entrega"):
        _int(sim, intr, f"{p.pid} vuelve a modo usuario con una señal pendiente", "Entrega de SIGKILL",
             f"La señal pendiente de {p.pid} se entrega al reanudarlo.")
        p.senal_pendiente = None
        sim.procesos.terminar(p, f"{p.pid} terminó por la señal SIGKILL.")
        return
    if p.estado == Estado.EJECUTANDO:
        _int(sim, intr, f"kill({p.pid})", "SIGKILL → ISR de señales", f"Se envía SIGKILL a {p.pid}, que está en la CPU.")
        sim.procesos.terminar(p, f"{p.pid} terminó por la señal SIGKILL.")
    elif p.estado in (Estado.ZOMBIE, Estado.TERMINADO):
        _int(sim, intr, f"kill({p.pid})", "SIGKILL ignorada", f"{p.pid} ya finalizó: la señal no tiene efecto.")
    else:
        p.senal_pendiente = "SIGKILL"
        _int(sim, intr, f"kill({p.pid})", f"SIGKILL pendiente en el PCB de {p.pid}",
             f"{p.pid} está en {p.estado.value}: la señal queda pendiente y se entregará cuando vuelva a ejecutar.")


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
