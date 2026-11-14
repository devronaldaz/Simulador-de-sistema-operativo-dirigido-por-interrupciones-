"""Escenarios de prueba del capítulo 8 del informe (S1, S3b, S6, S7, S8) y métricas de E1."""
import json
import unittest

from utilidades import correr


def por_pid(res):
    return {m["pid"]: m for m in res["metricas"]}


class MetricasE1(unittest.TestCase):
    def test_metricas(self):
        _, r = correr("e1_tres_procesos_rr4.json")
        m = por_pid(r)
        self.assertEqual([m[p]["retorno"] for p in ("P1", "P2", "P3")], [23, 17, 11])
        self.assertEqual([m[p]["espera"] for p in ("P1", "P2", "P3")], [9, 7, 5])
        self.assertEqual(r["promedios"], {"espera": 7.0, "retorno": 17.0, "respuesta": 2.67})
        self.assertEqual((r["cambios_contexto"], r["expropiaciones"], r["fallos_pagina"], r["reemplazos"]), (7, 2, 1, 1))
        self.assertEqual(r["uso_cpu"], 95.7)


class EscenariosDePrueba(unittest.TestCase):
    def test_s1_cambio_de_contexto(self):
        _, r = correr("s1_dos_cpu_bound.json")
        m = por_pid(r)
        self.assertEqual((m["A"]["retorno"], m["B"]["retorno"]), (12, 16))
        self.assertEqual((m["A"]["espera"], m["B"]["espera"]), (4, 8))
        self.assertEqual((r["cambios_contexto"], r["expropiaciones"]), (4, 2))

    def test_s3b_cadena_clasica_y_anomalia_de_belady(self):
        fallos = {}
        for politica in ("FIFO", "LRU"):
            for marcos in (3, 4):
                _, r = correr("s3b_cadena_clasica.json", reemplazo=politica, marcos=marcos)
                fallos[(politica, marcos)] = r["fallos_pagina"]
        self.assertEqual(fallos, {("FIFO", 3): 9, ("FIFO", 4): 10, ("LRU", 3): 10, ("LRU", 4): 8})

    def test_s6_fcfs_frente_a_round_robin(self):
        """Ejemplo de la Sesión 6 – Planificación, diap. 25."""
        _, fcfs = correr("s6_diez_procesos_100.json", planificador="FCFS")
        _, rr = correr("s6_diez_procesos_100.json", planificador="RR", quantum=1)
        self.assertEqual(fcfs["promedios"]["retorno"], 550.0)
        self.assertEqual(rr["promedios"]["retorno"], 995.5)

    def test_s7_determinismo(self):
        s1, r1 = correr("e1_tres_procesos_rr4.json")
        s2, r2 = correr("e1_tres_procesos_rr4.json")
        self.assertEqual(json.dumps(s1.bitacora.como_dict(r1)), json.dumps(s2.bitacora.como_dict(r2)))

    def test_s8_hiperpaginacion(self):
        _, pocos = correr("s8_hiperpaginacion.json", marcos=3)
        _, muchos = correr("s8_hiperpaginacion.json", marcos=6)
        self.assertEqual((pocos["ticks"], pocos["fallos_pagina"], pocos["reemplazos"], pocos["uso_cpu"]), (63, 32, 31, 42.9))
        self.assertEqual((muchos["ticks"], muchos["fallos_pagina"], muchos["reemplazos"], muchos["uso_cpu"]), (30, 3, 0, 90.0))


if __name__ == "__main__":
    unittest.main()
