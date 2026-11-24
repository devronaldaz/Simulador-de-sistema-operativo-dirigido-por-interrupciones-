// Visor de la bitácora (requisito R5). Pantalla 1: elegir algoritmos (con el servidor
// local simula vía /api/simular). Pantalla 2: la simulación, separada en pestañas.
// Los estados y las transiciones se leen de la propia traza, así que un estado
// nuevo (como ZOMBIE) aparece sin tocar este archivo si tiene posición abajo.
'use strict';

const POS = {   // posición de cada estado en el mapa (x, y de la esquina)
  NUEVO: [20, 30], TERMINADO: [600, 30], LISTO: [150, 160], EJECUTANDO: [430, 160],
  BLOQUEADO: [290, 290], ZOMBIE: [620, 290],
};
const W = 160, H = 70;
const RUTAS = {  // trazados a mano para las transiciones conocidas; las demás van en línea recta
  T1: { d: 'M100,100 L200,158', lx: 112, ly: 140, a: 'end' },
  T2: { d: 'M310,205 L428,205', lx: 369, ly: 248, a: 'middle' },
  T3: { d: 'M500,158 Q370,105 240,158', lx: 370, ly: 118, a: 'middle' },
  T4: { d: 'M520,232 Q520,325 452,325', lx: 508, ly: 280, a: 'end' },
  T5: { d: 'M288,325 Q225,325 225,232', lx: 216, ly: 296, a: 'end' },
  T6: { d: 'M560,158 L640,102', lx: 556, ly: 130, a: 'end' },
  T7: { d: 'M570,232 L650,288', lx: 625, ly: 252, a: 'start' },
  T8: { d: 'M700,288 L690,102', lx: 702, ly: 200, a: 'start' },
  T9: { d: 'M180,55 L598,55', lx: 390, ly: 47, a: 'middle' },
};
const TIPOS_INT = { TIMER: 'T', ES_DMA: 'E', SYSCALL: 'S', FALLO_PAG: 'F', EXCEPCION: 'X', NMI: 'N',
                    WORST_TIME: 'W', SENAL: 'K', PROTECCION: 'P' };

let traza = null, i = 0, temporizador = null, procTabla = null;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const color = est => `var(--${est})`;

// ---------------------------------------------------------------- mapa de estados
function dibujarMapa() {
  const svg = $('svg-estados');
  const estados = traza ? traza.estados : Object.keys(POS);
  const trans = traza ? traza.transiciones : [];
  let html = '<defs><marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" ' +
    'markerWidth="12" markerHeight="12" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>';
  for (const t of trans) {
    let r = RUTAS[t.id];
    if (!r) {   // transición nueva sin trazado: línea recta entre centros
      const [x1, y1] = POS[t.de] || [0, 0], [x2, y2] = POS[t.a] || [0, 0];
      r = { d: `M${x1 + W / 2},${y1 + H / 2} L${x2 + W / 2},${y2 + H / 2}`, lx: (x1 + x2) / 2 + W / 2, ly: (y1 + y2) / 2 + H / 2, a: 'middle' };
    }
    html += `<path id="ar-${t.id}" class="arista" d="${r.d}" marker-end="url(#flecha)" style="color:var(--suave)"/>` +
      `<text id="et-${t.id}" class="etiqueta" x="${r.lx}" y="${r.ly}" text-anchor="${r.a}">${t.id} ${esc(t.rotulo)}</text>`;
  }
  for (const nombre of estados) {
    const [x, y] = POS[nombre] || [20, 300];
    html += `<g class="estado" id="es-${nombre}"><rect x="${x}" y="${y}" width="${W}" height="${H}" rx="10" style="stroke:${color(nombre)}"/>` +
      `<text class="nombre" x="${x + W / 2}" y="${y + 22}">${nombre}</text><g class="fichas-svg"></g></g>`;
  }
  svg.innerHTML = html;
}

function ultimaTransicion(hasta) {
  for (let k = hasta; k >= 0; k--) if (traza.pasos[k].transicion) return k;
  return -1;
}

