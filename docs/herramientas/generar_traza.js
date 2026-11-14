// Implementación de referencia MÍNIMA del simulador dirigido por interrupciones.
// Sirve para GENERAR y VERIFICAR la traza del capítulo 5 del informe
// (3 procesos, Round Robin q=4, 3 marcos, LRU). No es el simulador final.
//
// Uso:  node generar_traza.js --trace | --snap | --counters | --metrics | --json
// Variables de entorno opcionales: CFG='{"Q":1000}'  ESC='{...}'
'use strict';

// ---------- Configuración y escenario ----------
const CFG = Object.assign({ Q: 4, FRAMES: 3, IO_LAT: 4, PF_LAT: 3, NMI_AT: 12 },
  process.env.CFG ? JSON.parse(process.env.CFG) : {});
const ESC = Object.assign({
  P1: { llegada: 0, prog: ['c0', 'c0', 'c0', 'c0', 'c1', 'c1', 'c1', 'c1', 'c1', 'exit1'] },
  P2: { llegada: 0, prog: ['c0', 'read0', 'c0', 'c0', 'c0', 'exit0'] },
  P3: { llegada: 2, prog: ['c0', 'sys0', 'c0', 'c0', 'c0', 'div0'] },
}, process.env.ESC ? JSON.parse(process.env.ESC) : {});

const TIPOS = ['TIMER', 'ES_DMA', 'SYSCALL', 'FALLO_PAG', 'EXCEPCION', 'NMI'];
const ABREV = { TIMER: 'T', ES_DMA: 'E', SYSCALL: 'S', FALLO_PAG: 'F', EXCEPCION: 'X', NMI: 'N' };
const NOM = { N: 'NUEVO', L: 'LISTO', E: 'EJECUTANDO', B: 'BLOQUEADO', T: 'TERMINADO' };
const cero = () => Object.fromEntries(TIPOS.map(t => [t, 0]));

// ---------- Estado del sistema ----------
let tick = 0, paso = 0, total = 0, cambiosCtx = 0, expropiaciones = 0, fallos = 0, reemplazos = 0;
const log = [], sysCnt = cero(), SIS = { cnt: cero() };
const pcb = {};
for (const [n, d] of Object.entries(ESC)) {
  pcb[n] = { pid: n, estado: 'N', pc: 0, prog: d.prog, llegada: d.llegada, q: 0, cnt: cero(),
    motivo: '-', tEst: { L: 0, E: 0, B: 0 }, primeraCPU: null, fin: null, cpu: 0, reintento: null };
}
const listos = [], colaDisco = [], disco = [];
let cpu = null;
const marcos = Array.from({ length: CFG.FRAMES }, (_, i) => ({ id: i, pag: null, uso: -1, carga: false }));
const pt = Object.fromEntries(Object.keys(pcb).map(n => [n, {}]));

// ---------- Utilidades ----------
const q2s = a => '[' + a.map(p => p.pid).join(', ') + ']';
const mem2s = () => marcos.map(m => m.pag === null ? `M${m.id}:libre` : `M${m.id}:${m.pag}${m.carga ? '(cargando)' : ''}`).join(' ');
const cnt2s = () => TIPOS.map(t => `${ABREV[t]}:${sysCnt[t]}`).join(' ') + ` = ${total}`;
let ultimoTipo = null;
function step(kind, comp, antes, despues, causa) {
  paso++; log.push({ n: paso, t: tick, kind, comp, antes, despues, causa, total, sys: { ...sysCnt }, intTipo: kind === 'INT' ? ultimoTipo : undefined, intId: kind === 'INT' ? total : undefined });
}
function setEstado(p, nuevo, comp, causa, antesExtra, despExtra) {
  step('TRANS', comp, `${p.pid}: ${NOM[p.estado]} · ${antesExtra}`, `${p.pid}: ${NOM[nuevo]} · ${despExtra}`, causa);
  p.estado = nuevo; p.motivo = causa;
}
function contar(tipo, p) { ultimoTipo = tipo; sysCnt[tipo]++; total++; (p ? p.cnt : SIS.cnt)[tipo]++; }
const tag = () => `[INT #${total}]`;

