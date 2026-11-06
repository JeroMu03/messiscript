import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from juego.progreso import GestorProgreso, calcular_medalla
from ui.ventana import VentanaPrincipal


class TestMedallas(unittest.TestCase):
    def test_criterios(self):
        self.assertEqual(calcular_medalla(20, 3, False), "oro")
        self.assertEqual(calcular_medalla(3, 3, True), "plata")
        self.assertEqual(calcular_medalla(4, 3, True), "bronce")

    def test_migracion_progreso_anterior_y_mejor_marca(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "progreso.json"
            ruta.write_text(json.dumps({"version": 1, "niveles_completados": ["MEXICO_2022"], "ultimo_nivel": "MEXICO_2022"}), encoding="utf-8")
            p = GestorProgreso(ruta)
            self.assertEqual(p.cantidad_completados, 1)
            self.assertEqual(p.medallas["MEXICO_2022"]["medalla"], "bronce")
            p.registrar_victoria("MEXICO_2022", "oro", 5)
            p.registrar_victoria("MEXICO_2022", "plata", 2)
            p.registrar_victoria("MEXICO_2022", "oro", 6)
            self.assertEqual(p.medallas["MEXICO_2022"], {"medalla": "oro", "acciones": 5})
            p.registrar_victoria("MEXICO_2022", "oro", 3)
            p.registrar_pista("CROACIA_2022")
            recargado = GestorProgreso(ruta)
            self.assertEqual(recargado.medallas["MEXICO_2022"]["acciones"], 3)
            self.assertIn("CROACIA_2022", recargado.pistas_consultadas)
            recargado.reiniciar()
            vacio = GestorProgreso(ruta)
            self.assertEqual(vacio.medallas, {})
            self.assertEqual(vacio.pistas_consultadas, [])
            self.assertEqual(vacio.cantidad_completados, 0)


class TestMejorasUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "progreso.json"
        self.w = VentanaPrincipal(ruta_progreso=self.ruta)

    def tearDown(self):
        self.w.cancha.timer.stop()
        self.w.cancha.celebracion_timer.stop()
        self.w.close()
        self.tmp.cleanup()

    def terminar(self):
        cancha = self.w.cancha
        cancha.timer.stop()
        while cancha.idx_frame < len(cancha.frames) - 1:
            cancha._avanzar_frame()
        cancha._avanzar_frame()
        cancha.celebracion_timer.stop()

    def resolver(self):
        self.w.editor.setPlainText(self.w.nivel_actual.codigo_inicial)
        self.w.ejecutar_jugada()
        self.terminar()

    def elegir_ficha(self, jugador):
        cancha = self.w.cancha
        cancha.resize(1000, 580)
        cancha.grab()
        rect = next(rect for rect, jug in cancha._zonas_click if jug == jugador)
        QTest.mouseClick(cancha, Qt.MouseButton.LeftButton, pos=rect.center().toPoint())

    def test_seleccion_zona_y_ejecucion_la_oculta(self):
        self.elegir_ficha("DI_MARIA")
        self.assertEqual(self.w.cancha.jugador_seleccionado, "DI_MARIA")
        self.assertEqual(self.w.cancha.zona_jugador("DI_MARIA"), [21, 4, 22, 5])
        self.w.editor.setPlainText(self.w.nivel_actual.codigo_inicial)
        self.w.ejecutar_jugada()
        self.w.cancha.timer.stop()
        self.assertIsNone(self.w.cancha.jugador_seleccionado)
        self.elegir_ficha("DI_MARIA")
        self.assertIsNone(self.w.cancha.jugador_seleccionado)

    def test_messi_tiene_zona_de_centro_seleccionable(self):
        self.w.seleccionar_nivel("INGLATERRA_2026")
        self.elegir_ficha("MESSI")
        self.assertEqual(self.w.cancha.jugador_seleccionado, "MESSI")
        self.assertEqual(self.w.cancha.zona_jugador("MESSI"), [24, 4, 25, 5])

    def test_desafio_no_expone_pista_ni_zonas(self):
        self.w.btn_desafio.setChecked(True)
        self.assertTrue(self.w.cancha.modo_desafio)
        self.assertFalse(self.w.btn_pista.isEnabled())
        self.assertNotIn("21–22", self.w.lbl_objetivo_nivel.text())
        self.elegir_ficha("DI_MARIA")
        self.assertIsNone(self.w.cancha.jugador_seleccionado)
        with patch("ui.ventana.DialogoPista") as pista:
            self.w.mostrar_pista()
            pista.assert_not_called()
        with patch("ui.ventana.DialogoAyuda") as ayuda:
            self.w.mostrar_ayuda()
            ayuda.assert_called_once_with(self.w, None)
        self.resolver()
        self.assertEqual(self.w.progreso.medallas["MEXICO_2022"]["medalla"], "oro")

    def test_pista_persistente_limita_medalla_y_no_se_pierde_al_cambiar(self):
        with patch("ui.ventana.DialogoPista.exec", return_value=0):
            self.w.mostrar_pista()
        self.assertIn("MEXICO_2022", GestorProgreso(self.ruta).pistas_consultadas)
        self.w.seleccionar_nivel("CROACIA_2022")
        self.w.seleccionar_nivel("MEXICO_2022")
        self.resolver()
        self.assertEqual(self.w.progreso.medallas["MEXICO_2022"]["medalla"], "plata")

    def test_pista_durante_reproduccion_no_da_oro(self):
        self.w.editor.setPlainText(self.w.nivel_actual.codigo_inicial)
        self.w.ejecutar_jugada()
        self.w.cancha.timer.stop()
        with patch("ui.ventana.DialogoPista.exec", return_value=0):
            self.w.mostrar_pista()
        self.terminar()
        self.assertEqual(self.w.progreso.medallas["MEXICO_2022"]["medalla"], "plata")

    def test_bronce_por_solucion_mas_larga_con_pista(self):
        self.w.progreso.registrar_pista("MEXICO_2022")
        codigo = self.w.nivel_actual.codigo_inicial.replace("MOVER DERECHA 4", "POSICIONAR DI_MARIA 21 5\nMOVER DERECHA 4")
        self.w.editor.setPlainText(codigo)
        self.w.ejecutar_jugada()
        self.terminar()
        self.assertEqual(self.w.progreso.medallas["MEXICO_2022"]["medalla"], "bronce")

    def test_repetir_no_recompila_ni_modifica_progreso(self):
        self.resolver()
        guardado = self.ruta.read_bytes()
        resultado = self.w.ultimo_intento["resultado"]
        self.w.editor.setPlainText("código distinto e inválido")
        with patch("ui.ventana.analizar", side_effect=AssertionError("No debe recompilar")):
            self.w.btn_repetir.click()
            self.assertIs(self.w.cancha.resultado_actual, resultado)
            self.terminar()
        self.assertEqual(self.ruta.read_bytes(), guardado)
        self.w.seleccionar_nivel("CROACIA_2022")
        self.assertFalse(self.w.btn_repetir.isEnabled())
        self.assertIsNone(self.w.ultimo_intento)

    def test_fallo_destaca_responsable_y_muestra_consejo(self):
        self.w.btn_desafio.setChecked(True)
        self.w.editor.setPlainText("INICIAR MEXICO_2022\nMOVER DERECHA 1\nFIN")
        self.w.ejecutar_jugada()
        self.terminar()
        fr = self.w.cancha.frames[-1]
        self.assertEqual(fr.responsable_fallo, "GUARDADO")
        self.assertIn("DI_MARIA", self.w.lbl_fallo.text())
        self.assertIn("GUARDADO", self.w.lbl_fallo.text())
        self.assertNotIn("POSICIONAR", self.w.status.currentMessage())
        self.assertFalse(self.w.lbl_fallo.isHidden())
        self.w.cancha.grab()
        self.w.reiniciar_simulacion()
        self.assertTrue(self.w.lbl_fallo.isHidden())
        self.assertIsNone(self.w.cancha.frames[0].responsable_fallo)

    def test_reinicio_progreso_invalida_repeticion_y_medallas(self):
        self.resolver()
        self.w.progreso.registrar_pista("MEXICO_2022")
        self.w.progreso.reiniciar()
        self.w._al_reiniciar_progreso()
        self.assertIsNone(self.w.ultimo_intento)
        self.assertFalse(self.w.btn_repetir.isEnabled())
        self.assertEqual(GestorProgreso(self.ruta).medallas, {})
        self.assertEqual(GestorProgreso(self.ruta).pistas_consultadas, [])
