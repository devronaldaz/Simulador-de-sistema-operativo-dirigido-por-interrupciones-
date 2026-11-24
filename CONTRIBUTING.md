# Cómo contribuir

## Flujo de trabajo

1. Toma una tarea de Notion y su issue en GitHub (título: `ID nombre`, p. ej. `P17 planificacion: SJF`).
2. Crea una rama desde `main`: `feat/<modulo>-<descripcion>` (también `fix/…`, `docs/…`, `test/…`).
3. Haz commits pequeños con prefijo: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.
4. Abre un pull request con `Closes #n`; lo revisa la persona que te toca en el anillo:
   Ronald → Jairo → Héctor → Yenny → Fabrizzio → Sergio → Ronald.
5. Solo se fusiona con la aprobación del revisor y las pruebas en verde.

## Reglas del diseño (no romperlas)

- **Todo entra por el controlador de interrupciones** (`controlador_int.py`); es el único lugar donde se cuenta una interrupción.
- **Solo `procesos.py` cambia `pcb.estado`**, y siempre con una transición T1–T6 que deja su porqué en la bitácora.
- Las ISR (`isr.py`) registran la aceptación y **delegan**: la política vive en `planificacion/` y `memoria/`.
- El visor solo **lee** la traza; nunca simula.
- Sin aleatoriedad: la simulación debe ser reproducible.

## Estilo

- Python 3.10+, PEP 8, anotaciones de tipo en funciones públicas.
- Docstring corto en cada módulo y en cada ISR.
- Nombres en español, en minúsculas con guion bajo.

## Antes de abrir el PR

```bash
python -m unittest discover -s pruebas -t pruebas
python -m simulador escenarios/e1_tres_procesos_rr4.json --modo resumen
```

La prueba dorada debe seguir en verde. Si un cambio altera **a propósito** la traza de E1, regenera la traza esperada con `node docs/herramientas/exportar_dorada.js` solo después de actualizar la herramienta de referencia, y explícalo en el PR.

## Agregar algo nuevo (un solo lugar de registro)

- **Algoritmo de planificación:** una entrada en `ALGORITMOS` de `simulador/planificacion/base.py` (criterio, quantum, expropiativo). Config, CLI y visor lo leen de ahí.
- **Política de reemplazo:** una función en `simulador/memoria/reemplazo.py`, registrada en `POLITICAS` y `CRITERIOS`.
- **Estado o transición:** el valor en `Estado` y la fila en `TRANSICIONES` (`simulador/modelos.py`); para dibujarlo, una posición en `POS` de `visor/visor.js`.
- **Tipo de interrupción:** el valor en `TipoInt`, la entrada en `ivt.ENTRADAS` y su ISR en `isr.py`.

Detalles y ejemplos en [docs/MANUAL_DE_USO.md](docs/MANUAL_DE_USO.md), sección 6.
