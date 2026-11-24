# Simulador de SO dirigido por interrupciones

Simulador didáctico de un sistema operativo que realiza **gestión de procesos y de memoria dirigida por interrupciones**: ningún algoritmo corre por iniciativa propia, cada uno se ejecuta como respuesta a una interrupción mediante su rutina de servicio (ISR). No ejecuta código real: los procesos siguen un *guion* (o una ráfaga y un tamaño) y el programa muestra, **paso a paso, qué decidió el sistema y por qué**.

Proyecto del curso **SI421U – Arquitectura de Computador y Sistemas Operativos** (UNI-FIIS).

## Uso rápido

```bash
git clone https://github.com/devronaldaz/Simulador-de-sistema-operativo-dirigido-por-interrupciones-.git
cd Simulador-de-sistema-operativo-dirigido-por-interrupciones-
python -m simulador escenarios/e1_tres_procesos_rr4.json
```

En Windows use `py` en lugar de `python`. Solo requiere Python 3.10 o superior, sin dependencias.

| Comando | Qué hace |
|---|---|
| `python -m simulador ESCENARIO` | Paso a paso en la consola (Enter avanza) |
| `python -m simulador.servidor --abrir` | **Visor web**: elige los algoritmos de procesos y memoria y simula en el navegador (http://localhost:8766) |
| `python -m simulador ESCENARIO --visor --abrir` | Visor con la traza de ese escenario, sin servidor |
| `python -m simulador ESCENARIO --modo resumen` | Solo el resumen: contadores, memoria y métricas |
| `python -m simulador ESCENARIO --planificador SJF --expropiativo si` | Cualquier parámetro del JSON se puede cambiar desde la línea de comandos |

**Guía rápida de ejecución:** [docs/GUIA_RAPIDA.md](docs/GUIA_RAPIDA.md) (prenderlo paso a paso, controles del visor y errores comunes).

**Manual completo:** [docs/MANUAL_DE_USO.md](docs/MANUAL_DE_USO.md) (parámetros, formato de escenarios y cómo hacer los cambios en vivo).

## Qué simula

**Procesos**
- Estados Nuevo, Listo, Ejecutando, Bloqueado, **Zombie** y Terminado, definidos como **tabla de transiciones** (T1–T9), cada cambio con su porqué.
- Planificación **FCFS, SJF (con y sin expropiación), Round Robin y Prioridades**, combinables con prioridad fija o **dinámica (inversa al uso de CPU)** y **aging**.
- **Planificador y despachador separados**: el planificador muestra el momento que lo invocó (los 5 de la Sesión 6), su criterio y los candidatos; el despachador guarda y carga contextos.
- **Planificador de largo plazo** con grado de multiprogramación; **worst time** (rechazar, truncar, cota SJF, por defecto); **señal kill**; recolección de zombies.

**Interrupciones:** timer (IRQ0), disco/DMA (IRQ14), llamadas al sistema (INT 0x80), fallo de página (14), protección (13), excepción (0), worst time, señal y NMI, con prioridades, enmascaramiento y anidamiento, y un contador por tipo y por proceso.

**Memoria**
- **MMU paginada**: VA → (p, d) → marco → PA visible en cada acceso; tabla de páginas con bits R y M; **TLB** con hit ratio; reemplazo **FIFO, LRU, Óptimo y Clock**, global o local; escritura a swap solo si M=1; marcos reservados al SO; conjunto de trabajo y EAT.
- **MMU contigua** con base y límite y ajuste **primero, mejor, peor o siguiente** (como el ejemplo del profesor), con falta de memoria y fragmentación externa.
- **Mapa de memoria** con registro inicial y final en hexadecimal, proceso o SO, estado del frame y estado del proceso.

**Interfaz:** consola paso a paso y visor web en dos pantallas: primero se eligen los procesos y los algoritmos (planificación, paginación o contigua, reemplazo o ajuste); luego la simulación, separada en pestañas (procesos, línea de tiempo, PCB, memoria, interrupciones y métricas, bitácora) con control de velocidad.

## Requisitos del curso

| Req. | Qué pide | Dónde se ve |
|---|---|---|
| R1 | Ver **cómo** procesa, paso a paso | Consola `--modo paso`; visor con controles |
| R2 | Interrupciones y transiciones de estado | `simulador/modelos.py` (tabla), `procesos.py`, `isr.py` |
| R3 | El **porqué** de cada cambio | Campo `causa` de cada paso |
| R4 | Contar interrupciones (total, tipo, proceso) | `contadores.py`; resumen y visor |
| R5 | Visualización tipo mapa de estados | `visor/index.html` |
| R6 | Bitácora transaccional (antes, después, causa) | `bitacora.py`; exportación JSON |

## Pruebas

```bash
python -m unittest discover -s pruebas -t pruebas
```

Hay 49 pruebas. Además de la **traza dorada** del ejemplo E1, incluyen los resultados conocidos de las diapositivas:

| Caso | Resultado |
|---|---|
| FCFS 24/3/3 | Espera promedio 17 |
| SJF no expropiativo / expropiativo | 4 / 3 |
| FCFS frente a RR, 10 × 100 | 550 / 995,5 |
| Reemplazo, cadena de la Semana 14 | FIFO 10, LRU 9, Óptimo 7 y Clock 9 fallos |
| Belady | FIFO 9 → 10 |
| MMU | VA 13 322 → PA 37 898 |
| Ajustes | Primero, mejor y peor |
| EAT | ≈ 200 ns |
| Conjunto de trabajo | W(13, 6) = {0, 2, 3, 4} |

`python docs/herramientas/matriz.py` corre todas las combinaciones de configuración y genera [docs/MATRIZ_COMBINACIONES.md](docs/MATRIZ_COMBINACIONES.md).

## Estructura

```text
simulador/          motor (Python, sin dependencias)
  nucleo.py           ciclo principal por tick
  controlador_int.py  IRR, IMR, IF, prioridades, anidamiento; único punto de conteo
  ivt.py · isr.py     tabla de vectores y rutinas de servicio
  cpu.py · disco.py   hardware simulado (la CPU accede a memoria a través de la MMU)
  procesos.py         máquina de estados, colas y planificador de largo plazo
  planificacion/      registro de algoritmos, planificador y despachador
  memoria/            MMU paginada (gestor.py), contigua (contigua.py) y reemplazo
  contadores.py       contador de interrupciones e invariantes
  bitacora.py         bitácora transaccional y exportación JSON
  metricas.py         métricas y resumen
  consola.py · cli.py interfaz de texto
  servidor.py         servidor local del visor (API /api/simular)
visor/              visor web: configuración + simulación en pestañas
escenarios/         entradas JSON
pruebas/            pruebas automáticas
docs/               guía rápida, manual, matriz de combinaciones, estado y herramientas
```

## Integrantes

Alcantara Miranda, Sergio Daniel · Ancajima Cruz, Fabrizzio Alessandro · Ayala Zubilete, Matthews Ronald · Chávez Yauri, Yenny Esther · Flores Sánchez, Héctor David · Huamán Choque, Jairo Jhosimar
