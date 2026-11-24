"""Gestión de procesos: ejemplos de las diapositivas y pedidos del docente (plan v2, sección 6.1)."""
import unittest

from simulador.modelos import Estado
from utilidades import correr


def por_pid(res):
    return {m["pid"]: m for m in res["metricas"]}


def orden_de_despacho(sim):
    return [p.transicion["pid"] for p in sim.bitacora.pasos if p.transicion and p.transicion["id"] == "T2"]


class EjemplosDeLaDiapositiva(unittest.TestCase):
    """Sesión 6/7 – Planificación: resultados conocidos."""

    def test_fcfs_24_3_3(self):
        sim, r = correr("p1_fcfs_diapositiva.json")
        self.assertEqual([por_pid(r)[p]["espera"] for p in ("P1", "P2", "P3")], [0, 24, 27])
        self.assertEqual(r["promedios"]["espera"], 17.0)

    def test_sjf_no_expropiativo(self):
        sim, r = correr("p2_sjf_diapositiva.json")
        self.assertEqual([por_pid(r)[p]["espera"] for p in ("P1", "P2", "P3", "P4")], [0, 6, 3, 7])
        self.assertEqual(r["promedios"]["espera"], 4.0)
        self.assertEqual(orden_de_despacho(sim), ["P1", "P3", "P2", "P4"])

    def test_sjf_expropiativo(self):
        sim, r = correr("p2_sjf_diapositiva.json", expropiativo=True)
        self.assertEqual([por_pid(r)[p]["espera"] for p in ("P1", "P2", "P3", "P4")], [9, 1, 0, 2])
        self.assertEqual(r["promedios"]["espera"], 3.0)
        # Gantt de la diapositiva: P1 0–2, P2 2–4, P3 4–5, P2 5–7, P4 7–11, P1 11–16
        self.assertEqual(orden_de_despacho(sim), ["P1", "P2", "P3", "P2", "P4", "P1"])
        self.assertEqual(r["expropiaciones_por_llegada"], 2)


class PrioridadesYAging(unittest.TestCase):
    def test_rr_con_prioridades(self):
        sim, r = correr("p4_rr_prioridades.json")
        fin = {m["pid"]: m["fin"] for m in r["metricas"]}
        # Primero los de prioridad 1 (P2 y P4, alternando por quantum), luego P3 (2) y al final P1 (3).
        self.assertLess(max(fin["P2"], fin["P4"]), fin["P3"])
        self.assertLess(fin["P3"], fin["P1"])
        self.assertEqual(orden_de_despacho(sim)[:2], ["P2", "P4"])

    def test_prioridad_inversa_al_uso_de_cpu(self):
        """El error que advirtió el docente: un CPU-bound con prioridad alta castiga al I/O-bound."""
        _, fija = correr("p3_prioridad_inversa_cpu.json", prioridad="fija")
        _, dinamica = correr("p3_prioridad_inversa_cpu.json", prioridad="dinamica")
        self.assertEqual(por_pid(fija)["IO"]["espera"], 20)
        self.assertLess(por_pid(dinamica)["IO"]["espera"], por_pid(fija)["IO"]["espera"])
        self.assertLess(por_pid(dinamica)["IO"]["retorno"], por_pid(fija)["IO"]["retorno"])
        self.assertGreater(por_pid(dinamica)["CPU"]["prioridad_final"], 1)   # el CPU-bound bajó su prioridad

    def test_aging_evita_la_inanicion(self):
        _, sin = correr("p5_inanicion_aging.json", aging=0)
        _, con = correr("p5_inanicion_aging.json", aging=4)
        self.assertEqual(por_pid(sin)["B"]["primer_despacho"], 24)
        self.assertEqual(por_pid(con)["B"]["primer_despacho"], 16)     # cálculo a mano del plan v2


class WorstTimeZombieKillLargoPlazo(unittest.TestCase):
    def test_worst_time_rechazar(self):
        sim, r = correr("p6_worst_time.json")
        self.assertTrue(por_pid(r)["P2"]["rechazado"])
        self.assertEqual(r["rechazados"], 1)
        p2 = sim.procesos.pcb("P2")
        self.assertEqual((p2.estado, p2.instrucciones_completadas), (Estado.TERMINADO, 0))

    def test_worst_time_truncar(self):
        sim, r = correr("p6_worst_time.json", worst_time_modo="truncar")
        self.assertEqual(r["por_tipo"]["WORST_TIME"], 1)
        self.assertEqual(sim.procesos.pcb("P2").cpu_usado, 50)

    def test_zombie_retiene_memoria(self):
        sim, _ = correr("p7_zombie_kill.json")
        zombies = [p for p in sim.bitacora.pasos if p.vista["estados"].get("P1") == "ZOMBIE"]
        self.assertTrue(zombies)
        for paso in zombies:                     # mientras es zombie, su marco sigue ocupado
            self.assertIn("P1", [f["proceso"] for f in paso.vista["mapa"]])
        self.assertNotIn("P1", [f["proceso"] for f in sim.bitacora.pasos[-1].vista["mapa"]])

    def test_kill_pendiente_y_entrega(self):
        sim, r = correr("p7_zombie_kill.json")
        self.assertEqual(r["por_proceso"]["P3"]["SENAL"], 2)       # envío (P3 en LISTO) y entrega
        self.assertEqual(sim.procesos.pcb("P3").instrucciones_completadas < 6, True)

    def test_grado_de_multiprogramacion(self):
        sim, r = correr("p8_largo_plazo.json")
        for paso in sim.bitacora.pasos:
            activos = [e for e in paso.vista["estados"].values() if e in ("LISTO", "EJECUTANDO", "BLOQUEADO", "ZOMBIE")]
            self.assertLessEqual(len(activos), 2)
        self.assertEqual([por_pid(r)[p]["respuesta"] for p in ("P3", "P4")], [6, 8])


if __name__ == "__main__":
    unittest.main()
