# Simulador de SO dirigido por interrupciones

Simulador didáctico de un sistema operativo que realiza **gestión de procesos y de memoria dirigida por interrupciones**: ningún algoritmo corre por iniciativa propia, cada uno se ejecuta como respuesta a una interrupción mediante su rutina de servicio (ISR). No ejecuta código real: los procesos siguen un *guion* y el programa muestra, **paso a paso, qué decidió el sistema y por qué**.

Proyecto del curso **SI421U – Arquitectura de Computador y Sistemas Operativos** (UNI-FIIS).

## Requisitos que cumple

| Req. | Qué pide | Dónde se ve |
|---|---|---|
| R1 | Ver **cómo** procesa, paso a paso | Modo `--modo paso` de la consola y botones del visor |
| R2 | Interrupciones y las 6 transiciones de estado | `simulador/procesos.py` (T1–T6) e `simulador/isr.py` |
| R3 | El **porqué** de cada cambio | Campo `causa` de cada paso de la bitácora |
| R4 | Contar interrupciones (total, tipo, proceso) | `simulador/contadores.py`; resumen final y panel del visor |
| R5 | Visualización tipo mapa de estados | `visor/index.html` |
| R6 | Bitácora transaccional (antes, después, causa) | `simulador/bitacora.py`; exportación a JSON |

## Requisitos de instalación

- Python 3.10 o superior (sin dependencias externas).
- Un navegador para el visor.

## Uso rápido

```bash
git clone <url-del-repositorio>
cd so-interrupt-sim
python -m simulador escenarios/e1_tres_procesos_rr4.json
```

En Windows se puede usar `py` en lugar de `python`.

| Comando | Qué hace |
|---|---|
| `python -m simulador ESCENARIO --modo paso` | Un paso por cada Enter (modo principal para la demostración) |
| `python -m simulador ESCENARIO --modo tick` | Un tick por cada Enter |
| `python -m simulador ESCENARIO --modo auto --velocidad 5` | Todo seguido, 5 pasos por segundo |
| `python -m simulador ESCENARIO --modo resumen` | Solo el resumen final (contadores y métricas) |
| `python -m simulador ESCENARIO --visor --abrir` | Prepara la traza y abre el visor en el navegador |
| `python -m simulador ESCENARIO --traza trazas/e1.json` | Guarda la bitácora en JSON |

Opciones para cambiar la configuración sin editar el JSON: `--planificador RR|FCFS`, `--quantum N`, `--marcos N`, `--reemplazo LRU|FIFO`, `--periodo-timer N`.

Órdenes en el modo paso a paso: `Enter` siguiente paso · `t` resto del tick · `c` contadores · `q` colas · `m` memoria · `g N` ir al paso N · `a` automático · `x` salir.

## Formato del escenario

```json
{
  "nombre": "E1 - tres procesos, Round Robin q=4, 3 marcos, LRU",
  "config": { "planificador": "RR", "quantum": 4, "marcos": 3, "reemplazo": "LRU",
              "periodo_timer": 1, "latencia_read": 4, "latencia_fallo": 3 },
  "procesos": [
    { "pid": "P2", "llegada": 0, "guion": ["cpu:0", "read:0", "cpu:0", "exit:0"] }
  ],
  "eventos_externos": [ { "tick": 12, "tipo": "NMI" } ]
}
```

| Instrucción | Significado | Interrupción que produce |
|---|---|---|
| `cpu:p` | Cómputo que usa la página *p* | Ninguna, o fallo de página si *p* no está en memoria |
| `read:p` | Lectura bloqueante de disco | `INT 0x80` (read) |
| `syscall:p:getpid` | Llamada que no bloquea | `INT 0x80` |
| `div0:p` | División por cero | Excepción vector 0 |
| `exit:p` | Fin del proceso | `INT 0x80` (exit) |

## Escenarios incluidos

| Archivo | Qué muestra |
|---|---|
| `e1_tres_procesos_rr4.json` | El ejemplo completo del informe: las 6 transiciones, fallo de página con LRU, NMI anidada (23 ticks, 83 pasos, 35 interrupciones) |
| `s1_dos_cpu_bound.json` | Cambio de contexto con Round Robin |
| `s3b_cadena_clasica.json` | Cadena clásica de reemplazo; con `--reemplazo FIFO --marcos 4` aparece la anomalía de Belady |
| `s6_diez_procesos_100.json` | FCFS (retorno 550) frente a RR con `--planificador RR --quantum 1` (retorno 995,5) |
| `s8_hiperpaginacion.json` | Hiperpaginación: compare `--marcos 3` y `--marcos 6` |

## Pruebas

```bash
python -m unittest discover -s pruebas -t pruebas
```

La prueba dorada (`pruebas/test_traza_dorada.py`) comprueba que el motor reproduce **paso por paso** la traza del ejemplo E1 generada por la herramienta de referencia del informe (`docs/herramientas/`).

## Estructura

```text
simulador/          motor (Python)
  nucleo.py           ciclo principal por tick
  controlador_int.py  IRR, IMR, IF, prioridades, anidamiento; único punto de conteo
  ivt.py · isr.py     tabla de vectores y rutinas de servicio
  cpu.py · disco.py   hardware simulado
  procesos.py         máquina de estados (T1–T6) y colas
  planificacion/      Round Robin, FCFS y despachador
  memoria/            tabla de páginas, marcos, LRU y FIFO
  contadores.py       contador de interrupciones e invariantes
  bitacora.py         bitácora transaccional y exportación JSON
  consola.py · cli.py interfaz de texto
visor/              visor web (solo lee la traza)
escenarios/         entradas JSON
pruebas/            pruebas automáticas
docs/               documentación y herramientas del informe
```

## Estado

Cimientos funcionales: fases F1 a F5 del informe con Round Robin, FCFS, LRU y FIFO. Pendiente (F6): SJF, prioridades con *aging* y reemplazo Óptimo. Ver [CONTRIBUTING.md](CONTRIBUTING.md) para trabajar en el repositorio.

## Integrantes

Alcantara Miranda, Sergio Daniel · Ancajima Cruz, Fabrizzio Alessandro · Ayala Zubilete, Matthews Ronald · Chávez Yauri, Yenny Esther · Flores Sánchez, Héctor David · Huamán Choque, Jairo Jhosimar
