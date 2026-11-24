"""Prueba dorada (fase F4): el motor reproduce paso a paso la traza del ejemplo E1 del informe.

La traza esperada la genera la herramienta de referencia del informe:
    node docs/herramientas/exportar_dorada.js
Los pasos PLAN (elección del planificador, separada del despachador) son
posteriores a esa herramienta: se excluyen al comparar y se prueban aparte.
"""
import json
import unittest

from utilidades import DATOS, correr


class TrazaDoradaE1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim, cls.res = correr("e1_tres_procesos_rr4.json")
        cls.pasos = [p for p in cls.sim.bitacora.pasos if p.tipo_paso.value != "PLAN"]
        cls.esperada = json.loads((DATOS / "e1_esperada.json").read_text(encoding="utf-8"))["pasos"]

    def test_mismo_numero_de_pasos(self):
        self.assertEqual(len(self.pasos), len(self.esperada))
        self.assertEqual(len(self.esperada), 83)

    def test_un_paso_plan_antes_de_cada_despacho(self):
        todos = self.sim.bitacora.pasos
        despachos = [k for k, p in enumerate(todos) if p.transicion and p.transicion["id"] == "T2"]
        self.assertEqual(len(despachos), 7)
        for k in despachos:
            self.assertEqual(todos[k - 1].tipo_paso.value, "PLAN")

    def test_cada_paso_coincide(self):
        for obtenido, esperado in zip(self.pasos, self.esperada):
            with self.subTest(paso=obtenido.paso):
                self.assertEqual(obtenido.tick, esperado["tick"])
                self.assertEqual(obtenido.tipo_paso.value, esperado["tipo_paso"])
                self.assertEqual(obtenido.contadores["total"], esperado["total"])
                tr = obtenido.transicion
                tr = tr and {k: tr[k] for k in ("pid", "de", "a")}
                self.assertEqual(tr, esperado["transicion"])

    def test_tipo_de_cada_interrupcion(self):
        int_obtenidas = [p for p in self.pasos if p.tipo_paso.value == "INT"]
        int_esperadas = [p for p in self.esperada if p["tipo_paso"] == "INT"]
        previo = {"TIMER": 0, "ES_DMA": 0, "SYSCALL": 0, "FALLO_PAG": 0, "EXCEPCION": 0, "NMI": 0}
        for obtenido, esperado in zip(int_obtenidas, int_esperadas):
            cambiado = [t for t in previo if obtenido.contadores[t] != previo[t]]
            self.assertEqual(cambiado, [esperado["int_tipo"]], f"paso {obtenido.paso}")
            previo = {t: obtenido.contadores[t] for t in previo}


if __name__ == "__main__":
    unittest.main()
