# Estado del proyecto: simulador de SO dirigido por interrupciones

**Curso:** SI421U – Arquitectura de Computador y Sistemas Operativos (UNI-FIIS)
**Repositorio:** https://github.com/devronaldaz/Simulador-de-sistema-operativo-dirigido-por-interrupciones-
**Entregables:** programa (en GitHub) · PPT para exponer · informe monográfico

Este documento resume lo que hay. Cómo usarlo: [MANUAL_DE_USO.md](MANUAL_DE_USO.md). Resultados de todas las combinaciones: [MATRIZ_COMBINACIONES.md](MATRIZ_COMBINACIONES.md).

---

## 1. Versión 2: lo que se agregó al ejecutar el plan de cambios v2

Fuentes del plan: `PLAN_CAMBIOS_v2_con_teoria.md`, `ANALISIS_REPO_Y_EJEMPLO.md`, las presentaciones del curso (incluidas Sesión 7 y Semana 14) y los dos ejemplos Java del profesor (`SistemaOperativoFinal.jar` y `PROYECTO_SISTEMAS_OPERATIVOS.jar`, inspeccionados con `javap`, sin ejecutarlos).

| Fase del plan | Estado | Qué se hizo |
|---|---|---|
| 1 · Núcleo enchufable | ✅ | Registro único de algoritmos (`ALGORITMOS`) y de reemplazos (`POLITICAS`); máquina de estados como **tabla** (`TRANSICIONES`); **planificador y despachador en pasos separados** (PLAN + T2 con los 4 sub-pasos del despachador); la traza indica **cuál de los 5 momentos** disparó la planificación; configuración centralizada (JSON y CLI generada desde el registro) |
| 2 · Procesos | ✅ | **SJF** con y sin expropiación; **prioridades** combinables con cualquier algoritmo (RR + prioridades = un parámetro); **prioridad dinámica inversa al uso de CPU** y **aging**; **worst time** (rechazar, truncar, cota SJF, por defecto); **estado ZOMBIE** con recolector (retiene memoria); **señal kill**; **planificador de largo plazo** con grado de multiprogramación; throughput; tipos de interrupción nuevos (WORST_TIME, SENAL, PROTECCION); notación corta de procesos (`burst`, `tamano`, `prioridad`, `es`) |
| 3 · Memoria y MMU | ✅ (salvo opcionales) | **MMU paginada** con traducción visible (VA → p, d → marco → PA); tabla de páginas con **R y M**; **mapa por frames** con registro inicial y final en hexadecimal, proceso o **SO**, estado del frame y del proceso; reemplazo **Óptimo** y **Clock**; alcance **local o global**; escritura a swap solo si M=1; **TLB** con hit ratio; **EAT**; conjunto de trabajo; **MMU contigua** con base y límite y ajuste **primero, mejor, peor y siguiente** (como el ejemplo del profesor), con "no hay memoria suficiente" y fragmentación externa |
| 4 · Visor | ✅ | Mapa de estados leído de la traza (incluye ZOMBIE), **flujo** cola → planificador → despachador → CPU con modo usuario/kernel, **línea de tiempo** con interrupciones por tipo, **panel PCB**, mapa de memoria, MMU, tabla de páginas, TLB, **métricas en vivo** y control de **velocidad** |
| 5 · Combinaciones | ✅ (parcial) | `docs/herramientas/matriz.py` corre y tabula todas las combinaciones. **Faltan los simulacros cronometrados** del equipo |
| 6 · Varias CPU | ❌ | Opcional; no se hizo |
| 7 · Entrega | ✅ (parcial) | **Manual de uso** y README actualizados. Faltan: actualizar el informe monográfico, la PPT y las tareas de Notion |

### 1.1 Lo tomado de los ejemplos del profesor

- La **tabla de memoria** con N.º de frame, registro inicial, registro final, proceso (o SO) y estado.
- La **región del SO** en memoria y los mensajes "No hay memoria suficiente".
- **First/Best/Worst Fit** (y Next Fit).
- **SJF con opción expropiativa**.
- El **PCB** con ancestro, tiempo de espera y número de interrupciones.
- El **tope de burst**, como modo `rechazar` del worst time.