function pintarMapa(paso) {
  const v = paso.vista, porEstado = {};
  for (const [pid, est] of Object.entries(v.estados)) (porEstado[est] = porEstado[est] || []).push(pid);
  const kTrans = ultimaTransicion(i), tr = kTrans >= 0 ? traza.pasos[kTrans].transicion : null;
  for (const nombre of traza.estados) {
    const g = document.querySelector(`#es-${nombre} .fichas-svg`);
    if (!g) continue;
    const [x, y] = POS[nombre] || [20, 300];
    const pids = porEstado[nombre] || [];
    const ancho = pids.length > 4 ? 26 : 36;
    g.innerHTML = pids.map((pid, n) => {
      const fx = x + 8 + (n % 5) * (ancho + 3), fy = y + 32 + Math.floor(n / 5) * 18;
      const movida = tr && kTrans === i && tr.pid === pid ? ' movida' : '';
      return `<g class="ficha${movida}"><rect x="${fx}" y="${fy}" width="${ancho}" height="17"/>` +
             `<text x="${fx + ancho / 2}" y="${fy + 12.5}">${pid}</text></g>`;
    }).join('');
    document.getElementById(`es-${nombre}`).classList.toggle('activo', pids.length > 0);
  }
  for (const t of traza.transiciones) {
    $(`ar-${t.id}`).setAttribute('class', 'arista');
    $(`ar-${t.id}`).style.color = 'var(--suave)';
    $(`et-${t.id}`).setAttribute('class', 'etiqueta');
  }
  if (tr && $(`ar-${tr.id}`)) {
    const clase = kTrans === i ? 'reciente' : 'previa';
    $(`ar-${tr.id}`).setAttribute('class', `arista ${clase}`);
    $(`ar-${tr.id}`).style.color = 'var(--resalte)';
    if (clase === 'reciente') $(`et-${tr.id}`).setAttribute('class', 'etiqueta reciente');
  }
}

// ---------------------------------------------------------------- flujo, colas, contadores
function pintarFlujo(paso) {
  const v = paso.vista, tipo = paso.tipo_paso;
  const activa = { cola: tipo === 'TRANS' && paso.transicion && paso.transicion.a === 'LISTO',
    plan: tipo === 'PLAN' || tipo === 'SCHED', desp: tipo === 'TRANS' && paso.transicion && paso.transicion.id === 'T2',
    cpu: tipo === 'EXEC', ctrl: tipo === 'INT' };
  const fichas = l => l.length ? l.map(p => `<span class="chip">${p}</span>`).join(' ') : '<span class="vacio">vacía</span>';
  const etapa = (clave, titulo, cuerpo) => `<div class="etapa${activa[clave] ? ' activa' : ''}"><b>${titulo}</b>${cuerpo}</div>`;
  const pcb = v.cpu ? v.pcb[v.cpu] : null;
  $('flujo').innerHTML =
    (v.nuevos.length ? etapa('x', 'Cola de nuevos (largo plazo)', fichas(v.nuevos)) + '<div class="flecha">↓</div>' : '') +
    etapa('cola', 'Cola de listos', fichas(v.listos)) + '<div class="flecha">↓</div>' +
    etapa('plan', `Planificador · ${esc(traza.planificador)}`, tipo === 'PLAN' ? esc(paso.despues) : '<span class="vacio">elige quién va</span>') +
    '<div class="flecha">↓</div>' +
    etapa('desp', 'Despachador', '<span class="vacio">cambia el contexto</span>') + '<div class="flecha">↓</div>' +
    etapa('cpu', `CPU · modo ${v.modo}`, v.cpu ? `<span class="chip">${v.cpu}</span> PC=${pcb.pc}` +
      (v.quantum ? ` · quantum ${v.quantum}` : '') : '<span class="vacio">libre / ociosa</span>') +
    etapa('ctrl', 'Controlador de interrupciones', paso.tipo_paso === 'INT' ? `INT #${paso.int_id} · ${paso.int_tipo}` : '<span class="vacio">—</span>');
  $('disco').innerHTML = v.disco.length
    ? v.disco.map(d => `<div><span class="chip">${d.pid}</span> ${d.tipo === 'read' ? 'lectura' : 'carga de página (DMA)'} hasta t=${d.fin}</div>`).join('')
    : '<span class="vacio">vacía</span>';
  const c = v.contadores;
  $('interrupciones').innerHTML = '<table><tbody>' +
    Object.keys(TIPOS_INT).filter(t => c[t] || ['TIMER', 'ES_DMA', 'SYSCALL'].includes(t))
      .map(t => `<tr><td>${t}</td><td>${c[t]}</td></tr>`).join('') +
    `<tr><th>Total</th><th>${c.total}</th></tr></tbody></table>` +
    '<div style="margin-top:4px">' + Object.entries(v.por_proceso).map(([p, n]) => `${p}=${n}`).join(' · ') + '</div>';
  const pcbs = Object.values(v.pcb), tick = Math.max(v.tick, 1);
  const term = pcbs.filter(p => p.estado === 'TERMINADO').length;
  const usado = pcbs.reduce((a, p) => a + p.cpu_usado, 0);
  const vivos = pcbs.filter(p => p.estado !== 'NUEVO');
  const espera = vivos.length ? (vivos.reduce((a, p) => a + p.espera, 0) / vivos.length).toFixed(2) : '—';
  $('metricas').innerHTML = `<table><tbody>
    <tr><td>Utilización de CPU</td><td>${(100 * usado / tick).toFixed(1)} %</td></tr>
    <tr><td>Rendimiento (throughput)</td><td>${(term / tick).toFixed(3)} proc/tick</td></tr>
    <tr><td>Espera promedio hasta ahora</td><td>${espera}</td></tr>
    <tr><td>Cambios de contexto</td><td>${v.cambios_contexto}</td></tr>
    <tr><td>Terminados</td><td>${term} de ${pcbs.length}</td></tr></tbody></table>`;
}