// ---------- Memoria ----------
function elegirMarco() {
  const libre = marcos.find(x => x.pag === null && !x.carga);
  if (libre) return { m: libre, victima: null };
  const cand = marcos.filter(x => !x.carga).sort((a, b) => a.uso - b.uso || a.id - b.id);
  if (!cand.length) throw new Error('todos los marcos en tránsito');
  return { m: cand[0], victima: cand[0].pag };
}
function liberarProceso(p) {
  for (const m of marcos) if (m.pag && !m.carga && m.pag.startsWith(p.pid + '.')) {
    const ant = `M${m.id}:${m.pag}`; delete pt[p.pid][m.pag.split('.')[1]];
    m.pag = null; m.uso = -1;
    step('MEM', 'Gestor de memoria', ant, `M${m.id}:libre`, `${p.pid} terminó: el SO libera los recursos asignados (Sesión 4 – Gestión); M${m.id} queda libre.`);
  }
}

// ---------- Planificador / despachador ----------
function despachar() {
  if (cpu !== null) return;
  if (!listos.length) {
    step('SCHED', 'Planificador', 'CPU libre · cola listos []', 'CPU ociosa (proceso inactivo)', 'No hay procesos listos: la CPU queda ociosa hasta la próxima interrupción.');
    return;
  }
  const antes = q2s(listos), p = listos.shift();
  cambiosCtx++; p.q = CFG.Q; if (p.primeraCPU === null) p.primeraCPU = tick;
  setEstado(p, 'E', 'Despachador (cambio de contexto)',
    `Despacho: el planificador RR toma la cabeza de la cola de listos ${antes}; el despachador restaura el contexto de ${p.pid} (PC=${p.pc}) desde su PCB y le asigna un quantum de ${CFG.Q}.`,
    `cola listos ${antes}`, `CPU=${p.pid} · cola listos ${q2s(listos)}`);
  cpu = p;
}

// ---------- Fase de ejecución del tick ----------
function ejecutarTick() {
  for (const p of Object.values(pcb)) if (p.estado === 'L' || p.estado === 'E' || p.estado === 'B') p.tEst[p.estado]++;
  if (!cpu) return null;
  const p = cpu, ins = p.prog[p.pc], op = ins.replace(/[0-9]+$/, ''), pag = ins.match(/[0-9]+$/)[0];
  if (pt[p.pid][pag] === undefined) return { tipo: 'FALLO_PAG', p, pag, ins };
  const m = marcos[pt[p.pid][pag]]; m.uso = tick;
  const reint = p.reintento !== null ? ` REINTENTO de la instrucción que falló en t=${p.reintento}.` : '';
  p.reintento = null; p.cpu++;
  if (op === 'c') {
    step('EXEC', 'CPU', `${p.pid}: PC=${p.pc}`, `${p.pid}: PC=${p.pc + 1}`,
      `Ejecuta ${ins} (página ${pag}, residente en M${m.id}); uso de M${m.id} = t${tick}.${reint}`);
    p.pc++; return null;
  }
  if (op === 'sys') { p.pc++; return { tipo: 'SYSCALL', p, nombre: 'getpid', reint }; }
  if (op === 'read') { p.pc++; return { tipo: 'SYSCALL', p, nombre: 'read', bloq: true, reint }; }
  if (op === 'exit') return { tipo: 'SYSCALL', p, nombre: 'exit', fin: true, reint };
  if (op === 'div') return { tipo: 'EXCEPCION', p, reint };
}

