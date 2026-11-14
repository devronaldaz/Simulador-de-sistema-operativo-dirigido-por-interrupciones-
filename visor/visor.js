// Visor de la bitácora (requisito R5). Solo LEE la traza: no simula nada.
'use strict';

const ESTADOS = {
  NUEVO:      { x: 30,  y: 30,  color: 'var(--nuevo)' },
  TERMINADO:  { x: 560, y: 30,  color: 'var(--terminado)' },
  LISTO:      { x: 150, y: 150, color: 'var(--listo)' },
  EJECUTANDO: { x: 440, y: 150, color: 'var(--ejecutando)' },
  BLOQUEADO:  { x: 295, y: 270, color: 'var(--bloqueado)' },
};
const ANCHO = 170, ALTO = 70;
// Las seis transiciones del mapa de la Sesión 6 (diap. 10).
const ARISTAS = {
  T1: { d: 'M115,100 L190,148', texto: ['T1 Admitido'], lx: 120, ly: 138, ancla: 'end' },
  T2: { d: 'M320,185 L436,185', texto: ['T2 Despacho del', 'planificador'], lx: 378, ly: 203, ancla: 'middle' },
  T3: { d: 'M520,148 Q395,85 270,148', texto: ['T3 Interrupción (fin de quantum)'], lx: 395, ly: 108, ancla: 'middle' },
  T4: { d: 'M540,222 Q545,305 469,305', texto: ['T4 Espera de', 'E/S o evento'], lx: 552, ly: 268, ancla: 'start' },
  T5: { d: 'M293,305 Q215,305 222,224', texto: ['T5 Fin de E/S', 'o evento'], lx: 212, ly: 268, ancla: 'end' },
  T6: { d: 'M575,148 L625,104', texto: ['T6 Salida'], lx: 612, ly: 140, ancla: 'start' },
};

let traza = null, i = 0, temporizador = null;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function dibujarBase() {
  const svg = $('svg-estados');
  let html = '<defs><marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto">' +
    '<path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>';
  for (const [id, a] of Object.entries(ARISTAS)) {
    html += `<path id="ar-${id}" class="arista" d="${a.d}" marker-end="url(#flecha)" style="color:var(--suave)"/>` +
      `<text id="et-${id}" class="etiqueta" x="${a.lx}" y="${a.ly}" text-anchor="${a.ancla}">` +
      a.texto.map((l, n) => `<tspan x="${a.lx}" dy="${n ? 13 : 0}">${l}</tspan>`).join('') + '</text>';
  }
  for (const [nombre, e] of Object.entries(ESTADOS)) {
    html += `<g class="estado" id="es-${nombre}"><rect x="${e.x}" y="${e.y}" width="${ANCHO}" height="${ALTO}" rx="10" style="stroke:${e.color}"/>` +
      `<text class="nombre" x="${e.x + ANCHO / 2}" y="${e.y + 22}">${nombre}</text><g class="fichas-svg"></g></g>`;
  }
  svg.innerHTML = html;
}

function ultimaTransicion(hasta) {
  for (let k = hasta; k >= 0; k--) if (traza.pasos[k].transicion) return k;
  return -1;
}

