# Matriz de combinaciones

Generada con `python docs/herramientas/matriz.py`. Cada fila es una ejecución real del simulador; sirve para estudiar **qué cambia en cada combinación** antes de la exposición.

## 1. Planificación de procesos

Escenario `x_matriz_procesos.json`: dos procesos CPU-bound (C1 con prioridad 1, C2 con prioridad 2) y dos I/O-bound (I1 con prioridad 3, I2 con prioridad 4), quantum 3. Menor número = mayor prioridad.

| Algoritmo | Exprop. por llegada | Prioridad | Aging | Zombie | Espera prom. | Retorno prom. | Respuesta prom. | Throughput | Cambios ctx | Exprop. quantum | Exprop. llegada | Interrup. | Orden de fin |
|---|---|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| FCFS | no | off | 0 | inmediata | 12,25 | 23,0 | 10,5 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| FCFS+prioridad fija | no | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| FCFS+prioridad fija | no | fija | 4 | inmediata | 12,25 | 23,0 | 10,5 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| FCFS+prioridad dinamica | no | dinamica | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| FCFS+prioridad dinamica | no | dinamica | 4 | inmediata | 12,25 | 23,0 | 10,5 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| FCFS+prioridad fija expropiativo | sí | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| FCFS+prioridad fija expropiativo | sí | fija | 4 | inmediata | 13,75 | 24,5 | 9,75 | 0,121 | 8 | 0 | 1 | 47 | C2 C1 I2 I1 |
| FCFS+prioridad dinamica expropiativo | sí | dinamica | 0 | inmediata | 13,0 | 23,75 | 10,5 | 0,121 | 8 | 0 | 1 | 47 | C2 C1 I1 I2 |
| FCFS+prioridad dinamica expropiativo | sí | dinamica | 4 | inmediata | 14,75 | 25,5 | 7,25 | 0,129 | 10 | 0 | 3 | 45 | C2 C1 I1 I2 |
| SJF | no | off | 0 | inmediata | 12,5 | 23,25 | 9,25 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| SJF+prioridad fija | no | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| SJF+prioridad fija | no | fija | 4 | inmediata | 12,0 | 22,75 | 11,0 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I1 I2 |
| SJF+prioridad dinamica | no | dinamica | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| SJF+prioridad dinamica | no | dinamica | 4 | inmediata | 12,0 | 22,75 | 11,0 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I1 I2 |
| SJF expropiativo | sí | off | 0 | inmediata | 7,25 | 18,0 | 1,0 | 0,129 | 11 | 0 | 4 | 45 | I2 I1 C2 C1 |
| SJF+prioridad fija expropiativo | sí | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| SJF+prioridad fija expropiativo | sí | fija | 4 | inmediata | 13,5 | 24,25 | 7,75 | 0,129 | 13 | 0 | 6 | 45 | C1 I1 C2 I2 |
| SJF+prioridad dinamica expropiativo | sí | dinamica | 0 | inmediata | 13,5 | 24,25 | 10,0 | 0,114 | 9 | 0 | 2 | 49 | C1 C2 I1 I2 |
| SJF+prioridad dinamica expropiativo | sí | dinamica | 4 | inmediata | 14,25 | 25,0 | 4,75 | 0,129 | 14 | 0 | 7 | 45 | C2 I1 C1 I2 |
| RR | no | off | 0 | inmediata | 15,25 | 26,0 | 2,5 | 0,129 | 12 | 5 | 0 | 45 | I2 C2 C1 I1 |
| RR+prioridad fija | no | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 12 | 5 | 0 | 48 | C1 C2 I2 I1 |
| RR+prioridad fija | no | fija | 4 | inmediata | 14,5 | 25,25 | 7,25 | 0,129 | 12 | 5 | 0 | 45 | C1 C2 I2 I1 |
| RR+prioridad dinamica | no | dinamica | 0 | inmediata | 15,0 | 25,75 | 6,25 | 0,129 | 12 | 5 | 0 | 45 | C2 I1 I2 C1 |
| RR+prioridad dinamica | no | dinamica | 4 | inmediata | 15,0 | 25,75 | 3,5 | 0,129 | 12 | 5 | 0 | 45 | I2 I1 C2 C1 |
| PRIORIDAD | no | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| PRIORIDAD | no | fija | 4 | inmediata | 12,25 | 23,0 | 10,5 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| PRIORIDAD dinámica | no | dinamica | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| PRIORIDAD dinámica | no | dinamica | 4 | inmediata | 12,25 | 23,0 | 10,5 | 0,121 | 7 | 0 | 0 | 47 | C1 C2 I2 I1 |
| PRIORIDAD | sí | fija | 0 | inmediata | 12,0 | 22,75 | 12,0 | 0,118 | 7 | 0 | 0 | 48 | C1 C2 I2 I1 |
| PRIORIDAD | sí | fija | 4 | inmediata | 13,75 | 24,5 | 9,75 | 0,121 | 8 | 0 | 1 | 47 | C2 C1 I2 I1 |
| PRIORIDAD dinámica | sí | dinamica | 0 | inmediata | 13,0 | 23,75 | 10,5 | 0,121 | 8 | 0 | 1 | 47 | C2 C1 I1 I2 |
| PRIORIDAD dinámica | sí | dinamica | 4 | inmediata | 14,75 | 25,5 | 7,25 | 0,129 | 10 | 0 | 3 | 45 | C2 C1 I1 I2 |
| RR+prioridad fija | no | fija | 0 | recolector | 12,0 | 22,75 | 12,0 | 0,111 | 12 | 5 | 0 | 50 | C1 C2 I2 I1 |