// ---------- Tratamiento de una frontera de tick ----------
function nmi(dueño) {
  contar('NMI', dueño);
  step('INT', 'Ctrl. de interrupciones', 'ISR(IRQ0) en curso, IF=0', 'NMI atendida (anidada) y ISR(IRQ0) reanudada',
    `Llega una NMI durante la ISR del timer. IF=0 enmascara las IRQ normales pero NO la NMI: se atiende de inmediato (anidamiento), la rutina de emergencia solo registra el evento y retorna con IRET. ${tag()}`);
}
function frontera() {
  const sync = ejecutarTick();
  const llegadas = tick === 0 ? [] : Object.values(pcb).filter(p => p.estado === 'N' && p.llegada === tick);
  const finDisco = disco.filter(d => d.fin === tick);

  // (1) interrupción síncrona originada en la instrucción ejecutada
  if (sync) {
    const p = sync.p;
    if (sync.tipo === 'FALLO_PAG') {
      contar('FALLO_PAG', p); fallos++; p.reintento = tick;
      step('INT', 'Ctrl. de interrupciones', `${p.pid} ejecuta ${sync.ins} (PC=${p.pc})`, 'Vector 14 → ISR de fallo de página',
        `Excepción síncrona (fault): ${p.pid} referencia su página ${sync.pag}, que no es residente (bit válido-inválido = i). La instrucción no se completa y PC=${p.pc} se conserva para reintentarla. ${tag()}`);
      const memAntes = mem2s();
      const usos = marcos.map(x => `M${x.id}=${x.carga ? 'en tránsito' : 't' + x.uso}`).join(', ');
      const { m, victima } = elegirMarco();
      if (victima) {
        reemplazos++; const [vp, vpag] = victima.split('.');
        step('MEM', 'Gestor de memoria (LRU)', memAntes, `M${m.id}:${victima} invalidada`,
          `Reemplazo LRU: no hay marcos libres. Últimos usos: ${usos}. Víctima = ${victima} en M${m.id} (la menos recientemente usada). Página limpia: se descarta sin swap-out y se marca inválida en la tabla de ${vp}.`);
        delete pt[vp][vpag];
      }
      m.pag = `${p.pid}.${sync.pag}`; m.carga = true;
      disco.push({ pid: p.pid, fin: tick + CFG.PF_LAT, tipo: 'pagein', marco: m.id, pag: sync.pag });
      step('MEM', 'Gestor de memoria', victima ? `M${m.id}:${victima} invalidada` : memAntes, mem2s(),
        `${victima ? '' : `Hay un marco libre (M${m.id}): no hace falta reemplazar. `}Se programa la transferencia DMA de ${p.pid}.${sync.pag} hacia M${m.id}; terminará en t=${tick + CFG.PF_LAT} (IRQ14).`);
      const antesD = q2s(colaDisco); colaDisco.push(p);
      setEstado(p, 'B', 'Gestor de procesos',
        `Fallo de página en ${p.pid}.${sync.pag}: ${p.pid} debe esperar a que el DMA cargue la página (evento de E/S).`,
        `CPU=${p.pid} · cola disco ${antesD}`, `CPU libre · cola disco ${q2s(colaDisco)}`);
      cpu = null;
    } else if (sync.tipo === 'SYSCALL') {
      contar('SYSCALL', p);
      step('INT', 'Ctrl. de interrupciones', `${p.pid} ejecuta INT 0x80 (${sync.nombre})`, 'Vector 0x80 → ISR de llamada al sistema',
        `Trap síncrono: ${p.pid} pide ${sync.nombre}(); cambio de modo usuario→kernel.${sync.reint} ${tag()}`);
      if (sync.bloq) {
        disco.push({ pid: p.pid, fin: tick + CFG.IO_LAT, tipo: 'read' });
        const antesD = q2s(colaDisco); colaDisco.push(p);
        setEstado(p, 'B', 'Gestor de procesos',
          `read() bloqueante: el disco tarda ${CFG.IO_LAT} ticks; ${p.pid} espera el evento «fin de E/S» (llegará en t=${tick + CFG.IO_LAT}).`,
          `CPU=${p.pid} · cola disco ${antesD}`, `CPU libre · cola disco ${q2s(colaDisco)}`);
        cpu = null;
      } else if (sync.fin) {
        setEstado(p, 'T', 'Gestor de procesos', `exit(): ${p.pid} ejecutó su última instrucción; salida normal.`, `CPU=${p.pid}`, 'CPU libre');
        p.fin = tick; cpu = null; liberarProceso(p);
      } else {
        step('SCHED', 'Planificador', `CPU=${p.pid}`, `CPU=${p.pid} (sin cambio)`,
          `${sync.nombre}() se resolvió dentro del kernel sin esperar: la ISR retorna (IRET) al mismo proceso. Hubo cambio de modo, no cambio de contexto.`);
      }
    } else if (sync.tipo === 'EXCEPCION') {
      contar('EXCEPCION', p);
      step('INT', 'Ctrl. de interrupciones', `${p.pid} ejecuta una división por cero`, 'Vector 0 → ISR de excepción',
        `Excepción síncrona: error aritmético irrecuperable en ${p.pid}.${sync.reint} ${tag()}`);
      setEstado(p, 'T', 'Gestor de procesos', `Excepción (vector 0): el SO termina a ${p.pid} de forma anormal.`, `CPU=${p.pid}`, 'CPU libre');
      p.fin = tick; cpu = null; liberarProceso(p);
    }
  }

  // (2) llegadas (spawn = INT 0x80 emitida por el proceso init simulado)
  for (const p of llegadas) admitir(p);

  // (3) IRQ0 (timer, cada P ticks; P=1 por defecto) y IRQ14 (fin de DMA), en orden de prioridad
  const P = CFG.P || 1, hayTimer = tick % P === 0;
  const irr = (hayTimer ? ['IRQ0'] : []).concat(finDisco.map(() => 'IRQ14'));
  const resto = hayTimer && irr.length > 1 ? `; IRQ14 espera en el IRR (IF=0 durante la ISR)` : '';
  const dueño = cpu;
  const marca = (res, usado) => { const r = log[log.length - 1]; r.timer = { pid: dueño ? dueño.pid : 'SIS', usado, res }; };
  if (hayTimer) {
    contar('TIMER', dueño);
    if (dueño) {
      dueño.q -= P; const usado = CFG.Q - dueño.q;
      const antesC = `IRR={${irr.join(', ')}} · CPU=${dueño.pid}`;
      if (dueño.q > 0) {
        step('INT', 'Ctrl. de interrupciones', antesC, `IRQ0 → ISR timer; ${dueño.pid} continúa`,
          `Timer: ${dueño.pid} lleva ${usado}/${CFG.Q} del quantum; no se agota y la ISR retorna al mismo proceso (sin cambio de proceso)${resto}. ${tag()}`);
        marca('continúa', usado);
        if (CFG.NMI_AT === tick) nmi(dueño);
      } else if (listos.length) {
        step('INT', 'Ctrl. de interrupciones', antesC, 'IRQ0 → ISR timer; quantum agotado',
          `Timer: quantum de ${dueño.pid} agotado (${usado}/${CFG.Q})${resto}. ${tag()}`);
        marca('expropia', usado);
        if (CFG.NMI_AT === tick) nmi(dueño);
        expropiaciones++;
        const antesL = q2s(listos); listos.push(dueño);
        setEstado(dueño, 'L', 'Planificador RR (cambio de contexto)',
          `Interrupción del timer (IRQ0); quantum agotado (${usado}/${CFG.Q}); hay listos ${antesL}, así que el planificador RR expropia la CPU y guarda el contexto de ${dueño.pid} (PC=${dueño.pc}) en su PCB.`,
          `CPU=${dueño.pid} · cola listos ${antesL}`, `CPU libre · cola listos ${q2s(listos)}`);
        cpu = null;
      } else {
        dueño.q = CFG.Q;
        step('INT', 'Ctrl. de interrupciones', antesC, `IRQ0 → ISR timer; ${dueño.pid} continúa`,
          `Timer: quantum de ${dueño.pid} agotado (${usado}/${CFG.Q}), pero la cola de listos está vacía: el planificador RR decide NO cambiar de proceso y renueva el quantum${resto}. ${tag()}`);
        marca('renueva', usado);
        if (CFG.NMI_AT === tick) nmi(dueño);
      }
    } else {
      step('INT', 'Ctrl. de interrupciones', `IRR={${irr.join(', ')}} · CPU libre`, 'IRQ0 → ISR timer; sin proceso en CPU',
        `Timer: no hay proceso en CPU en este instante; la interrupción se atribuye al Sistema${resto}. ${tag()}`);
      marca('sin proceso', 0);
      if (CFG.NMI_AT === tick) nmi(null);
    }
  } else if (CFG.NMI_AT === tick) nmi(cpu);
  for (const d of finDisco) {
    const p = pcb[d.pid]; contar('ES_DMA', p);
    step('INT', 'Ctrl. de interrupciones', hayTimer ? 'IRQ14 pendiente; llegó el EOI de IRQ0' : 'IRQ14 en el IRR', 'IRQ14 → ISR de fin de E/S/DMA',
      `El disco avisa que terminó ${d.tipo === 'read' ? 'la lectura pedida por' : 'la transferencia DMA de la página de'} ${p.pid}. ${tag()}`);
    if (d.tipo === 'pagein') {
      const m = marcos[d.marco]; m.carga = false; m.uso = tick; pt[p.pid][d.pag] = m.id;
      step('MEM', 'Gestor de memoria', `M${m.id}:${m.pag}(cargando)`, `M${m.id}:${m.pag}`,
        `La página ${m.pag} queda residente; la tabla de páginas de ${p.pid} marca válido (v).`);
    }
    const antesD = q2s(colaDisco); colaDisco.splice(colaDisco.indexOf(p), 1);
    const antesL = q2s(listos); listos.push(p);
    setEstado(p, 'L', 'Gestor de procesos',
      d.tipo === 'read' ? `Fin de E/S (IRQ14): ocurrió el evento que ${p.pid} esperaba; vuelve a la cola de listos, no a la CPU.`
        : `Fin de E/S/DMA (IRQ14): la página ${d.pag} de ${p.pid} ya está en memoria; ${p.pid} podrá reintentar la instrucción que falló.`,
      `cola disco ${antesD} · cola listos ${antesL}`, `cola disco ${q2s(colaDisco)} · cola listos ${q2s(listos)}`);
    if (cpu) step('SCHED', 'Planificador', `CPU=${cpu.pid}`, `CPU=${cpu.pid} (sin cambio)`,
      `Round Robin no expropia cuando un proceso pasa a listos: ${cpu.pid} conserva la CPU y le quedan ${cpu.q}/${CFG.Q} del quantum. Interrupción atendida sin cambio de proceso.`);
  }
  disco.splice(0, disco.length, ...disco.filter(d => d.fin !== tick));

  // (4) retorno de la interrupción: si la CPU quedó libre se despacha
  despachar();
  log.push({ n: null, t: tick, kind: 'SNAP', cpu: cpu ? cpu.pid : null, listos: q2s(listos), disco: q2s(colaDisco), mem: mem2s(),
    est: Object.values(pcb).map(p => `${p.pid}:${NOM[p.estado]}`).join(' · '), cnt: cnt2s(),
    porProc: Object.values(pcb).map(p => `${p.pid}=${TIPOS.reduce((a, t) => a + p.cnt[t], 0)}`).join(' ') + ` SIS=${TIPOS.reduce((a, t) => a + SIS.cnt[t], 0)}` });
}
function admitir(p) {
  contar('SYSCALL', p);
  step('INT', 'Ctrl. de interrupciones', `init ejecuta INT 0x80 (spawn ${p.pid})`, 'Vector 0x80 → ISR de llamada al sistema',
    `Trap síncrono: se pide crear ${p.pid} (equivale a fork+exec). ${tag()}`);
  const { m, victima } = elegirMarco();
  if (victima) throw new Error('el escenario no debe reemplazar durante la admisión');
  m.pag = `${p.pid}.0`; m.uso = tick; pt[p.pid]['0'] = m.id;
  step('MEM', 'Gestor de memoria', `M${m.id}:libre`, `M${m.id}:${p.pid}.0`,
    `El cargador deja residente la página 0 (código inicial) de ${p.pid} en el marco libre M${m.id}.`);
  const antes = q2s(listos); listos.push(p);
  setEstado(p, 'L', 'Gestor de procesos',
    `Admisión: el SO creó el PCB de ${p.pid} y completó su preparación; entra al final de la cola de listos.`,
    `en creación · cola listos ${antes}`, `cola listos ${q2s(listos)}`);
}

