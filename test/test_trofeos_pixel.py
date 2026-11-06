import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.ventana import VentanaPrincipal


class TestTrofeosPixel(unittest.TestCase):
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

    def ganar(self, nivel_id):
        self.w.seleccionar_nivel(nivel_id)
        self.w.editor.setPlainText(self.w.nivel_actual.codigo_inicial)
        self.w.ejecutar_jugada()
        c = self.w.cancha
        c.timer.stop()
        while c.idx_frame < len(c.frames) - 1:
            c._avanzar_frame()
        c._avanzar_frame()
        c.celebracion_timer.stop()

    def test_cada_trofeo_se_desbloquea_con_su_partido(self):
        tarjetas = self.w.pagina_trofeos.trofeos_especiales
        self.assertFalse(tarjetas["FINAL_2022"].desbloqueado)
        self.assertFalse(tarjetas["INGLATERRA_2026"].desbloqueado)
        self.ganar("MEXICO_2022")
        self.ganar("CROACIA_2022")
        self.assertTrue(all(not t.desbloqueado for t in tarjetas.values()))
        self.ganar("FINAL_2022")
        self.assertTrue(tarjetas["FINAL_2022"].icono.desbloqueado)
        self.assertFalse(tarjetas["INGLATERRA_2026"].icono.desbloqueado)
        self.ganar("INGLATERRA_2026")
        self.assertTrue(all(t.icono.desbloqueado for t in tarjetas.values()))
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.w.btn_reiniciar_progreso.click()
        self.assertTrue(all(not t.icono.desbloqueado for t in tarjetas.values()))
        self.assertTrue(all("CANDADO" in t.estado.text() for t in tarjetas.values()))

    def test_progreso_guardado_recupera_la_coleccion(self):
        self.w.progreso.registrar_victoria("INGLATERRA_2026")
        otra = VentanaPrincipal(ruta_progreso=self.ruta)
        try:
            tarjetas = otra.pagina_trofeos.trofeos_especiales
            self.assertFalse(tarjetas["FINAL_2022"].icono.desbloqueado)
            self.assertTrue(tarjetas["INGLATERRA_2026"].icono.desbloqueado)
            self.assertIn("desbloqueado", tarjetas["INGLATERRA_2026"].icono.accessibleName())
            otra.pagina_trofeos.grab()
        finally:
            otra.close()