// ---------------------------------------------------------------- línea de tiempo
let lineaConstruida = false;
function construirLinea() {
  const inst = traza.instantaneas, pids = traza.procesos;
  const ints = inst.map(() => []);
  for (const p of traza.pasos) if (p.tipo_paso === 'INT') ints[p.tick].push(TIPOS_INT[p.int_tipo] || '?');
  let html = '<table><thead><tr><th class="pid">t</th>' + inst.map(s => `<th>${s.tick}</th>`).join('') + '</tr></thead><tbody>';
  for (const pid of pids) {
    html += `<tr><th class="pid">${pid}</th>` + inst.map((s, k) => {
      const est = s.estados[pid];
      const fondo = est === 'TERMINADO' && (k === 0 || inst[k - 1].estados[pid] === 'TERMINADO') ? 'transparent' : color(est);
      return `<td class="c" data-t="${s.tick}" title="${pid} en t=${s.tick}: ${est}" style="background:${fondo}">${est === 'EJECUTANDO' ? '▮' : ''}</td>`;
    }).join('') + '</tr>';
  }
  html += '<tr><th class="pid">INT</th>' + ints.map((l, k) =>
    `<td class="int" data-t="${k}" title="${l.length} interrupciones: ${l.join(' ')}">${[...new Set(l)].join('')}</td>`).join('') + '</tr>';
  $('linea').innerHTML = html + '</tbody></table>';
  $('leyenda').innerHTML = traza.estados.map(e => `<span style="background:${color(e)}"></span>${e}`).join('') +
    ' · Interrupciones: ' + Object.entries(TIPOS_INT).map(([t, l]) => `${l}=${t}`).join(', ');
  lineaConstruida = true;
}

function pintarLinea(paso) {
  document.querySelectorAll('.linea td.ahora').forEach(c => c.classList.remove('ahora'));
  document.querySelectorAll(`.linea td[data-t="${paso.tick}"]`).forEach(c => c.classList.add('ahora'));
}

// ---------------------------------------------------------------- PCB y memoria
function pintarPCB(paso) {
  const filas = Object.values(paso.vista.pcb);
  const contigua = traza.memoria === 'contigua';
  $('pcb').innerHTML = '<thead><tr><th>PID</th><th>Estado</th><th>PC</th><th>Prioridad</th><th>Ráfaga</th><th>Restante</th>' +
    '<th>CPU usado</th><th>Quantum</th><th>Espera</th><th>Interrup.</th><th>Cambios ctx</th><th>E/S</th><th>Clase</th>' +
    '<th>Padre</th>' + (contigua ? '<th>Base</th><th>Límite</th>' : '') + '<th>Último motivo</th></tr></thead><tbody>' +
    filas.map(p => `<tr data-pid="${p.pid}"${p.pid === procTabla ? ' class="actual"' : ''}><td><b>${p.pid}</b></td>` +
      `<td class="estado-celda" style="color:${color(p.estado)}">${p.estado}${p.senal_pendiente ? ' ⚑' : ''}</td><td>${p.pc}</td>` +
      `<td>${p.prioridad}</td><td>${p.burst}</td><td>${p.rafaga_restante}</td><td>${p.cpu_usado}</td>` +
      `<td>${p.quantum_restante ?? '—'}</td><td>${p.espera}</td><td>${p.interrupciones}</td><td>${p.cambios_contexto}</td>` +
      `<td>${p.operaciones_es}</td><td>${p.clase}</td><td>${p.padre}</td>` +
      (contigua ? `<td>${p.base ?? '—'}</td><td>${p.limite ?? '—'}</td>` : '') +
      `<td style="white-space:normal;max-width:380px">${esc(p.motivo)}</td></tr>`).join('') + '</tbody>';
}