// ---------- Ciclo principal ----------
tick = 0;
for (const p of Object.values(pcb).filter(p => p.llegada === 0)) admitir(p);
despachar();
log.push({ n: null, t: 0, kind: 'SNAP', cpu: cpu ? cpu.pid : null, listos: q2s(listos), disco: q2s(colaDisco), mem: mem2s(),
  est: Object.values(pcb).map(p => `${p.pid}:${NOM[p.estado]}`).join(' · '), cnt: cnt2s(),
  porProc: Object.values(pcb).map(p => `${p.pid}=${TIPOS.reduce((a, t) => a + p.cnt[t], 0)}`).join(' ') + ` SIS=${TIPOS.reduce((a, t) => a + SIS.cnt[t], 0)}` });
while (tick < (CFG.MAX || 200) && Object.values(pcb).some(p => p.estado !== 'T')) { tick++; frontera(); }

// ---------- Resultados ----------
const P = Object.values(pcb);
const metricas = P.map(p => ({ pid: p.pid, llegada: p.llegada, primerDespacho: p.primeraCPU, fin: p.fin,
  retorno: p.fin - p.llegada, espera: p.tEst.L, respuesta: p.primeraCPU - p.llegada, bloqueado: p.tEst.B, enCPU: p.tEst.E, instr: p.cpu }));
