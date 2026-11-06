import tempfile
import unittest
from pathlib import Path

from juego import (
    GestorProgreso,
    cargar_niveles,
    construir_escenarios,
    obtener_nivel,
    simular,
)
from messiscript import analizar


class TestMotorEIntegracion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.niveles = cargar_niveles()
        cls.escenarios = construir_escenarios(cls.niveles)

    def _ejecutar_codigo(self, nivel_id: str, codigo: str = None):
        nivel = obtener_nivel(nivel_id, self.niveles)
        fuente = codigo if codigo is not None else nivel.codigo_inicial
        res_comp = analizar(fuente, escenarios=self.escenarios)
        self.assertTrue(res_comp["valido"], f"Error de compilación en {nivel_id}: {res_comp}")
        return simular(res_comp["acciones"], nivel)

    def test_mexico_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("MEXICO_2022")
        self.assertTrue(res.exito, res.motivo)
        self.assertIsNotNone(res.trofeo)

    def test_croacia_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("CROACIA_2022")
        self.assertTrue(res.exito, res.motivo)

    def test_pase_requiere_posicionar_companero(self):
        from dataclasses import replace
        nivel = replace(obtener_nivel("INGLATERRA_2026", self.niveles), tactica={})
        codigo = "INICIAR INGLATERRA_2026\nPASE LAUTARO\nFIN"
        sin_posicionar = simular(analizar(codigo, escenarios=self.escenarios)["acciones"], nivel)
        self.assertFalse(sin_posicionar.exito)
        self.assertIn("no está en la cancha", sin_posicionar.motivo)

        con_posicionar = simular(analizar(nivel.codigo_inicial, escenarios=self.escenarios)["acciones"], nivel)
        self.assertTrue(con_posicionar.exito, con_posicionar.motivo)

    def test_final_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("FINAL_2022")
        self.assertTrue(res.exito, res.motivo)
        self.assertIn("Di María", res.motivo)

    def test_final_cada_marca_es_necesaria(self):
        nivel = obtener_nivel("FINAL_2022", self.niveles)
        for instruccion, marcador, protegido in (
            ("POSICIONAR MAC_ALLISTER 21 6\n", "TCHOUAMENI", "MESSI"),
            ("POSICIONAR ALVAREZ 24 14\n", "KOUNDE", "MESSI"),
            ("POSICIONAR DI_MARIA 24 7\n", "VARANE", "DI_MARIA"),
        ):
            with self.subTest(marcador=marcador):
                res = self._ejecutar_codigo("FINAL_2022", nivel.codigo_inicial.replace(instruccion, ""))
                self.assertFalse(res.exito)
                self.assertIn(f"{marcador} le quitó la pelota a {protegido}", res.motivo)
                self.assertEqual(res.frames[-1].poseedor, marcador)
                self.assertTrue(any(f.estado == "presionando" for f in res.frames))

    def test_final_tres_marcas_y_animaciones(self):
        nivel = obtener_nivel("FINAL_2022", self.niveles)
        res = self._ejecutar_codigo("FINAL_2022")
        self.assertEqual(len(res.frames[0].flechas), 3)
        self.assertEqual(set(res.frames[0].posiciones), set(nivel.inicio) | set(nivel.rivales))
        for jugador, destino in (("MAC_ALLISTER", (21, 6)), ("ALVAREZ", (24, 14)), ("DI_MARIA", (24, 7))):
            self.assertTrue(any(f.posiciones[jugador] not in (nivel.inicio[jugador], destino) for f in res.frames))
        self.assertNotEqual(res.frames[-1].posiciones["TCHOUAMENI"], nivel.rivales["TCHOUAMENI"])
        self.assertNotEqual(res.frames[-1].posiciones["KOUNDE"], nivel.rivales["KOUNDE"])
        self.assertEqual(res.frames[-1].posiciones["VARANE"], nivel.rivales["VARANE"])

    def test_final_64_combinaciones_de_tres_zonas_2x2(self):
        from itertools import product
        nivel = obtener_nivel("FINAL_2022", self.niveles)
        for mx, my, ax, ay, dx, dy in product((20, 21), (5, 6), (23, 24), (14, 15), (24, 25), (6, 7)):
            with self.subTest(mac=(mx, my), alvarez=(ax, ay), di_maria=(dx, dy)):
                codigo = nivel.codigo_inicial.replace("MAC_ALLISTER 21 6", f"MAC_ALLISTER {mx} {my}").replace("ALVAREZ 24 14", f"ALVAREZ {ax} {ay}").replace("DI_MARIA 24 7", f"DI_MARIA {dx} {dy}")
                res = self._ejecutar_codigo("FINAL_2022", codigo)
                self.assertTrue(res.exito, res.motivo)

    def test_inglaterra_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("INGLATERRA_2026")
        self.assertTrue(res.exito, res.motivo)
        self.assertEqual(res.trofeo.id, "pase_final_2026")
        self.assertIn("Lautaro de cabeza", res.motivo)
        self.assertIn("centro de Messi", res.motivo)

    def test_inglaterra_solo_lautaro_tiene_amenaza(self):
        res = self._ejecutar_codigo("INGLATERRA_2026")
        self.assertEqual(len(res.frames[0].flechas), 1)
        self.assertIn("STONES", res.frames[0].flechas[0]["texto"])
        self.assertEqual(res.frames[0].flechas[0]["destino"], res.frames[0].posiciones["LAUTARO"])
        vuelo = [f for f in res.frames if f.estado == "centrando"]
        self.assertGreater(len(vuelo), 1)
        self.assertTrue(any(f.altura_balon > 0.9 for f in vuelo))
        self.assertEqual(vuelo[-1].altura_balon, 0)
        self.assertEqual(vuelo[-1].poseedor, "LAUTARO")

    def test_inglaterra_stones_roba_si_lautaro_no_escapa(self):
        nivel = obtener_nivel("INGLATERRA_2026", self.niveles)
        res = self._ejecutar_codigo(nivel.id, nivel.codigo_inicial.replace("POSICIONAR LAUTARO 27 10\n", ""))
        self.assertFalse(res.exito)
        self.assertIn("STONES le quitó la pelota a LAUTARO", res.motivo)
        self.assertEqual(res.frames[-1].poseedor, "STONES")
        self.assertTrue(any(f.estado == "centrando" for f in res.frames))

    def test_inglaterra_centro_requiere_banda(self):
        res = self._ejecutar_codigo("INGLATERRA_2026", "INICIAR INGLATERRA_2026\nPOSICIONAR LAUTARO 27 10\nPASE LAUTARO\nREMATAR\nFIN")
        self.assertFalse(res.exito)
        self.assertIn("El centro debe hacerlo MESSI desde la banda", res.motivo)

    def test_inglaterra_16_combinaciones_de_centro_y_desmarque(self):
        from itertools import product
        for cx, cy, lx, ly in product((24, 25), (4, 5), (26, 27), (9, 10)):
            with self.subTest(centro=(cx, cy), lautaro=(lx, ly)):
                codigo = (f"INICIAR INGLATERRA_2026\nPOSICIONAR LAUTARO {lx} {ly}\n"
                          f"MOVER DERECHA {cx-22}\nMOVER ARRIBA {6-cy}\nPASE LAUTARO\nREMATAR\nFIN")
                res = self._ejecutar_codigo("INGLATERRA_2026", codigo)
                self.assertTrue(res.exito, res.motivo)

    def test_movimiento_fuera_de_cancha(self):
        codigo = "INICIAR INGLATERRA_2026\nMOVER ARRIBA 10\nFIN"
        res = self._ejecutar_codigo("INGLATERRA_2026", codigo)
        self.assertFalse(res.exito)
        self.assertIn("salió de la cancha", res.motivo)

    def test_pase_interceptado(self):
        # Si Messi se mueve 3 a la derecha en vez de subir, choca con Gvardiol en [19, 12]
        codigo = "INICIAR CROACIA_2022\nPOSICIONAR MAC_ALLISTER 20 6\nMOVER DERECHA 3\nFIN"
        res = self._ejecutar_codigo("CROACIA_2022", codigo)
        self.assertFalse(res.exito)
        self.assertIn("Gvardiol", res.motivo)

    def test_croacia_mac_allister_libera_a_messi(self):
        for instruccion in ("", "POSICIONAR MAC_ALLISTER 18 9\n", "POSICIONAR MAC_ALLISTER 19 8\n"):
            with self.subTest(instruccion=instruccion):
                codigo = f"INICIAR CROACIA_2022\n{instruccion}POSICIONAR ALVAREZ 25 10\nMOVER ARRIBA 1\nFIN"
                res = self._ejecutar_codigo("CROACIA_2022", codigo)
                self.assertFalse(res.exito)
                self.assertIn("MODRIC le quitó la pelota a MESSI", res.motivo)
                self.assertEqual(res.frames[-1].poseedor, "MODRIC")

    def test_croacia_julian_pierde_al_recibir_si_no_se_adelanta(self):
        for instruccion in ("", "POSICIONAR ALVAREZ 23 11\n", "POSICIONAR ALVAREZ 22 10\n"):
            with self.subTest(instruccion=instruccion):
                codigo = (f"INICIAR CROACIA_2022\nPOSICIONAR MAC_ALLISTER 20 6\n{instruccion}"
                          "REPETIR 2 { MOVER ARRIBA 1 MOVER DERECHA 2 }\nPASE ALVAREZ\nREMATAR\nFIN")
                res = self._ejecutar_codigo("CROACIA_2022", codigo)
                self.assertFalse(res.exito)
                self.assertIn("LOVREN le quitó la pelota a ALVAREZ", res.motivo)
                self.assertEqual(res.frames[-1].poseedor, "LOVREN")
                self.assertTrue(any(f.poseedor == "ALVAREZ" and f.estado == "pasando" for f in res.frames))
                self.assertTrue(any(f.estado == "presionando" for f in res.frames))
                self.assertFalse(any(f.estado == "gol" for f in res.frames))

    def test_croacia_desmarques_independientes_y_animados(self):
        nivel = obtener_nivel("CROACIA_2022", self.niveles)
        for orden in (("MAC_ALLISTER 20 6", "ALVAREZ 25 10"), ("ALVAREZ 25 10", "MAC_ALLISTER 20 6")):
            codigo = (f"INICIAR CROACIA_2022\nPOSICIONAR {orden[0]}\nPOSICIONAR {orden[1]}\n"
                      "REPETIR 2 { MOVER ARRIBA 1 MOVER DERECHA 2 }\nPASE ALVAREZ\nREMATAR\nFIN")
            res = self._ejecutar_codigo("CROACIA_2022", codigo)
            self.assertTrue(res.exito, res.motivo)
            self.assertEqual(len(res.frames[0].flechas), 2)
            self.assertTrue(any(f.posiciones["MAC_ALLISTER"] not in (nivel.inicio["MAC_ALLISTER"], (20, 6)) for f in res.frames))
            self.assertTrue(any(f.posiciones["ALVAREZ"] not in (nivel.inicio["ALVAREZ"], (25, 10)) for f in res.frames))
            self.assertNotEqual(res.frames[-1].posiciones["MODRIC"], nivel.rivales["MODRIC"])
            for fijo in ("LOVREN", "GVARDIOL", "DE_PAUL", "ENZO_FERNANDEZ", "OTAMENDI"):
                self.assertEqual(res.frames[0].posiciones[fijo], res.frames[-1].posiciones[fijo])

    def test_croacia_desmarque_revertido_reactiva_amenaza(self):
        nivel = obtener_nivel("CROACIA_2022", self.niveles)
        for jugador in ("MAC_ALLISTER", "ALVAREZ"):
            x, y = nivel.inicio[jugador]
            codigo = nivel.codigo_inicial.replace("REPETIR 2", f"POSICIONAR {jugador} {x} {y}\nREPETIR 2")
            res = self._ejecutar_codigo("CROACIA_2022", codigo)
            self.assertFalse(res.exito)
            self.assertIn("quitó la pelota", res.motivo)

    def test_croacia_jugadores_de_contexto_fijos(self):
        res = self._ejecutar_codigo("CROACIA_2022", "INICIAR CROACIA_2022\nPOSICIONAR DE_PAUL 13 14\nFIN")
        self.assertFalse(res.exito)
        self.assertIn("solo podés reposicionar a MAC_ALLISTER, ALVAREZ", res.motivo)

    def test_remate_desde_muy_lejos(self):
        codigo = "INICIAR MEXICO_2022\nPOSICIONAR DI_MARIA 21 5\nREMATAR\nFIN"
        res = self._ejecutar_codigo("MEXICO_2022", codigo)
        self.assertFalse(res.exito)
        self.assertIn("lejos", res.motivo)

    def test_mexico_sin_desmarque_robo_animado(self):
        for accion in ("MOVER DERECHA 4\nREMATAR", "REMATAR", "PASE DI_MARIA"):
            with self.subTest(accion=accion):
                res = self._ejecutar_codigo("MEXICO_2022", f"INICIAR MEXICO_2022\n{accion}\nFIN")
                self.assertFalse(res.exito)
                self.assertIn("quitó la pelota", res.motivo)
                self.assertEqual(res.frames[-1].poseedor, "GUARDADO")
                self.assertEqual(res.frames[-1].balon, res.frames[-1].posiciones["GUARDADO"])
                intermedios = [f for f in res.frames if f.estado == "presionando"]
                self.assertGreater(len(intermedios), 1)
                self.assertNotEqual(intermedios[0].posiciones["GUARDADO"], res.frames[-1].posiciones["GUARDADO"])

    def test_mexico_equipo_inicial_y_desmarque_animado(self):
        nivel = obtener_nivel("MEXICO_2022", self.niveles)
        res = self._ejecutar_codigo("MEXICO_2022")
        self.assertTrue(res.exito, res.motivo)
        self.assertEqual(set(res.frames[0].posiciones), set(nivel.inicio) | set(nivel.rivales))
        self.assertEqual(res.frames[0].flechas[0]["destino"], nivel.inicio["MESSI"])
        intermedios = [f for f in res.frames if f.estado == "posicionando" and f.posiciones["DI_MARIA"] not in ((21, 8), (21, 5))]
        self.assertGreater(len(intermedios), 1)
        self.assertNotEqual(intermedios[0].posiciones["GUARDADO"], nivel.rivales["GUARDADO"])
        self.assertTrue(any(flecha["color"] == "#38BDF8" for f in intermedios for flecha in f.flechas))
        for fijo in ("LAUTARO", "DE_PAUL", "ENZO_FERNANDEZ"):
            self.assertTrue(all(f.posiciones[fijo] == nivel.inicio[fijo] for f in res.frames))

    def test_mexico_desmarque_insuficiente_no_libera_marca(self):
        for destino in ("21 8", "21 7", "15 8"):
            with self.subTest(destino=destino):
                res = self._ejecutar_codigo("MEXICO_2022", f"INICIAR MEXICO_2022\nPOSICIONAR DI_MARIA {destino}\nMOVER DERECHA 4\nREMATAR\nFIN")
                self.assertFalse(res.exito)
                self.assertIn("quitó la pelota", res.motivo)

    def test_mexico_solo_clave_reposicionable(self):
        res = self._ejecutar_codigo("MEXICO_2022", "INICIAR MEXICO_2022\nPOSICIONAR DE_PAUL 14 13\nFIN")
        self.assertFalse(res.exito)
        self.assertIn("solo podés reposicionar a DI_MARIA", res.motivo)

    def test_mexico_volver_a_posicion_inicial_reactiva_amenaza(self):
        res = self._ejecutar_codigo("MEXICO_2022", "INICIAR MEXICO_2022\nPOSICIONAR DI_MARIA 21 5\nPOSICIONAR DI_MARIA 21 8\nREMATAR\nFIN")
        self.assertFalse(res.exito)
        self.assertIn("quitó la pelota", res.motivo)

    def test_progreso_temporal_y_balon_de_oro(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta = Path(tmpdir) / "progreso.json"
            prog = GestorProgreso(ruta)
            self.assertEqual(prog.cantidad_completados, 0)
            for n in self.niveles:
                prog.registrar_victoria(n.id)
            self.assertTrue(prog.balon_de_oro_desbloqueado)

            # Recargar desde disco
            prog2 = GestorProgreso(ruta)
            self.assertEqual(prog2.cantidad_completados, 4)
            prog2.reiniciar()
            self.assertEqual(prog2.cantidad_completados, 0)

    def test_croacia_todas_las_combinaciones_de_zonas_2x2(self):
        nivel = obtener_nivel("CROACIA_2022", self.niveles)
        for mx in (20, 21):
            for my in (5, 6):
                for ax in (24, 25):
                    for ay in (9, 10):
                        with self.subTest(mac=(mx, my), alvarez=(ax, ay)):
                            codigo = nivel.codigo_inicial.replace("MAC_ALLISTER 20 6", f"MAC_ALLISTER {mx} {my}").replace("ALVAREZ 25 10", f"ALVAREZ {ax} {ay}")
                            res = self._ejecutar_codigo("CROACIA_2022", codigo)
                            self.assertTrue(res.exito, res.motivo)

    def test_mexico_cuatro_casillas_de_la_zona_2x2(self):
        nivel = obtener_nivel("MEXICO_2022", self.niveles)
        for x in (21, 22):
            for y in (4, 5):
                with self.subTest(destino=(x, y)):
                    codigo = nivel.codigo_inicial.replace("DI_MARIA 21 5", f"DI_MARIA {x} {y}")
                    res = self._ejecutar_codigo("MEXICO_2022", codigo)
                    self.assertTrue(res.exito, res.motivo)

    def test_desmarques_fuera_de_zonas_2x2_siguen_marcados(self):
        casos = [
            ("MEXICO_2022", "DI_MARIA 21 5", "DI_MARIA 20 5"),
            ("MEXICO_2022", "DI_MARIA 21 5", "DI_MARIA 21 6"),
            ("CROACIA_2022", "MAC_ALLISTER 20 6", "MAC_ALLISTER 19 6"),
            ("CROACIA_2022", "MAC_ALLISTER 20 6", "MAC_ALLISTER 20 7"),
            ("CROACIA_2022", "ALVAREZ 25 10", "ALVAREZ 26 10"),
            ("CROACIA_2022", "ALVAREZ 25 10", "ALVAREZ 25 11"),
        ]
        for nivel_id, antes, despues in casos:
            with self.subTest(destino=despues):
                nivel = obtener_nivel(nivel_id, self.niveles)
                res = self._ejecutar_codigo(nivel_id, nivel.codigo_inicial.replace(antes, despues))
                self.assertFalse(res.exito)
                self.assertIn("quitó la pelota", res.motivo)


if __name__ == "__main__":
    unittest.main()
