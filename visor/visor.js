// Visor de la bitácora (requisito R5). Solo LEE la traza: no simula nada.
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

// ---------------------------------------------------------------- general
function pintar() {
  if (!traza) return;
  const paso = traza.pasos[i], total = traza.pasos.length;
  $('posicion').textContent = `paso ${paso.paso}/${total} · t=${paso.tick}`;
  $('barra').value = i + 1;
  pintarMapa(paso);
  const titulo = paso.transicion
    ? `${paso.transicion.pid}: ${paso.transicion.de} → ${paso.transicion.a} (${paso.transicion.id})`
    : `${paso.tipo_paso} · ${paso.componente}`;
  $('porque').innerHTML = `<div class="titulo">${esc(titulo)}${paso.int_id ? ` · INT #${paso.int_id}` : ''}</div>` +
    `<div>Causa: ${esc(paso.causa)}</div><div class="cambio">Antes: ${esc(paso.antes)}<br>Después: ${esc(paso.despues)}</div>`;
  pintarFlujo(paso);
  pintarLinea(paso);
  pintarPCB(paso);
  pintarMemoria(paso);
  document.querySelectorAll('#filas tr.actual').forEach(f => f.classList.remove('actual'));
  const fila = $('filas').children[i];
  if (fila) { fila.classList.add('actual'); fila.scrollIntoView({ block: 'nearest' }); }
}

function cargar(datos) {
  traza = datos; i = 0;
  if (!traza.estados) { alert('Traza de una versión anterior: vuelva a generarla con --visor.'); return; }
  procTabla = traza.procesos[0];
  const r = traza.resumen, c = traza.config;
  $('escenario').textContent = `${traza.escenario} · ${traza.planificador}${c.quantum && traza.planificador.startsWith('RR') ? ` q=${c.quantum}` : ''} · ` +
    `memoria ${traza.memoria} · ${r.ticks} ticks · ${r.interrupciones} interrupciones · ${r.cambios_contexto} cambios de contexto`;
  $('barra').max = traza.pasos.length;
  $('proc-tabla').innerHTML = traza.procesos.map(p => `<option>${p}</option>`).join('');
  $('filas').innerHTML = traza.pasos.map((p, k) =>
    `<tr data-k="${k}" class="${p.transicion ? 'trans' : p.tipo_paso === 'PLAN' ? 'plan' : ''}"><td>${p.paso}</td><td>${p.tick}</td><td>${p.tipo_paso}</td>` +
    `<td>${esc(p.componente)}</td><td>${esc(p.antes)} → ${esc(p.despues)}</td><td>${esc(p.causa)}</td></tr>`).join('');
  dibujarMapa();
  construirLinea();
  pintar();
}

function ir(k) { if (traza) { i = Math.max(0, Math.min(traza.pasos.length - 1, k)); pintar(); } }
function alternar() {
  if (temporizador) { clearInterval(temporizador); temporizador = null; $('reproducir').textContent = 'Reproducir'; return; }
  temporizador = setInterval(() => { if (!traza || i >= traza.pasos.length - 1) return alternar(); ir(i + 1); }, +$('velocidad').value);
  $('reproducir').textContent = 'Pausa';
}

dibujarMapa();
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
  f.text().then(t => cargar(JSON.parse(t))).catch(err => alert('Traza inválida: ' + err.message));
};
document.addEventListener('keydown', e => {
  if (['INPUT', 'SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowRight') ir(i + 1);
  else if (e.key === 'ArrowLeft') ir(i - 1);
  else if (e.key === 'Home') ir(0);
  else if (e.key === 'End') ir(Infinity);
  else if (e.key === ' ') { e.preventDefault(); alternar(); }
});
if (window.TRAZA) cargar(window.TRAZA);