Lo que **no** se copió:
- Las interrupciones **aleatorias**: el simulador es determinista, para que cada ejecución sea reproducible.
- **LIFO:** no está en las acotaciones del docente.

---

## 2. Resultados verificados (49 pruebas automáticas en verde)

| Caso | Esperado (diapositivas / plan) | Obtenido |
|---|---|---|
| FCFS P1=24, P2=3, P3=3 | Espera 0, 24, 27 → promedio 17 | ✅ igual |
| SJF no expropiativo (P1–P4) | Espera 0, 6, 3, 7 → promedio 4; orden P1 P3 P2 P4 | ✅ igual |
| SJF expropiativo | Espera 9, 1, 0, 2 → promedio 3; Gantt P1 P2 P3 P2 P4 P1 | ✅ igual |
| FCFS frente a RR (10 × 100, q=1) | Retorno 550 y 995,5 | ✅ igual |
| Reemplazo, cadena de la Semana 14 | FIFO 10, LRU 9, Óptimo 7, Clock 9 | ✅ igual |
| Belady | FIFO 9 → 10; LRU 10 → 8; Óptimo 7 → 6 | ✅ igual |
| MMU | VA 13 322 → PA 37 898; VA 21 005 → PA 49 677 | ✅ igual |
| Base y límite | 4120 / 4999 / excepción; 5799; 9120 | ✅ igual |
| Ajustes con 212 KiB | Primero H2, mejor H4, peor H2 | ✅ igual |
| EAT con p = 0,00001 | ≈ 200 ns | ✅ 199,999 |
| Conjunto de trabajo | W(13, 6) = {0, 2, 3, 4} | ✅ igual |
| Aging (B de prioridad 5) | Primer despacho en t=16 (sin aging, t=24) | ✅ igual |
| Prioridad inversa al uso de CPU | El I/O-bound espera menos con prioridad dinámica | ✅ espera 20 → 12 |
| Ejemplo E1 del informe | 83 pasos de la traza dorada, 35 interrupciones, mismas métricas | ✅ igual (más 7 pasos PLAN nuevos: 90 en total) |

---

## 3. Lo que falta

| Pendiente | Prioridad |
|---|---|
| **Actualizar el informe** con lo nuevo: SJF, prioridades, worst time, zombie, MMU, TLB, Óptimo, Clock, contigua. Ojo: E1 pasó de 83 a 90 pasos | Alta |
| **PPT** y **simulacros cronometrados** de los cambios en vivo (sección 6 del manual) | Alta |
| **Tareas de Notion**: el CSV de 46 tareas no incluye el trabajo de la versión 2 | Media |
| Confirmar con el profesor las **preguntas abiertas**: qué significa el worst time de 50, quién libera al zombie, si basta un procesador, si el visor web es suficiente | Media |
| Opcionales: varias CPU, `wait` del padre para el zombie, segmentación, MLFQ, NRU, PFF, interrupciones aleatorias con semilla | Baja |
| La teoría de hardware de interrupciones del informe (8259A, IDT) sigue sin contrastar con el informe de interrupciones del grupo | Media |

### Decisiones tomadas sin confirmar con el profesor (todas son parámetros)

| Decisión | Valor por defecto | Alternativas |
|---|---|---|
| Worst time | `rechazar` (como el tope de 100 del ejemplo del profesor) | `truncar`, `cota_sjf`, `defecto` |
| Zombie | `inmediata` (para no alterar el ejemplo E1); los escenarios de zombie usan `recolector` | — |
| MMU | `paginada` | `contigua` |
| Prioridad | Menor número = mayor prioridad | — |
| Señal kill a un proceso que no está en la CPU | Queda pendiente en su PCB y se entrega cuando vuelve a ejecutar (dos interrupciones: envío y entrega) | — |