**Qué observar (en este escenario):** SJF expropiativo (SRTF) da la menor espera promedio porque atiende primero las ráfagas cortas de los I/O-bound; SJF no expropiativo no mejora a FCFS porque C1 llega solo y nadie lo interrumpe. RR sin prioridades da la mejor respuesta a costa de más cambios de contexto. Con prioridad fija terminan primero C1 y C2 (prioridad alta) y los I/O-bound esperan; con RR, prioridad dinámica y aging los I/O-bound terminan primero. La política zombie retiene recursos: más interrupciones y menor throughput. Las conclusiones dependen del escenario: no son reglas generales.

## 2. Memoria paginada

Escenario `m3_tlb_bits_local.json` (dos procesos, escrituras que activan el bit M, dos marcos del SO).

| Reemplazo | Alcance | Marcos | TLB | Fallos de página | Reemplazos | Escrituras a swap | Hit ratio TLB | EAT con fallos (ns) | Ticks |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| FIFO | global | 3 | 0 | 9 | 6 | 1 | — | 10714342,9 | 27 |
| FIFO | global | 3 | 2 | 9 | 6 | 1 | 0,0 | 10714342,9 | 27 |
| FIFO | global | 4 | 0 | 6 | 4 | 1 | — | 8333400,0 | 20 |
| FIFO | global | 4 | 2 | 6 | 4 | 1 | 0,056 | 8333400,0 | 20 |
| FIFO | local | 3 | 0 | 10 | 8 | 1 | — | 11363690,9 | 27 |
| FIFO | local | 3 | 2 | 10 | 8 | 1 | 0,0 | 11363690,9 | 27 |
| FIFO | local | 4 | 0 | 5 | 2 | 1 | — | 7353011,8 | 22 |
| FIFO | local | 4 | 2 | 5 | 2 | 1 | 0,059 | 7353011,8 | 22 |
| LRU | global | 3 | 0 | 10 | 8 | 1 | — | 11363690,9 | 27 |
| LRU | global | 3 | 2 | 10 | 8 | 1 | 0,0 | 11363690,9 | 27 |
| LRU | global | 4 | 0 | 5 | 2 | 1 | — | 7353011,8 | 22 |
| LRU | global | 4 | 2 | 5 | 2 | 1 | 0,059 | 7353011,8 | 22 |
| LRU | local | 3 | 0 | 10 | 8 | 1 | — | 11363690,9 | 27 |
| LRU | local | 3 | 2 | 10 | 8 | 1 | 0,0 | 11363690,9 | 27 |
| LRU | local | 4 | 0 | 5 | 2 | 1 | — | 7353011,8 | 22 |
| LRU | local | 4 | 2 | 5 | 2 | 1 | 0,059 | 7353011,8 | 22 |
| OPTIMO | global | 3 | 0 | 5 | 2 | 1 | — | 7353011,8 | 21 |
| OPTIMO | global | 3 | 2 | 5 | 2 | 1 | 0,118 | 7353011,8 | 21 |
| OPTIMO | global | 4 | 0 | 4 | 1 | 1 | — | 6250075,0 | 18 |
| OPTIMO | global | 4 | 2 | 4 | 1 | 1 | 0,125 | 6250075,0 | 18 |
| OPTIMO | local | 3 | 0 | 8 | 7 | 2 | — | 10000060,0 | 24 |
| OPTIMO | local | 3 | 2 | 8 | 7 | 2 | 0,0 | 10000060,0 | 24 |
| OPTIMO | local | 4 | 0 | 4 | 1 | 1 | — | 6250075,0 | 18 |
| OPTIMO | local | 4 | 2 | 4 | 1 | 1 | 0,125 | 6250075,0 | 18 |
| CLOCK | global | 3 | 0 | 10 | 8 | 1 | — | 11363690,9 | 27 |
| CLOCK | global | 3 | 2 | 10 | 8 | 1 | 0,0 | 11363690,9 | 27 |
| CLOCK | global | 4 | 0 | 5 | 2 | 1 | — | 7353011,8 | 22 |
| CLOCK | global | 4 | 2 | 5 | 2 | 1 | 0,059 | 7353011,8 | 22 |
| CLOCK | local | 3 | 0 | 9 | 8 | 2 | — | 10714342,9 | 26 |
| CLOCK | local | 3 | 2 | 9 | 8 | 2 | 0,0 | 10714342,9 | 26 |
| CLOCK | local | 4 | 0 | 5 | 2 | 1 | — | 7353011,8 | 22 |
| CLOCK | local | 4 | 2 | 5 | 2 | 1 | 0,059 | 7353011,8 | 22 |

