# Manual de uso del simulador

## 1. Cómo correrlo

**Requisito único:** Python 3.10 o superior. No hay dependencias externas.

| Sistema | Comprobar Python | Ejecutar el ejemplo |
|---|---|---|
| Windows | `py --version` | `py -m simulador escenarios/e1_tres_procesos_rr4.json` |
| Linux | `python3 --version` | `python3 -m simulador escenarios/e1_tres_procesos_rr4.json` |
| macOS | `python3 --version` | `python3 -m simulador escenarios/e1_tres_procesos_rr4.json` |

Desde la carpeta del repositorio clonado:

```bash
git clone https://github.com/devronaldaz/Simulador-de-sistema-operativo-dirigido-por-interrupciones-.git
cd Simulador-de-sistema-operativo-dirigido-por-interrupciones-
py -m simulador escenarios/e1_tres_procesos_rr4.json
```

En este manual se usa `py`; en Linux y macOS reemplácelo por `python3`.

## 2. Las tres formas de verlo

### 2.1 Consola paso a paso (modo principal)

```bash
py -m simulador escenarios/e1_tres_procesos_rr4.json
```

Cada Enter muestra **un paso** con estado antes, estado después, porqué, transición, CPU, colas, memoria y contadores.

| Tecla | Acción |
|---|---|
| Enter | Siguiente paso |
| `t` | Resto del tick |
| `c` | Contadores de interrupciones |
| `q` | Colas y motivo del último cambio de cada proceso |
| `m` | Mapa de memoria (frames o regiones, con registros en hexadecimal) |
| `g N` | Ir al paso N |
| `a` | Automático hasta el final |
| `x` | Salir con el resumen |

Otros modos: `--modo tick` (un tick por Enter), `--modo auto --velocidad 5` (5 pasos por segundo) y `--modo resumen` (solo el resumen).

### 2.2 Visor gráfico (tiempo real)

```bash
py -m simulador escenarios/e1_tres_procesos_rr4.json --visor --abrir
```

Abre `visor/index.html` en el navegador con la simulación. **Si abre `index.html` sin haber usado `--visor`, verá "Sin traza cargada"**: use el botón *Cargar traza JSON* con un archivo generado con `--traza`.

| Panel | Qué muestra |
|---|---|
| Mapa de estados | Los estados (incluido ZOMBIE) con las transiciones rotuladas; la última resaltada en naranja |
| Flujo de la CPU | Cola de nuevos → cola de listos → planificador → despachador → CPU (modo usuario o kernel) → controlador de interrupciones; se ilumina la etapa que actúa |
| Línea de tiempo | Una fila por proceso con su estado en cada tick, y una fila con las interrupciones del tick (T timer, E E/S, S syscall, F fallo, X excepción, N NMI, W worst time, K kill, P protección). Clic en una celda para saltar a ese tick |
| PCB | PID, estado, PC, prioridad, ráfaga, restante, CPU usado, quantum, espera, interrupciones, cambios de contexto, E/S, clase, padre (y base/límite en contigua) |
| Mapa de memoria | N.º de frame o región, registro inicial, registro final (hexadecimal), proceso o SO, página, estado del frame y **estado del proceso dueño** |
| MMU | La última traducción: VA → (p, d) → marco → PA, o base + d |
| Tabla de páginas y TLB | Del proceso elegido: página, marco, bits R y M |
| Interrupciones y métricas | Contadores por tipo y proceso; utilización, throughput, espera promedio y cambios de contexto en vivo |
| Registro | Todos los pasos; clic para saltar |

Controles: ◀ ▶ (o flechas del teclado), Reproducir/Pausa (espacio), velocidad de 0,5× a 20×, barra de posición.

### 2.3 Resumen y archivo de traza

```bash
py -m simulador escenarios/e1_tres_procesos_rr4.json --modo resumen --traza trazas/e1.json
```

## 3. Parámetros

Todos se pueden poner en la sección `config` del JSON o en la línea de comandos (los guiones bajos pasan a guiones: `worst_time` → `--worst-time`). La línea de comandos tiene prioridad.

### 3.1 Planificación

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `planificador` | `FCFS`, `SJF`, `RR`, `PRIORIDAD` | `RR` | Criterio de elección |
| `quantum` | entero ≥ 1 | 4 | Solo RR |
| `expropiativo` | `si`, `no` | según el algoritmo | Expropiación por llegada: SJF expropiativo = SRTF; PRIORIDAD lo es por defecto |
| `prioridad` | `off`, `fija`, `dinamica` | `off` | Se combina con **cualquier** algoritmo (RR + prioridades = `--prioridad fija`). Menor número = mayor prioridad. `dinamica`: baja la prioridad de quien usa mucha CPU y sube la de quien se bloquea por E/S |
| `aging` | entero ≥ 0 | 0 | Cada N ticks en LISTO la prioridad mejora 1 nivel |
| `grado_multiprogramacion` | entero ≥ 0 | 0 (sin límite) | Planificador de largo plazo: máximo de procesos admitidos |