function pintarMemoria(paso) {
  const v = paso.vista;
  $('modo-memoria').textContent = traza.memoria === 'contigua'
    ? `(contigua · ${traza.config.ajuste} ajuste · base y límite)`
    : `(paginada · marcos de ${traza.config.tamano_marco} B · ${traza.config.reemplazo} ${traza.config.alcance})`;
  $('mapa').innerHTML = `<thead><tr><th>N° ${traza.memoria === 'contigua' ? 'región' : 'frame'}</th><th>Registro inicial</th>` +
    '<th>Registro final</th><th>Proceso</th><th>Página</th><th>Estado</th><th>Estado del proceso</th></tr></thead><tbody>' +
    v.mapa.map(f => `<tr><td>${f.n}</td><td>${f.inicio}</td><td>${f.fin}</td><td><b>${f.proceso || '—'}</b></td>` +
      `<td>${f.pagina ?? '—'}</td><td>${f.estado}</td>` +
      `<td style="color:${color(f.estado_proceso)}">${f.estado_proceso}</td></tr>`).join('') + '</tbody>';
  $('mmu').textContent = v.mmu || 'Sin accesos todavía.';
  const tabla = v.tablas[procTabla] || [];
  $('tabla-paginas').innerHTML = traza.memoria === 'contigua'
    ? '<tbody><tr><td class="vacio">En memoria contigua no hay tabla de páginas: la MMU usa base y límite (ver PCB).</td></tr></tbody>'
    : '<thead><tr><th>Página</th><th>Presente</th><th>Marco</th><th>R</th><th>M</th></tr></thead><tbody>' +
      (tabla.length ? tabla.map(e => `<tr><td>${e.pagina}</td><td>1</td><td>${e.marco}</td><td>${e.r}</td><td>${e.m}</td></tr>`).join('')
                    : '<tr><td colspan="5" class="vacio">sin páginas presentes</td></tr>') + '</tbody>';
  $('tlb').innerHTML = traza.config.tlb ? (v.tlb.length ? v.tlb.map(e => `<span class="chip">${e}</span>`).join(' ') : '<span class="vacio">vacía</span>')
    : '<span class="vacio">sin TLB (parámetro tlb = 0)</span>';
}


// ---------------------------------------------------------------- paso actual
function centrar(caja, elemento, horizontal) {
  const rc = caja.getBoundingClientRect(), re = elemento.getBoundingClientRect();
  if (horizontal) caja.scrollLeft += re.left - rc.left - caja.clientWidth / 2;
  else caja.scrollTop += re.top - rc.top - caja.clientHeight / 2 + re.height / 2;
}

function pintar() {
  if (!traza) return;
  const paso = traza.pasos[i], total = traza.pasos.length;
  $('posicion').textContent = `paso ${paso.paso}/${total} · t=${paso.tick}`;
  $('barra').value = i + 1;
  const titulo = paso.transicion
    ? `${paso.transicion.pid}: ${paso.transicion.de} → ${paso.transicion.a} (${paso.transicion.id})`
    : `${paso.tipo_paso} · ${paso.componente}`;
  const intTxt = paso.int_id ? ` · INT #${paso.int_id}` : '';
  $('paso-actual').innerHTML = `<b>${esc(titulo)}${intTxt}</b> — ${esc(paso.causa)}`;
  $('paso-actual').title = paso.causa;
  pintarMapa(paso);
  $('porque').innerHTML = `<div class="titulo">${esc(titulo)}${intTxt}</div>` +
    `<div>Causa: ${esc(paso.causa)}</div><div class="cambio">Antes: ${esc(paso.antes)}<br>Después: ${esc(paso.despues)}</div>`;
  pintarFlujo(paso);
  pintarLinea(paso);
  pintarPCB(paso);
  pintarMemoria(paso);
  document.querySelectorAll('#filas tr.actual').forEach(f => f.classList.remove('actual'));
  const fila = $('filas').children[i];
  if (fila) fila.classList.add('actual');
  // Solo se desplaza la caja interna de la pestaña visible: la página no se mueve.
  if (fila && !$('p-bitacora').hidden) centrar($('caja-filas'), fila);
  const celda = document.querySelector('.linea td.ahora');
  if (celda && !$('p-linea').hidden) centrar($('linea'), celda, true);
}

// ---------------------------------------------------------------- algoritmos en uso
const NOMBRES_PLAN = { FCFS: 'FCFS', SJF: 'SJF', RR: 'Round Robin', PRIORIDAD: 'Prioridades' };
const TITULOS_PLAN = { FCFS: 'First Come, First Served', SJF: 'Shortest Job First', RR: 'Round Robin', PRIORIDAD: 'Por prioridades' };
const NOMBRES_REEMPLAZO = { FIFO: 'FIFO', LRU: 'LRU', OPTIMO: 'Óptimo', CLOCK: 'Reloj (segunda oportunidad)' };

