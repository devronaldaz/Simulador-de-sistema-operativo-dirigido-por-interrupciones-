"""API del servidor local del visor: opciones, escenarios y simulación."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer

from simulador import servidor


class TestServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(servidor.Manejador, directory=str(servidor.VISOR)))
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _post(self, cuerpo):
        req = urllib.request.Request(f"{self.url}/api/simular", data=json.dumps(cuerpo).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_opciones_listan_los_algoritmos(self):
        with urllib.request.urlopen(f"{self.url}/api/opciones") as r:
            datos = json.load(r)
        self.assertEqual(set(datos["planificadores"]), {"FCFS", "SJF", "RR", "PRIORIDAD"})
        self.assertEqual(set(datos["reemplazo"]), {"FIFO", "LRU", "OPTIMO", "CLOCK"})
        self.assertIn("mejor", datos["ajuste"])

    def test_escenarios_de_ejemplo(self):
        with urllib.request.urlopen(f"{self.url}/api/escenarios") as r:
            lista = json.load(r)
        self.assertTrue(any(e["archivo"].startswith("e1") for e in lista))

    def test_simular_devuelve_la_traza_con_el_algoritmo_elegido(self):
        e1 = next(e for e in servidor.escenarios() if e["archivo"].startswith("e1"))["datos"]
        e1["config"].update(planificador="FCFS", reemplazo="FIFO")
        codigo, traza = self._post(e1)
        self.assertEqual(codigo, 200)
        self.assertEqual(traza["planificador"], "FCFS")
        self.assertEqual(traza["config"]["reemplazo"], "FIFO")
        self.assertGreater(len(traza["pasos"]), 0)

    def test_escenario_invalido_responde_400(self):
        codigo, cuerpo = self._post({"config": {}, "procesos": [{"pid": "P1", "guion": ["cpu:0"]}]})
        self.assertEqual(codigo, 400)
        self.assertIn("exit", cuerpo["error"])

    def test_detecta_el_puerto_ocupado(self):
        puerto = self.srv.server_address[1]
        self.assertTrue(servidor.puerto_ocupado(puerto))
        self.assertEqual(servidor.main(["--puerto", str(puerto)]), 1)

    def test_sirve_el_visor(self):
        with urllib.request.urlopen(f"{self.url}/") as r:
            self.assertIn("pantalla-inicio", r.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
