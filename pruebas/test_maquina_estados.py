"""Máquina de estados (R2/R3), validación del escenario y bitácora (R6)."""
import unittest

from simulador import ErrorEscenario, Simulador, desde_dict
from simulador.modelos import Estado
from simulador.procesos import TransicionInvalida
from utilidades import correr

MINIMO = {"procesos": [{"pid": "P1", "llegada": 0, "guion": ["cpu:0", "exit:0"]}]}


class MaquinaDeEstados(unittest.TestCase):
    def test_las_seis_transiciones_aparecen_en_e1(self):
        sim, _ = correr("e1_tres_procesos_rr4.json")
        vistas = {}
        for p in sim.bitacora.pasos:
            if p.transicion:
                vistas[p.transicion["id"]] = vistas.get(p.transicion["id"], 0) + 1
        self.assertEqual(vistas, {"T1": 3, "T2": 7, "T3": 2, "T4": 2, "T5": 2, "T6": 3})

    def test_toda_transicion_tiene_porque(self):
        sim, _ = correr("e1_tres_procesos_rr4.json")
        for p in sim.bitacora.pasos:
            self.assertTrue(p.causa.strip(), f"paso {p.paso} sin causa")
            self.assertTrue(p.antes and p.despues, f"paso {p.paso} sin antes/después")

    def test_transicion_fuera_del_mapa_aborta(self):
        sim = Simulador(desde_dict(MINIMO))
        p = sim.procesos.pcbs[0]          # sigue en NUEVO
        with self.assertRaises(TransicionInvalida):
            sim.procesos.poner_en_cpu(p, "[]", "NUEVO → EJECUTANDO no existe en el mapa")

    def test_zombie_pasa_por_t7_y_t8(self):
        sim, _ = correr("p7_zombie_kill.json")
        ids = [p.transicion["id"] for p in sim.bitacora.pasos if p.transicion]
        self.assertEqual(ids.count("T7"), 3)
        self.assertEqual(ids.count("T8"), 3)
        self.assertNotIn("T6", ids)

    def test_el_escenario_original_no_se_modifica(self):
        esc = desde_dict(MINIMO)
        Simulador(esc).ejecutar()
        self.assertEqual(esc.procesos[0].estado, Estado.NUEVO)


class ValidacionDelEscenario(unittest.TestCase):
    def test_instruccion_invalida(self):
        with self.assertRaises(ErrorEscenario):
            desde_dict({"procesos": [{"pid": "P1", "guion": ["saltar:0", "exit:0"]}]})

    def test_guion_sin_exit(self):
        with self.assertRaises(ErrorEscenario):
            desde_dict({"procesos": [{"pid": "P1", "guion": ["cpu:0"]}]})

    def test_pid_repetido(self):
        p = {"pid": "P1", "guion": ["exit:0"]}
        with self.assertRaises(ErrorEscenario):
            desde_dict({"procesos": [p, p]})

    def test_planificador_desconocido(self):
        with self.assertRaises(ErrorEscenario):
            desde_dict({**MINIMO, "config": {"planificador": "XYZ"}})


if __name__ == "__main__":
    unittest.main()