### 3.2 Tiempos y procesos

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `worst_time` | entero ≥ 0 | 0 (sin tope) | Tope de ráfaga de CPU |
| `worst_time_modo` | `rechazar`, `truncar`, `cota_sjf`, `defecto` | `rechazar` | `rechazar`: no admite procesos con ráfaga mayor (como el ejemplo del profesor con 100). `truncar`: el proceso se corta al llegar al tope (interrupción WORST_TIME). `cota_sjf`: SJF ordena por min(ráfaga, tope). `defecto`: procesos sin `burst` usan el tope |
| `politica_zombie` | `inmediata`, `recolector` | `inmediata` | `recolector`: al terminar el proceso pasa a ZOMBIE y conserva su memoria hasta que init lo recoge |
| `recolector_ticks` | entero ≥ 1 | 3 | Ticks como zombie antes de la recolección |
| `periodo_timer` | entero ≥ 1 | 1 | Ticks entre interrupciones del temporizador |
| `latencia_read`, `latencia_fallo`, `latencia_swap` | enteros | 4, 3, 2 | Duración de la lectura, de la carga de página y de la escritura a swap |

### 3.3 Memoria

| Parámetro | Valores | Por defecto | Efecto |
|---|---|---|---|
| `mmu` | `paginada`, `contigua` | `paginada` | Paginación por demanda, o regiones con base y límite (como el ejemplo del profesor) |
| `marcos` | entero ≥ 1 | 3 | Marcos para procesos (paginada) |
| `marcos_so` | entero ≥ 0 | 0 | Marcos reservados al SO al inicio de la memoria |
| `tamano_marco` | bytes | 4096 | Tamaño de página y marco |
| `reemplazo` | `FIFO`, `LRU`, `OPTIMO`, `CLOCK` | `LRU` | Algoritmo de reemplazo |
| `alcance` | `global`, `local` | `global` | Con `local`, un proceso solo reemplaza sus propias páginas |
| `tlb` | entero ≥ 0 | 0 (sin TLB) | Entradas de la TLB |
| `pagina_0_residente_al_admitir` | `true`, `false` | `true` | Carga la página 0 al admitir |
| `memoria_total`, `memoria_so` | bytes | 65536, 8192 | Memoria y región del SO (contigua) |
| `ajuste` | `primer`, `mejor`, `peor`, `siguiente` | `primer` | Política de asignación de huecos (contigua) |
| `ws_delta` | entero | 6 | Ventana del conjunto de trabajo |

## 4. Escribir un escenario

```json
{
  "nombre": "Mi escenario",
  "config": { "planificador": "SJF", "marcos": 4 },
  "procesos": [
    { "pid": "P1", "llegada": 0, "burst": 7, "prioridad": 2 },
    { "pid": "P2", "llegada": 2, "burst": 4, "tamano": 8192, "es": [2] },
    { "pid": "P3", "llegada": 3, "guion": ["cpu:0", "write:@4200", "read:0", "cpu:1", "exit:1"] }
  ],
  "eventos_externos": [ { "tick": 5, "tipo": "KILL", "pid": "P1" }, { "tick": 8, "tipo": "NMI" } ]
}
```

- **Notación corta:** `burst` (ticks de CPU), `tamano` (bytes; define cuántas páginas usa), `prioridad`, `llegada` y opcionalmente `es` (después de qué tick de su ráfaga hace una lectura de disco).
- **Guion (modo avanzado):** `cpu:p` cómputo en la página *p* · `write:p` escritura (activa el bit M) · `read:p` lectura de disco · `syscall:p:getpid` llamada sin espera · `div0:p` división por cero · `exit:p` fin. En lugar de la página se puede dar una dirección: `cpu:@13322`.
- **Eventos externos:** `NMI` y `KILL` (con `pid`).

## 5. Escenarios incluidos

