"""Gestión de memoria: MMU, reemplazo, TLB y memoria contigua (plan v2, secciones 6.2, 6.3 y 7)."""
import unittest

from simulador.memoria.contigua import ErrorProteccion, ajustar, traducir_base_limite
from simulador.memoria.gestor import conjunto_de_trabajo, eat_fallos, eat_tlb, traducir_paginada
from utilidades import correr


class FormulasDeLaSemana14(unittest.TestCase):
    def test_traduccion_paginada(self):
        self.assertEqual(traducir_paginada(13322, 4096, 9), (3, 1034, 37898))
        self.assertEqual(traducir_paginada(21005, 4096, 12), (5, 525, 49677))
        self.assertEqual(divmod(9000, 4096), (2, 808))

    def test_base_y_limite(self):
        self.assertEqual(traducir_base_limite(4000, 1000, 120), 4120)
        self.assertEqual(traducir_base_limite(4000, 1000, 999), 4999)
        self.assertEqual(traducir_base_limite(5000, 800, 799), 5799)
        self.assertEqual(traducir_base_limite(9000, 800, 120), 9120)
        for base, limite, d in ((4000, 1000, 1000), (5000, 800, 800), (9000, 800, 800)):
            with self.assertRaises(ErrorProteccion):
                traducir_base_limite(base, limite, d)

    def test_politicas_de_ajuste(self):
        huecos = [100, 500, 200, 300]
        self.assertEqual(ajustar(huecos, 212, "primer"), 1)    # H2, sobran 288
        self.assertEqual(ajustar(huecos, 212, "mejor"), 3)     # H4, sobran 88
        self.assertEqual(ajustar(huecos, 212, "peor"), 1)      # H2, sobran 288
        self.assertIsNone(ajustar(huecos, 600, "primer"))

    def test_eat_y_conjunto_de_trabajo(self):
        self.assertAlmostEqual(eat_fallos(0.00001, 100, 10_000_000), 200, delta=0.01)
        self.assertEqual(eat_tlb(20, 1.0, 100), 120)
        self.assertEqual(conjunto_de_trabajo([7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2], 13, 6), {0, 2, 3, 4})


class AlgoritmosDeReemplazo(unittest.TestCase):
    def test_cadena_de_la_semana_14(self):
        fallos = {r: correr("m1_reemplazo_semana14.json", reemplazo=r)[1]["fallos_pagina"]
                  for r in ("FIFO", "LRU", "OPTIMO", "CLOCK")}
        self.assertEqual(fallos, {"FIFO": 10, "LRU": 9, "OPTIMO": 7, "CLOCK": 9})

    def test_belady_con_optimo(self):
        self.assertEqual(correr("s3b_cadena_clasica.json", reemplazo="OPTIMO", marcos=3)[1]["fallos_pagina"], 7)
        self.assertEqual(correr("s3b_cadena_clasica.json", reemplazo="OPTIMO", marcos=4)[1]["fallos_pagina"], 6)


class MMUPaginada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim, cls.res = correr("m3_tlb_bits_local.json")

    def test_mapa_por_frames_en_hexadecimal(self):
        mapa = self.sim.bitacora.pasos[0].vista["mapa"]
        self.assertEqual([f["proceso"] for f in mapa[:2]], ["SO", "SO"])          # marcos del SO
        self.assertEqual((mapa[3]["inicio"], mapa[3]["fin"]), ("0x3000", "0x3FFF"))  # 12 288 a 16 383

    def test_fallo_de_tlb_no_es_fallo_de_pagina(self):
        m = self.res["memoria"]
        self.assertGreater(m["tlb_fallos"], m["fallos"])
        self.assertEqual(self.res["fallos_pagina"], m["fallos"])

    def test_bit_m_y_swap(self):
        self.assertEqual(self.res["memoria"]["escrituras_swap"], 1)

    def test_reemplazo_local(self):
        for paso in self.sim.bitacora.pasos:
            if paso.componente.startswith("Gestor de memoria (CLOCK)"):
                pid_victima = paso.despues.split(":")[1].split(".")[0]
                self.assertIn(f"{pid_victima}.", paso.causa)
                self.assertIn("alcance local", paso.causa)

    def test_traduccion_visible_en_cada_acceso(self):
        ejecuciones = [p for p in self.sim.bitacora.pasos if p.tipo_paso.value == "EXEC"]
        self.assertTrue(all("MMU: VA=" in p.causa and "PA=" in p.causa for p in ejecuciones))


class MemoriaContigua(unittest.TestCase):
    def test_como_el_ejemplo_del_profesor(self):
        sim, r = correr("m2_memoria_contigua.json")
        causas = [p.causa for p in sim.bitacora.pasos]
        self.assertTrue(any("No hay memoria suficiente para P4" in c for c in causas))
        self.assertEqual(r["por_tipo"]["PROTECCION"], 1)                          # P6 accede fuera de su límite
        self.assertEqual(sim.bitacora.pasos[0].vista["mapa"][0]["proceso"], "SO")
        self.assertTrue(all(m["fin"] is not None for m in r["metricas"]))       # todos terminan
        self.assertEqual(r["invariantes"], ["OK"])


if __name__ == "__main__":
    unittest.main()
