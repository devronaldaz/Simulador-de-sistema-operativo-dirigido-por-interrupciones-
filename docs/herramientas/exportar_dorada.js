// Exporta la traza "dorada" del ejemplo E1 a partir de la herramienta de referencia
// del informe (generar_traza.js). La usa la prueba pruebas/test_traza_dorada.py.
// Uso: node docs/herramientas/exportar_dorada.js
'use strict';
const cp = require('child_process'), fs = require('fs'), path = require('path');

const salida = cp.execFileSync(process.execPath, [path.join(__dirname, 'generar_traza.js'), '--json'], { encoding: 'utf8' });
const d = JSON.parse(salida);
const estado = s => (s.split(': ')[1] || '').split(' ')[0];
const pasos = d.steps.map(s => ({
  paso: s.n, tick: s.t, tipo_paso: s.kind, total: s.total,
  int_tipo: s.intTipo || null,
  transicion: s.kind === 'TRANS' ? { pid: s.antes.split(':')[0], de: estado(s.antes), a: estado(s.despues) } : null,
}));
const destino = path.join(__dirname, '..', '..', 'pruebas', 'datos', 'e1_esperada.json');
fs.writeFileSync(destino, JSON.stringify({ origen: 'docs/herramientas/generar_traza.js', pasos, resumen: d.resumen }, null, 1));
console.log(`${pasos.length} pasos escritos en ${destino}`);
