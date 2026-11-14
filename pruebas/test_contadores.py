"""Contador de interrupciones (R4) e interrupción de timer (escenarios S9 y S10)."""
import unittest

from utilidades import correr


class ContadoresE1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim, cls.res = correr("e1_tres_procesos_rr4.json")

    def test_por_tipo(self):
        self.assertEqual(self.res["por_tipo"], {"TIMER": 23, "ES_DMA": 2, "SYSCALL": 7,
                                                "FALLO_PAG": 1, "EXCEPCION": 1, "NMI": 1})
        self.assertEqual(self.res["interrupciones"], 35)

    def test_por_proceso(self):
        totales = {pid: sum(c.values()) for pid, c in self.res["por_proceso"].items()}
        self.assertEqual(totales, {"P1": 13, "P2": 8, "P3": 9, "SISTEMA": 5})

    def test_invariantes(self):
        self.assertEqual(self.res["invariantes"], ["OK"])

    def test_resultados_de_la_isr_del_timer(self):
        self.assertEqual(self.res["timer_resultados"], {"A": 15, "B": 2, "C": 1, "D": 5})


class PeriodoDelTimer(unittest.TestCase):
    """S10: IRQ0 = ⌊ticks/P⌋ y los resultados A–D suman las IRQ0 (tabla 8.3-B del informe)."""

    def comprobar(self, periodo, timers, total, cambios, expropiaciones, resultados):
        _, r = correr("e1_tres_procesos_rr4.json", periodo_timer=periodo)
        self.assertEqual(r["por_tipo"]["TIMER"], timers)
        self.assertEqual(r["interrupciones"], total)
        self.assertEqual(r["cambios_contexto"], cambios)
        self.assertEqual(r["expropiaciones"], expropiaciones)
        self.assertEqual(r["timer_resultados"], resultados)
        self.assertEqual(r["invariantes"], ["OK"])

    def test_periodo_1(self):
        self.comprobar(1, 23, 35, 7, 2, {"A": 15, "B": 2, "C": 1, "D": 5})

    def test_periodo_2(self):
        self.comprobar(2, 11, 23, 9, 4, {"A": 6, "B": 4, "C": 0, "D": 1})

    def test_periodo_4(self):
        self.comprobar(4, 5, 17, 8, 3, {"A": 0, "B": 3, "C": 1, "D": 1})


if __name__ == "__main__":
    unittest.main()