function textoProcesos(c, nombre) {
  let t = `<b>${esc(nombre)}</b>`;
  if (c.planificador === 'RR') t += ` · quantum ${c.quantum}`;
  if (c.aging) t += ` · aging ${c.aging}`;
  return t + ` · timer cada ${c.periodo_timer} tick${c.periodo_timer > 1 ? 's' : ''}`;
}
function textoMemoria(c) {
  if (c.mmu === 'contigua') return `<b>Contigua · ${esc(c.ajuste)} ajuste</b> · ${c.memoria_total} B (SO ${c.memoria_so} B)`;
  return `<b>Paginación · reemplazo ${esc(NOMBRES_REEMPLAZO[c.reemplazo] || c.reemplazo)}</b> (${esc(c.alcance)})` +
    ` · ${c.marcos} marcos de ${c.tamano_marco} B` + (c.tlb ? ` · TLB ${c.tlb}` : ' · sin TLB');
}

function cargar(datos) {
  if (!datos || !datos.estados) { alert('Traza de una versión anterior: vuelva a generarla con --visor.'); return false; }
  if (temporizador) alternar();
  traza = datos; i = 0;
  procTabla = traza.procesos[0];
  const r = traza.resumen, c = traza.config;
  $('algoritmos').innerHTML =
    `<span class="insignia">Gestión de procesos: ${textoProcesos(c, traza.planificador)}</span>` +
    `<span class="insignia">Gestión de memoria: ${textoMemoria(c)}</span>`;
  $('escenario').textContent = `${traza.escenario} · ${traza.procesos.length} procesos · ${r.ticks} ticks · ` +
    `${r.interrupciones} interrupciones · ${r.cambios_contexto} cambios de contexto`;
  $('barra').max = traza.pasos.length;
  $('proc-tabla').innerHTML = traza.procesos.map(p => `<option>${p}</option>`).join('');
  $('filas').innerHTML = traza.pasos.map((p, k) =>
    `<tr data-k="${k}" class="${p.transicion ? 'trans' : p.tipo_paso === 'PLAN' ? 'plan' : ''}"><td>${p.paso}</td><td>${p.tick}</td><td>${p.tipo_paso}</td>` +
    `<td>${esc(p.componente)}</td><td>${esc(p.antes)} → ${esc(p.despues)}</td><td>${esc(p.causa)}</td></tr>`).join('');
  dibujarMapa();
  construirLinea();
  return true;
}

function ir(k) { if (traza) { i = Math.max(0, Math.min(traza.pasos.length - 1, k)); pintar(); } }
const ICONO_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>';
const ICONO_PAUSA = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14M16 5v14"/></svg>';
function botonReproducir(reproduciendo) {
  $('reproducir').innerHTML = reproduciendo ? `${ICONO_PAUSA}<span>Pausa</span>` : `${ICONO_PLAY}<span>Reproducir</span>`;
  $('reproducir').setAttribute('aria-pressed', String(reproduciendo));
}
function alternar() {
  if (temporizador) { clearInterval(temporizador); temporizador = null; botonReproducir(false); return; }
  if (!traza) return;
  if (i >= traza.pasos.length - 1) ir(0);
  temporizador = setInterval(() => { if (!traza || i >= traza.pasos.length - 1) return alternar(); ir(i + 1); }, +$('velocidad').value);
  botonReproducir(true);
}
botonReproducir(false);

// ---------------------------------------------------------------- pantallas y pestañas
function mostrar(pantalla) {
  const sim = pantalla === 'sim' && !!traza;
  if (!sim && temporizador) alternar();
  $('pantalla-inicio').hidden = sim;
  $('pantalla-sim').hidden = !sim;
  if (sim) pintar();
  window.scrollTo(0, 0);
  const hash = sim ? '#simulacion' : '#inicio';
  if (location.hash !== hash) history.pushState(null, '', hash);
}
window.addEventListener('popstate', () => mostrar(location.hash === '#simulacion' ? 'sim' : 'inicio'));

const PESTANAS = [...document.querySelectorAll('.pestanas [role=tab]')];
function marcarPestana(nombre) {   // solo el estado visual y ARIA (patrón de pestañas WAI-ARIA)
  PESTANAS.forEach(b => {
    const activa = b.dataset.pestana === nombre;
    b.classList.toggle('activa', activa);
    b.setAttribute('aria-selected', String(activa));
    b.tabIndex = activa ? 0 : -1;
  });
  document.querySelectorAll('#pantalla-sim .panel').forEach(p => { p.hidden = p.id !== `p-${nombre}`; });
}
function activarPestana(nombre) {
  marcarPestana(nombre);
  try { localStorage.setItem('so-visor-pestana', nombre); } catch (e) { /* sin almacenamiento */ }
  pintar();
}
PESTANAS.forEach((b, k) => {
  b.onclick = () => activarPestana(b.dataset.pestana);
  b.onkeydown = e => {   // flechas, Inicio y Fin recorren las pestañas
    const destino = { ArrowRight: k + 1, ArrowLeft: k - 1, Home: 0, End: PESTANAS.length - 1 }[e.key];
    if (destino === undefined) return;
    e.preventDefault(); e.stopPropagation();
    const b2 = PESTANAS[(destino + PESTANAS.length) % PESTANAS.length];
    b2.focus(); activarPestana(b2.dataset.pestana);
  };
});

