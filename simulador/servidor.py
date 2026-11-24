"""Servidor local del visor: python -m simulador.servidor [--puerto 8766]

Sirve la carpeta visor/ y una API mínima para que la pantalla de inicio elija
los algoritmos y ejecute la simulación sin pasar por la consola:

  GET  /api/opciones    algoritmos de procesos y de memoria, con su descripción
  GET  /api/escenarios  escenarios de ejemplo (escenarios/*.json)
  POST /api/simular     recibe un escenario en JSON y devuelve la traza completa

Solo escucha en 127.0.0.1 y no usa dependencias externas.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import webbrowser
from dataclasses import asdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import OPCIONES, Config, ErrorEscenario, desde_dict
from .memoria.reemplazo import CRITERIOS
from .metricas import resumen
from .nucleo import Simulador
from .planificacion import ALGORITMOS

RAIZ = Path(__file__).resolve().parent.parent
VISOR = RAIZ / "visor"
ESCENARIOS = RAIZ / "escenarios"
MAX_CUERPO = 512 * 1024

AJUSTES = {
    "primer": "el primer hueco donde cabe",
    "mejor": "el hueco más pequeño donde cabe",
    "peor": "el hueco más grande",
    "siguiente": "como primer ajuste, pero sigue desde el último hueco usado",
}


def opciones() -> dict[str, Any]:
    return {
        "planificadores": {k: v["descripcion"] for k, v in ALGORITMOS.items()},
        "reemplazo": dict(CRITERIOS),
        "ajuste": AJUSTES,
        "valores": {k: sorted(v) for k, v in OPCIONES.items()},
        "por_defecto": asdict(Config()),
    }


def escenarios() -> list[dict[str, Any]]:
    lista = []
    for ruta in sorted(ESCENARIOS.glob("*.json")):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        lista.append({"archivo": ruta.name, "nombre": datos.get("nombre", ruta.stem), "datos": datos})
    return lista


def simular(datos: dict[str, Any]) -> dict[str, Any]:
    """Valida el escenario, lo ejecuta y devuelve la traza que lee el visor."""
    sim = Simulador(desde_dict(datos)).ejecutar()
    return sim.bitacora.como_dict(resumen(sim))


class Manejador(SimpleHTTPRequestHandler):
    def _json(self, codigo: int, cuerpo: Any) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por http.server)
        if self.path == "/api/opciones":
            return self._json(200, opciones())
        if self.path == "/api/escenarios":
            return self._json(200, escenarios())
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/simular":
            return self._json(404, {"error": "ruta desconocida"})
        largo = int(self.headers.get("Content-Length") or 0)
        if not 0 < largo <= MAX_CUERPO:
            return self._json(413, {"error": "cuerpo vacío o demasiado grande"})
        try:
            datos = json.loads(self.rfile.read(largo).decode("utf-8"))
            if not isinstance(datos, dict):
                raise ErrorEscenario("se esperaba un objeto JSON con el escenario")
            return self._json(200, simular(datos))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json(400, {"error": "JSON inválido"})
        except (ErrorEscenario, TypeError, ValueError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception as exc:  # la simulación falló: se informa en la pantalla de inicio
            return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def end_headers(self) -> None:
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, formato: str, *args: Any) -> None:
        if "/api/" in str(args[0] if args else ""):
            super().log_message(formato, *args)


class Servidor(ThreadingHTTPServer):
    # En Windows, SO_REUSEADDR deja que dos servidores escuchen el mismo puerto sin error
    # y el navegador termina en el equivocado; sin él, el segundo falla al iniciar.
    allow_reuse_address = False


def puerto_ocupado(puerto: int) -> bool:
    """¿Ya responde algo en localhost:puerto (IPv4 o IPv6)? p. ej. un http.server olvidado."""
    for familia, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(familia, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex((host, puerto)) == 0:
                    return True
        except OSError:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m simulador.servidor", description=__doc__.splitlines()[0])
    ap.add_argument("--puerto", type=int, default=8766)
    ap.add_argument("--abrir", action="store_true", help="abre el visor en el navegador")
    args = ap.parse_args(argv)
    aviso = (f"El puerto {args.puerto} ya está en uso (¿quedó abierto otro servidor?). Ciérrelo con Ctrl+C "
             f"en su terminal o use otro puerto: python -m simulador.servidor --puerto {args.puerto + 1}")
    if puerto_ocupado(args.puerto):
        print(aviso, file=sys.stderr)
        return 1
    try:
        servidor = Servidor(("127.0.0.1", args.puerto), partial(Manejador, directory=str(VISOR)))
    except OSError:
        print(aviso, file=sys.stderr)
        return 1
    url = f"http://localhost:{args.puerto}"
    print(f"Visor en {url}  (Ctrl+C para detener)")
    if args.abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
