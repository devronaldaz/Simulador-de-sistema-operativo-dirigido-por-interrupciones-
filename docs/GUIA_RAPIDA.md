# Guía rápida de ejecución

Para prender el simulador en 5 minutos. El detalle de cada opción está en el [manual de uso](MANUAL_DE_USO.md).

## 1. Qué necesita

| Requisito | Cómo comprobarlo | Si falta |
|---|---|---|
| Python 3.10 o superior | `py --version` (Windows) · `python3 --version` (Linux/macOS) | Instalarlo desde python.org; en Windows marcar **Add python.exe to PATH** |
| El repositorio | — | `git clone …` (paso 2) o *Code → Download ZIP* en GitHub y descomprimir |
| Un navegador | — | Chrome, Edge o Firefox |

No hay que instalar nada más: el simulador no tiene dependencias.

## 2. Prenderlo (Windows, PowerShell)

**Paso 1. Descargar el proyecto** (solo la primera vez):

```powershell
git clone https://github.com/devronaldaz/Simulador-de-sistema-operativo-dirigido-por-interrupciones-.git
```

**Paso 2. Entrar a la carpeta del proyecto.** Todos los comandos se ejecutan **desde aquí**; es el error más común (ver sección 6):

```powershell
cd Simulador-de-sistema-operativo-dirigido-por-interrupciones-
```

**Paso 3. Iniciar el visor:**

```powershell
py -m simulador.servidor --abrir
```

La terminal muestra `Visor en http://localhost:8766  (Ctrl+C para detener)` y se abre el navegador. Si no se abre solo, entre a **http://localhost:8766**.

**Paso 4. Detenerlo:** en esa terminal, **Ctrl + C**. Mientras el visor esté abierto, deje la terminal abierta.

> En Linux y macOS use `python3` en lugar de `py`.

## 3. Usar el visor

**Pantalla 1 · Configuración**

1. **Procesos a simular:** elija un escenario de ejemplo. Sus procesos aparecen en la tabla y se pueden editar; *+ Añadir proceso* agrega filas y la ✕ quita una.
2. **Gestión de procesos:** elija FCFS, SJF, Round Robin o Prioridades, y ajuste quantum, expropiación, prioridad y aging.
3. **Gestión de memoria:** paginación (reemplazo FIFO, LRU, Óptimo o Clock) o contigua (primer, mejor, peor o siguiente ajuste).
4. Pulse **Iniciar simulación** en la barra de abajo, que resume lo elegido.

**Pantalla 2 · Simulación**

Arriba quedan siempre los algoritmos en uso, los controles y el paso actual con su porqué. Abajo, las pestañas *Procesos*, *Línea de tiempo*, *PCB*, *Memoria*, *Interrupciones y métricas* y *Bitácora*.

| Acción | Botón | Teclado |
|---|---|---|
| Paso siguiente / anterior | ▷ / ◁ | → / ← |
| Primer / último paso | ⏮ / ⏭ | Inicio / Fin |
| Reproducir / pausar | **Reproducir** | Espacio |
| Velocidad | lista *Velocidad* (0,5× a 20×) | — |
| Ir a un paso | barra de posición, o clic en una fila de la bitácora o en una columna de la línea de tiempo | — |
| Cambiar de pestaña | clic en la pestaña | con el foco en una pestaña: → / ←, Inicio, Fin |
| Volver a elegir algoritmos | **Cambiar algoritmos** | botón Atrás del navegador |
| Tema claro / oscuro | botón ☀ / ☾ de la cabecera | — |

El tema oscuro es el predeterminado; para el **proyector** conviene el claro. Se recuerda en cada navegador.

## 4. Otras formas de ejecutarlo

| Para… | Comando |
|---|---|
| Ver paso a paso en la consola (Enter avanza) | `py -m simulador escenarios/e1_tres_procesos_rr4.json` |
| Solo el resumen final (contadores, memoria, métricas) | `py -m simulador escenarios/e1_tres_procesos_rr4.json --modo resumen` |
| Cambiar un algoritmo sin editar el JSON | `py -m simulador escenarios/p2_sjf_diapositiva.json --planificador SJF --expropiativo si` |
| Abrir el visor **sin servidor** con un escenario | `py -m simulador escenarios/e1_tres_procesos_rr4.json --visor --abrir` |
| Guardar la traza en un archivo | `py -m simulador escenarios/e1_tres_procesos_rr4.json --modo resumen --traza trazas/e1.json` |
| Usar otro puerto | `py -m simulador.servidor --puerto 8767` |

Sin servidor, el visor muestra la simulación de ese escenario, pero la pantalla de configuración no puede simular otros algoritmos.

## 5. Antes de exponer

- [ ] `py -m unittest discover -s pruebas` termina en **OK**.
- [ ] `py -m simulador.servidor --abrir` muestra la pantalla de configuración con los escenarios cargados.
- [ ] Iniciar una simulación y reproducirla de principio a fin.
- [ ] Poner el **tema claro** si se usa proyector.
- [ ] Sin internet, las fuentes cambian a las del sistema; el visor funciona igual.
- [ ] Tener a mano la tabla de cambios en vivo del [manual](MANUAL_DE_USO.md#6-cambios-en-vivo-lo-que-puede-pedir-el-profesor).

## 6. Errores comunes

| Lo que aparece | Por qué | Solución |
|---|---|---|
| `No module named simulador` (o `No module named 'simulador'`) | El comando se ejecutó fuera de la carpeta del proyecto | Entrar a la carpeta del proyecto (paso 2) y repetir |
| `El término 'py' no se reconoce como nombre de un cmdlet…` | Python no está instalado o no está en el PATH | Instalar Python marcando *Add python.exe to PATH*, o probar con `python` |
| `El puerto 8766 ya está en uso (¿quedó abierto otro servidor?)` | Sigue abierto un servidor anterior (de esta u otra terminal) | Cerrarlo con **Ctrl + C** en su terminal, o usar `--puerto 8767` |
| El navegador muestra **404 / File not found** | Se usó `py -m http.server` desde otra carpeta, o hay un servidor viejo en ese puerto | Cerrar ese servidor y usar `py -m simulador.servidor` desde la carpeta del proyecto |
| El visor dice **Modo sin servidor** | Se abrió `index.html` directamente o con `http.server` | Usar `py -m simulador.servidor` para elegir algoritmos y simular |
| El visor dice **No hay traza cargada** | Se abrió sin servidor y sin haber generado una traza | Usar el servidor, o generar una con `--visor` (sección 4) |
| `No se pudo simular: el guion de P1 debe terminar en exit o div0` | Un guion de la tabla no termina en `exit` o `div0` | Agregar `exit:0` al final del guion, o vaciarlo para que se genere con el burst-time |
| `No se pudo simular: PID repetido: P1` | Dos filas tienen el mismo PID | Cambiar uno de los PID |
| `No se pudo simular: el escenario no tiene procesos` | Se quitaron todas las filas | Añadir al menos un proceso |
| Después de actualizar el código se ve la versión anterior | El navegador guardó la página en caché | Recargar con **Ctrl + F5** |
| `--visor` no se refleja en el navegador | El visor ya estaba abierto | Recargar la página |