// ---------------------------------------------------------------- pantalla de inicio
const OPC_ESTATICAS = {
  planificadores: {
    FCFS: 'Primero en llegar, primero en ser atendido (no expropiativo)',
    SJF: 'Menor próxima ráfaga de CPU; con expropiativo=true es SRTF',
    RR: 'Turno fijo (quantum); al agotarse vuelve al final de la cola',
    PRIORIDAD: 'Mayor prioridad (menor número); expropiativo por defecto',
  },
  reemplazo: { LRU: 'la menos recientemente usada', FIFO: 'la que lleva más tiempo en memoria',
    OPTIMO: 'la que tardará más en volver a usarse', CLOCK: 'la primera con bit R=0 que encuentra la manecilla' },
  ajuste: { primer: 'el primer hueco donde cabe', mejor: 'el hueco más pequeño donde cabe', peor: 'el hueco más grande',
    siguiente: 'como primer ajuste, pero sigue desde el último hueco usado' },
  por_defecto: {},
};
const MMU = {
  paginada: ['Paginación (MMU con tabla de páginas)', 'Dirección virtual → (página, desplazamiento) → marco; fallos de página y reemplazo'],
  contigua: ['Asignación contigua (base y límite)', 'Cada proceso ocupa un bloque continuo; huecos y fragmentación externa'],
};
const CAMPOS_NUM = ['quantum', 'aging', 'periodo_timer', 'grado_multiprogramacion', 'worst_time', 'recolector_ticks',
  'marcos', 'marcos_so', 'tamano_marco', 'tlb', 'memoria_total', 'memoria_so'];
const CAMPOS_TXT = ['prioridad', 'worst_time_modo', 'politica_zombie', 'alcance'];

let API = false, OPC = OPC_ESTATICAS, ESCENARIOS = [], base = null;
const eleccion = { planificador: 'RR', mmu: 'paginada', reemplazo: 'LRU', ajuste: 'primer' };

function tarjetas(id, clave, opciones, titulo) {
  $(id).innerHTML = Object.entries(opciones).map(([valor, desc]) =>
    `<button type="button" class="tarjeta" data-clave="${clave}" data-valor="${valor}">` +
    `<span class="t">${esc(titulo(valor))}</span><span class="d">${esc(desc)}</span></button>`).join('');
}

function construirTarjetas() {
  tarjetas('tarjetas-planificador', 'planificador', OPC.planificadores, v => `${TITULOS_PLAN[v] || v} (${v})`);
  tarjetas('tarjetas-mmu', 'mmu', Object.fromEntries(Object.entries(MMU).map(([k, v]) => [k, v[1]])), v => MMU[v][0]);
  tarjetas('tarjetas-reemplazo', 'reemplazo', Object.fromEntries(Object.entries(OPC.reemplazo).map(([k, v]) => [k, `Víctima: ${v}`])),
    v => NOMBRES_REEMPLAZO[v] || v);
  tarjetas('tarjetas-ajuste', 'ajuste', OPC.ajuste, v => `${v[0].toUpperCase()}${v.slice(1)} ajuste`);
  document.querySelectorAll('.tarjeta').forEach(b => {
    b.onclick = () => { eleccion[b.dataset.clave] = b.dataset.valor; refrescarEleccion(); };
  });
}

function refrescarEleccion() {
  document.querySelectorAll('.tarjeta').forEach(b => {
    const elegida = eleccion[b.dataset.clave] === b.dataset.valor;
    b.classList.toggle('elegida', elegida);
    b.setAttribute('aria-pressed', String(elegida));
  });
  document.querySelectorAll('[data-solo]').forEach(el => { el.hidden = el.dataset.solo !== eleccion.planificador; });
  document.querySelectorAll('[data-mmu]').forEach(el => { el.hidden = el.dataset.mmu !== eleccion.mmu; });
  const memoria = eleccion.mmu === 'contigua'
    ? `asignación <b>contigua</b> con <b>${eleccion.ajuste} ajuste</b>`
    : `<b>paginación</b> con reemplazo <b>${NOMBRES_REEMPLAZO[eleccion.reemplazo] || eleccion.reemplazo}</b>`;
  const q = eleccion.planificador === 'RR' && $('quantum').value ? ` (quantum ${$('quantum').value})` : '';
  $('resumen-eleccion').innerHTML = `Procesos: <b>${NOMBRES_PLAN[eleccion.planificador] || eleccion.planificador}</b>${q} · Memoria: ${memoria}`;
}