function pintar() {
  if (!traza) return;
  const paso = traza.pasos[i], v = paso.vista, total = traza.pasos.length;
  $('posicion').textContent = `paso ${paso.paso}/${total} · t=${paso.tick}`;
  $('barra').value = i + 1;

  // Fichas de procesos dentro de su estado
  const porEstado = {};
  for (const [pid, est] of Object.entries(v.estados)) (porEstado[est] = porEstado[est] || []).push(pid);
  const kTrans = ultimaTransicion(i), tr = kTrans >= 0 ? traza.pasos[kTrans].transicion : null;
  for (const [nombre, e] of Object.entries(ESTADOS)) {
    const g = document.querySelector(`#es-${nombre} .fichas-svg`);
    const pids = porEstado[nombre] || [];
    g.innerHTML = pids.map((pid, n) => {
      const x = e.x + 12 + n * 40, y = e.y + 34;
      const movida = tr && kTrans === i && tr.pid === pid ? ' movida' : '';
      return `<g class="ficha${movida}"><rect x="${x}" y="${y}" width="34" height="22"/><text x="${x + 17}" y="${y + 15}">${pid}</text></g>`;
    }).join('');
    document.getElementById(`es-${nombre}`).classList.toggle('activo', pids.length > 0);
  }
  // Transición reciente resaltada; la anterior, punteada
  for (const id of Object.keys(ARISTAS)) {
    $(`ar-${id}`).setAttribute('class', 'arista');
    $(`ar-${id}`).style.color = 'var(--suave)';
    $(`et-${id}`).setAttribute('class', 'etiqueta');
  }
  if (tr) {
    const clase = kTrans === i ? 'reciente' : 'previa';
    $(`ar-${tr.id}`).setAttribute('class', `arista ${clase}`);
    $(`ar-${tr.id}`).style.color = 'var(--resalte)';
    if (clase === 'reciente') $(`et-${tr.id}`).setAttribute('class', 'etiqueta reciente');
  }

  // Porqué del paso actual
  const titulo = paso.transicion
    ? `${paso.transicion.pid}: ${paso.transicion.de} → ${paso.transicion.a} (${paso.transicion.id})`
    : `${paso.tipo_paso} · ${paso.componente}`;
  $('porque').innerHTML = `<div class="titulo">${esc(titulo)}${paso.int_id ? ` · INT #${paso.int_id}` : ''}</div>` +
    `<div>Causa: ${esc(paso.causa)}</div><div class="cambio">Antes: ${esc(paso.antes)}<br>Después: ${esc(paso.despues)}</div>`;

  // Paneles
  $('cpu').innerHTML = v.cpu ? `<span class="chip">${v.cpu}</span> quantum ${v.quantum ?? '—'}` : '<span class="vacio">libre / ociosa</span>';
  $('listos').innerHTML = v.listos.length ? v.listos.map(p => `<span>${p}</span>`).join(' → ') : '<span class="vacio">vacía</span>';
  $('disco').innerHTML = v.disco.length
    ? v.disco.map(d => `<div><span class="chip">${d.pid}</span> ${d.tipo === 'read' ? 'lectura' : 'carga de página (DMA)'} hasta t=${d.fin}</div>`).join('')
    : '<span class="vacio">vacía</span>';
  $('marcos').innerHTML = v.marcos.map(m =>
    `<div class="marco"><span>M${m.id}: ${m.pagina ?? '<span class="vacio">libre</span>'} ${m.cargando ? '<span class="carga">(cargando)</span>' : ''}</span>` +
    `<span class="vacio">${m.ultimo_uso >= 0 && !m.cargando && m.pagina ? 'uso t' + m.ultimo_uso : ''}</span></div>`).join('');
  const tipos = ['TIMER', 'ES_DMA', 'SYSCALL', 'FALLO_PAG', 'EXCEPCION', 'NMI'];
  $('interrupciones').innerHTML = '<table class="contadores"><tbody>' +
    tipos.map(t => `<tr><td>${t}</td><td>${v.contadores[t]}</td></tr>`).join('') +
    `<tr><th>Total</th><th>${v.contadores.total}</th></tr></tbody></table>` +
    '<div style="margin-top:6px">' + Object.entries(v.por_proceso).map(([p, n]) => `${p}=${n}`).join(' · ') + '</div>';

  // Registro
  document.querySelectorAll('#filas tr.actual').forEach(f => f.classList.remove('actual'));
  const fila = $('filas').children[i];
  if (fila) { fila.classList.add('actual'); fila.scrollIntoView({ block: 'nearest' }); }
}

function cargar(datos) {
  traza = datos; i = 0;
  const r = traza.resumen;
  $('escenario').textContent = `${traza.escenario} · ${traza.config.planificador} q=${traza.config.quantum} · ` +
    `${traza.config.marcos} marcos ${traza.config.reemplazo} · ${r.ticks} ticks · ${r.interrupciones} interrupciones`;
  $('barra').max = traza.pasos.length;
  $('filas').innerHTML = traza.pasos.map((p, k) =>
    `<tr data-k="${k}" class="${p.transicion ? 'trans' : ''}"><td>${p.paso}</td><td>${p.tick}</td><td>${p.tipo_paso}</td>` +
    `<td>${esc(p.componente)}</td><td>${esc(p.antes)} → ${esc(p.despues)}</td><td>${esc(p.causa)}</td></tr>`).join('');
  pintar();
}

function ir(k) { if (traza) { i = Math.max(0, Math.min(traza.pasos.length - 1, k)); pintar(); } }
function alternar() {
  if (temporizador) { clearInterval(temporizador); temporizador = null; $('reproducir').textContent = 'Reproducir'; return; }
  temporizador = setInterval(() => { if (!traza || i >= traza.pasos.length - 1) return alternar(); ir(i + 1); }, 700);
  $('reproducir').textContent = 'Pausa';
}

dibujarBase();
$('inicio').onclick = () => ir(0);
$('anterior').onclick = () => ir(i - 1);
$('siguiente').onclick = () => ir(i + 1);
$('fin').onclick = () => ir(Infinity);
$('reproducir').onclick = alternar;
$('barra').oninput = e => ir(+e.target.value - 1);
$('filas').onclick = e => { const tr = e.target.closest('tr'); if (tr) ir(+tr.dataset.k); };
$('archivo').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  f.text().then(t => cargar(JSON.parse(t))).catch(err => alert('Traza inválida: ' + err.message));
};
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowRight') ir(i + 1);
  else if (e.key === 'ArrowLeft') ir(i - 1);
  else if (e.key === 'Home') ir(0);
  else if (e.key === 'End') ir(Infinity);
  else if (e.key === ' ') { e.preventDefault(); alternar(); }
});
if (window.TRAZA) cargar(window.TRAZA);