| Archivo | Muestra | Prueba con |
|---|---|---|
| `e1_tres_procesos_rr4.json` | El ejemplo del informe: las 6 transiciones, fallo de página, NMI | — |
| `p1_fcfs_diapositiva.json` | FCFS de la diapositiva (espera promedio 17) | — |
| `p2_sjf_diapositiva.json` | SJF de la diapositiva (espera 4; expropiativo 3) | `--expropiativo si` |
| `p3_prioridad_inversa_cpu.json` | El error que advirtió el docente | `--prioridad fija` frente a `dinamica` |
| `p4_rr_prioridades.json` | RR + prioridades | — |
| `p5_inanicion_aging.json` | Inanición y aging | `--aging 0` frente a `4` |
| `p6_worst_time.json` | Worst time de 50 | `--worst-time-modo truncar` |
| `p7_zombie_kill.json` | Zombie y señal kill | `--politica-zombie inmediata` |
| `p8_largo_plazo.json` | Grado de multiprogramación | `--grado-multiprogramacion 0` |
| `m1_reemplazo_semana14.json` | Cadena 7 0 1 2 0 3 0 4 2 3 0 3 2 | `--reemplazo FIFO`, `LRU`, `OPTIMO`, `CLOCK` |
| `m2_memoria_contigua.json` | Memoria contigua, falta de memoria, fragmentación, protección | `--ajuste mejor`, `peor`, `siguiente` |
| `m3_tlb_bits_local.json` | TLB, bits R y M, marcos del SO, alcance local | `--tlb 0`, `--alcance global` |
| `s1`, `s3b`, `s6`, `s8` | Cambio de contexto, Belady, FCFS frente a RR, hiperpaginación | ver README |
| `x_matriz_procesos.json` | Escenario de la matriz de combinaciones | `docs/MATRIZ_COMBINACIONES.md` |

## 6. Cambios en vivo (lo que puede pedir el profesor)

| Pedido | Cómo se hace | Qué mirar |
|---|---|---|
| **RR con prioridades** | `py -m simulador escenarios/p4_rr_prioridades.json` o, con cualquier escenario, `--planificador RR --prioridad fija` | Paso PLAN: el planificador elige por prioridad y RR expropia por quantum |
| **FCFS o SJF con worst time de 50** | `--planificador FCFS --worst-time 50` (rechaza ráfagas > 50) o `--worst-time-modo truncar` (las corta en 50) | En `p6_worst_time.json`: P2 (80) rechazado o cortado; interrupción WORST_TIME |
| **Agregar el estado zombie** | `--politica-zombie recolector --recolector-ticks 3` | Mapa de estados con ZOMBIE; frames del zombie siguen ocupados en el mapa de memoria |
| **Prioridad inversa al uso de CPU** | `--prioridad dinamica` (+ `--aging 4`) | Pasos SCHED "prioridad dinámica" y "aging" |
| **SJF expropiativo** | `--planificador SJF --expropiativo si` | Pasos TRANS "expropiación" en los momentos 3 y 4 |
| **Cambiar la memoria** | `--reemplazo CLOCK --alcance local --tlb 4`, o `--mmu contigua --ajuste mejor` | Mapa de memoria, MMU y resumen de memoria |
| **Limitar la multiprogramación** | `--grado-multiprogramacion 2` | Cola de nuevos y pasos del planificador de largo plazo |

### 6.1 Cambios de código (si el pedido no es un parámetro)

| Pedido | Dónde | Cómo |
|---|---|---|
| **Nuevo estado o transición** | `simulador/modelos.py` | Agregar el valor a `Estado` y la fila a `TRANSICIONES` (origen, destino → id, rótulo). Para dibujarlo, una posición en `POS` de `visor/visor.js` |
| **Nuevo algoritmo de planificación** | `simulador/planificacion/base.py` | Una entrada en `ALGORITMOS` (criterio, quantum, expropiativo). Config, CLI y visor la leen solos |
| **Nueva política de reemplazo** | `simulador/memoria/reemplazo.py` | Una función y su entrada en `POLITICAS` y `CRITERIOS` |
| **Nuevo tipo de interrupción** | `modelos.TipoInt`, `ivt.ENTRADAS`, una ISR en `isr.py` | El contador y el visor la muestran automáticamente |

## 7. Cómo leer el resumen

- **Interrupciones por proceso y tipo:** cada interrupción se atribuye a un proceso o al Sistema; la fila TOTAL debe cuadrar (invariantes "OK").
- **ISR del timer A/B/C/D:** continúa / expropia / renueva el quantum / sin proceso.
- **Expropiaciones:** por quantum (timer) y por llegada o prioridad.
- **Memoria:** fallos, reemplazos, escrituras a swap, tasa de fallos y EAT; con TLB, aciertos, fallos y hit ratio. En contigua: rechazos por falta de memoria y fragmentación externa.
- **Métricas:** espera, retorno, respuesta, utilización de CPU y throughput (los cinco criterios de la Sesión 6 – Planificación).

## 8. Pruebas y matriz

```bash
py -m unittest discover -s pruebas -t pruebas
py docs/herramientas/matriz.py
```

La primera corre las 49 pruebas automáticas, que incluyen los ejemplos de las diapositivas. La segunda regenera `docs/MATRIZ_COMBINACIONES.md`.