function llenarConfig(cfg) {
  const c = { ...OPC.por_defecto, ...cfg };
  for (const k of ['planificador', 'mmu', 'reemplazo', 'ajuste']) if (c[k]) eleccion[k] = c[k];
  for (const k of [...CAMPOS_NUM, ...CAMPOS_TXT]) $(k).value = c[k] ?? '';
  $('expropiativo').value = c.expropiativo === true ? 'si' : c.expropiativo === false ? 'no' : '';
  refrescarEleccion();
}

function filaProceso(p = {}) {
  const tr = document.createElement('tr');
  const celda = (campo, valor, tipo = 'text', extra = '') =>
    `<td><input data-campo="${campo}" type="${tipo}" value="${esc(valor ?? '')}" ${extra}></td>`;
  tr.innerHTML = celda('pid', p.pid) + celda('llegada', p.llegada ?? 0, 'number', 'min="0"') +
    celda('prioridad', p.prioridad ?? '', 'number', 'min="0"') + celda('burst', p.burst, 'number', 'min="1"') +
    celda('tamano', p.tamano, 'number', 'min="1"') + celda('es', (p.es || []).join(', '), 'text', 'placeholder="ej. 2, 5"') +
    celda('guion', (p.guion || []).join(', '), 'text', 'placeholder="se genera con el burst-time"') +
    `<td><button type="button" class="quitar" aria-label="Quitar proceso ${esc(p.pid || '')}" title="Quitar proceso">` +
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button></td>';
  tr.querySelector('.quitar').onclick = () => tr.remove();
  return tr;
}

function elegirEscenario(k) {
  base = ESCENARIOS[k];
  if (!base) return;
  const d = base.datos;
  $('procesos').replaceChildren(...(d.procesos || []).map(filaProceso));
  const ev = d.eventos_externos || [];
  $('eventos-externos').textContent = ev.length
    ? `Eventos externos del escenario: ${ev.map(e => `${e.tipo}${e.pid ? ' ' + e.pid : ''} en t=${e.tick}`).join(', ')}` : '';
  llenarConfig(d.config || {});
}

function leerProcesos() {
  return [...$('procesos').children].map(tr => {
    const v = c => tr.querySelector(`[data-campo="${c}"]`).value.trim();
    const p = { pid: v('pid'), llegada: +v('llegada') || 0 };
    if (v('prioridad') !== '') p.prioridad = +v('prioridad');
    if (v('tamano') !== '') p.tamano = +v('tamano');
    const guion = v('guion').split(',').map(s => s.trim()).filter(Boolean);
    if (guion.length) p.guion = guion;
    else {
      if (v('burst') !== '') p.burst = +v('burst');
      const es = v('es').split(',').map(s => s.trim()).filter(Boolean).map(Number);
      if (es.length) p.es = es;
    }
    return p;
  });
}

function leerConfig() {
  const cfg = { ...(base ? base.datos.config : {}), ...eleccion };
  for (const k of CAMPOS_NUM) { const v = $(k).value.trim(); if (v !== '') cfg[k] = +v; else delete cfg[k]; }
  for (const k of CAMPOS_TXT) cfg[k] = $(k).value;
  const ex = $('expropiativo').value;
  if (ex) cfg.expropiativo = ex === 'si'; else delete cfg.expropiativo;
  return cfg;
}

async function simular() {
  const procesos = leerProcesos();
  const pids = new Set(procesos.map(p => p.pid));
  const eventos = (base ? base.datos.eventos_externos || [] : []).filter(e => e.tipo !== 'KILL' || pids.has(e.pid));
  // El nombre del escenario de ejemplo menciona su algoritmo original; aquí solo se toman sus procesos.
  const datos = { nombre: base ? `Procesos tomados del ejemplo: ${base.nombre.replace(/\s*\(.*\)\s*$/, '')}` : 'Procesos propios',
    config: leerConfig(), procesos, eventos_externos: eventos };
  $('error').hidden = true;
  $('iniciar').disabled = true; $('iniciar').querySelector('span').textContent = 'Simulando…';
  try {
    const r = await fetch('api/simular', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos) });
    const cuerpo = await r.json();
    if (!r.ok) throw new Error(cuerpo.error || `error ${r.status}`);
    if (cargar(cuerpo)) mostrar('sim');
  } catch (err) {
    $('error').textContent = `No se pudo simular: ${err.message}`;
    $('error').hidden = false;
  } finally {
    $('iniciar').disabled = false; $('iniciar').querySelector('span').textContent = 'Iniciar simulación';
  }
}