## 3. Memoria contigua

Escenario `m2_memoria_contigua.json` (como el ejemplo del profesor: región del SO y procesos de distinto tamaño).

| Ajuste | Rechazos por memoria | Fragmentación externa final | Espera prom. | Retorno prom. | Ticks |
|---|--:|--:|--:|--:|--:|
| primer | 4 | 0,0 | 8,0 | 14,33 | 22 |
| mejor | 4 | 0,0 | 8,0 | 14,33 | 22 |
| peor | 4 | 0,0 | 8,0 | 14,33 | 22 |
| siguiente | 4 | 0,0 | 8,0 | 14,33 | 22 |

## 4. Temporizador y quantum

Escenario `e1_tres_procesos_rr4.json`.

| Período del timer | Quantum | IRQ0 | Interrupciones | Cambios ctx | Espera prom. | Resultados A/B/C/D |
|--:|--:|--:|--:|--:|--:|---|
| 1 | 2 | 24 | 38 | 13 | 8,0 | 11/7/0/6 |
| 1 | 4 | 23 | 35 | 7 | 7,0 | 15/2/1/5 |
| 1 | 8 | 26 | 42 | 7 | 7,33 | 18/0/0/8 |
| 2 | 2 | 12 | 26 | 13 | 8,0 | 0/7/0/5 |
| 2 | 4 | 11 | 23 | 9 | 8,33 | 6/4/0/1 |
| 2 | 8 | 13 | 29 | 7 | 7,33 | 7/0/0/6 |
| 4 | 2 | 5 | 17 | 8 | 8,0 | 0/3/1/1 |
| 4 | 4 | 5 | 17 | 8 | 8,0 | 0/3/1/1 |
| 4 | 8 | 6 | 22 | 7 | 7,33 | 4/0/0/2 |