const prom = k => +(metricas.reduce((a, m) => a + m[k], 0) / metricas.length).toFixed(2);
const resumen = { Q: CFG.Q, ticks: tick, esperaProm: prom('espera'), retornoProm: prom('retorno'), respuestaProm: prom('respuesta'),
  cambiosCtx, expropiaciones, fallos, reemplazos, intTotal: total, sys: sysCnt,
  usoCPU: +(P.reduce((a, p) => a + p.cpu, 0) / tick * 100).toFixed(1), throughput: +(P.length / tick).toFixed(3) };

const modo = process.argv[2] || '--trace';
const ln = s => console.log(s);
if (modo === '--json') {
  console.log(JSON.stringify({ cfg: CFG, steps: log.filter(e => e.kind !== 'SNAP'), snaps: log.filter(e => e.kind === 'SNAP'), metricas, resumen }, null, 1));
} else if (modo === '--trace') {
  const a = process.argv[3] !== undefined ? +process.argv[3] : -1, b = process.argv[4] !== undefined ? +process.argv[4] : 1e9;
  ln('| # | t | Componente | Estado ANTES | Estado DESPUÉS | Causa (el porqué) | ΣINT |');
  ln('|--:|--:|---|---|---|---|--:|');
  for (const e of log.filter(e => e.kind !== 'SNAP' && e.t >= a && e.t <= b)) ln(`| ${e.n} | ${e.t} | ${e.comp} | ${e.antes} | ${e.despues} | ${e.causa} | ${e.total} |`);
} else if (modo === '--ints') {
  for (const t of TIPOS) { const ids = log.filter(e => e.kind === 'INT' && e.intTipo === t).map(e => '#' + e.intId); ln(`| ${t} | ${ids.length} | ${ids.join(', ') || '—'} |`); }
} else if (modo === '--timers') {
  ln('| INT # | t | Atribuida a | Quantum usado | Resultado de la ISR | Paso |');
  ln('|--:|--:|---|---|---|--:|');
  for (const e of log.filter(e => e.timer)) ln(`| #${e.intId} | ${e.t} | ${e.timer.pid === 'SIS' ? 'Sistema' : e.timer.pid} | ${e.timer.res === 'sin proceso' ? '—' : e.timer.usado + '/' + CFG.Q} | ${({ 'continúa': 'continúa (sin cambio de proceso)', expropia: 'quantum agotado → expropia (cambio de contexto)', renueva: 'quantum agotado, cola vacía → renueva, sin cambio', 'sin proceso': 'CPU sin proceso → Sistema' })[e.timer.res]} | ${e.n} |`);
} else if (modo === '--timerstats') {
  const t = log.filter(e => e.timer), c = {}; t.forEach(e => c[e.timer.res] = (c[e.timer.res] || 0) + 1); ln(JSON.stringify({ total: t.length, ...c }));
} else if (modo === '--stats') {
  const k = {}; log.filter(e => e.kind !== 'SNAP').forEach(e => k[e.kind] = (k[e.kind] || 0) + 1);
  ln(JSON.stringify(k));
} else if (modo === '--pm') {
  ln('| Proceso | Llegada | Primer despacho | Fin | Retorno | Espera (LISTO) | En CPU (EJECUTANDO) | Bloqueado | Respuesta |');
  ln('|---|--:|--:|--:|--:|--:|--:|--:|--:|');
  for (const m of metricas) ln(`| ${m.pid} | ${m.llegada} | ${m.primerDespacho} | ${m.fin} | ${m.retorno} | ${m.espera} | ${m.enCPU} | ${m.bloqueado} | ${m.respuesta} |`);
  ln(`| **Promedio** | | | | **${resumen.retornoProm}** | **${resumen.esperaProm}** | | | **${resumen.respuestaProm}** |`);
} else if (modo === '--snap') {
  ln('| t | CPU | Cola de listos | Cola del disco | Marcos de memoria | Estados | Contador del sistema (T E S F X N = Σ) | Por proceso |');
  ln('|--:|---|---|---|---|---|---|---|');
  for (const e of log.filter(e => e.kind === 'SNAP')) ln(`| ${e.t} | ${e.cpu || 'libre'} | ${e.listos} | ${e.disco} | ${e.mem} | ${e.est} | ${e.cnt} | ${e.porProc} |`);
} else if (modo === '--counters') {
  ln('| Proceso | TIMER | E/S-DMA | SYSCALL | FALLO_PAG | EXCEPCIÓN | NMI | Total |');
  ln('|---|--:|--:|--:|--:|--:|--:|--:|');
  const fila = (n, c) => ln(`| ${n} | ${TIPOS.map(t => c[t]).join(' | ')} | ${TIPOS.reduce((a, t) => a + c[t], 0)} |`);
  for (const p of P) fila(p.pid, p.cnt);
  fila('Sistema (CPU sin proceso)', SIS.cnt);
  fila('**Total del sistema**', sysCnt);
  const chk = TIPOS.every(t => P.reduce((a, p) => a + p.cnt[t], 0) + SIS.cnt[t] === sysCnt[t]);
  ln(`\nVerificación Σ(procesos)+Sistema = total por tipo: ${chk ? 'OK' : 'ERROR'}`);
  const nInt = log.filter(e => e.kind === 'INT').length; ln(`Filas INT en la bitácora = ${nInt}; contador = ${total}`);
} else if (modo === '--metrics') {
  ln(JSON.stringify({ resumen, metricas }));
}