async function preparar() {
  try {
    const r = await fetch('api/opciones', { cache: 'no-store' });
    if (!r.ok) throw new Error('sin API');
    OPC = await r.json();
    ESCENARIOS = await (await fetch('api/escenarios', { cache: 'no-store' })).json();
    API = true;
  } catch (e) { API = false; }
  construirTarjetas();
  if (API) {
    $('escenario-base').innerHTML = ESCENARIOS.map((e, k) => `<option value="${k}">${esc(e.nombre)}</option>`).join('');
    elegirEscenario(0);
  } else {
    $('aviso-estatico').hidden = false;
    document.querySelector('#pantalla-inicio .bloque').hidden = true;   // sin servidor no se editan procesos
    document.querySelectorAll('#pantalla-inicio input, #pantalla-inicio select, #pantalla-inicio .tarjeta')
      .forEach(el => { el.disabled = true; });
    $('iniciar').hidden = true;
    if (window.TRAZA && cargar(window.TRAZA)) {
      llenarConfig(window.TRAZA.config);
      $('ver-traza').hidden = false;
    } else {
      $('resumen-eleccion').innerHTML = 'No hay traza cargada: genere una con <code>py -m simulador ESCENARIO --visor</code> o use <b>Cargar traza JSON</b>.';
    }
  }
  let pestana = 'procesos';
  try { pestana = localStorage.getItem('so-visor-pestana') || pestana; } catch (e) { /* sin almacenamiento */ }
  if (!$(`p-${pestana}`)) pestana = 'procesos';
  marcarPestana(pestana);
  mostrar(location.hash === '#simulacion' ? 'sim' : 'inicio');
}

// ---------------------------------------------------------------- tema (oscuro por defecto; claro para el proyector)
function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  $('tema').setAttribute('aria-label', tema === 'light' ? 'Cambiar a tema oscuro' : 'Cambiar a tema claro');
  try { localStorage.setItem('so-visor-tema', tema); } catch (e) { /* sin almacenamiento */ }
}
$('tema').onclick = () => aplicarTema(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
if (document.documentElement.dataset.theme === 'light') $('tema').setAttribute('aria-label', 'Cambiar a tema oscuro');

// ---------------------------------------------------------------- eventos
dibujarMapa();
$('iniciar').onclick = simular;
$('anadir-proceso').onclick = () => {
  const n = $('procesos').children.length + 1;
  $('procesos').append(filaProceso({ pid: `P${n}`, llegada: 0, burst: 4, tamano: 4096 }));
};
$('escenario-base').onchange = e => elegirEscenario(+e.target.value);
$('quantum').oninput = refrescarEleccion;
$('ver-traza').onclick = () => mostrar('sim');
$('volver').onclick = () => mostrar('inicio');
$('inicio').onclick = () => ir(0);
$('anterior').onclick = () => ir(i - 1);
$('siguiente').onclick = () => ir(i + 1);
$('fin').onclick = () => ir(Infinity);
$('reproducir').onclick = alternar;
$('velocidad').onchange = () => { if (temporizador) { alternar(); alternar(); } };
$('barra').oninput = e => ir(+e.target.value - 1);
$('filas').onclick = e => { const tr = e.target.closest('tr'); if (tr) ir(+tr.dataset.k); };
$('pcb').onclick = e => { const tr = e.target.closest('tr[data-pid]'); if (tr) { procTabla = tr.dataset.pid; $('proc-tabla').value = procTabla; pintar(); } };
$('proc-tabla').onchange = e => { procTabla = e.target.value; pintar(); };
$('linea').onclick = e => {
  const td = e.target.closest('td[data-t]'); if (!td || !traza) return;
  const k = traza.pasos.findIndex(p => p.tick === +td.dataset.t); if (k >= 0) ir(k);
};
$('archivo').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  f.text().then(t => {
    const datos = JSON.parse(t);
    if (cargar(datos)) { if (!API) { llenarConfig(datos.config); $('ver-traza').hidden = false; } mostrar('sim'); }
  }).catch(err => alert('Traza inválida: ' + err.message));
  e.target.value = '';
};
document.addEventListener('keydown', e => {
  if ($('pantalla-sim').hidden || ['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowRight') ir(i + 1);
  else if (e.key === 'ArrowLeft') ir(i - 1);
  else if (e.key === 'Home') ir(0);
  else if (e.key === 'End') ir(Infinity);
  else if (e.key === ' ') { e.preventDefault(); alternar(); }
});
preparar();
