import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from ui import audio_8bit
from ui.ventana import VentanaPrincipal


class TestUISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_carga_nivel_error_y_ejecucion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("INGLATERRA_2026", ir_a_jugar=True)
            texto_inicial = ventana.editor.toPlainText()
            self.assertIn("INICIAR INGLATERRA_2026", texto_inicial)
            self.assertNotIn("POSICIONAR LAUTARO", texto_inicial)

            # Cargar explícitamente la solución para probar la ejecución
            ventana.editor.setPlainText(ventana.nivel_actual.codigo_inicial)
            ventana.ejecutar_jugada()
            self.assertGreater(ventana.paneles.tabla_acciones.rowCount(), 0)
            ventana.cancha.timer.stop()

            # Provocar un error quitando FIN
            ventana.editor.setPlainText("INICIAR INGLATERRA_2026\nMOVER DERECHA 2")
            ventana.ejecutar_jugada()
            self.assertGreater(ventana.paneles.tabla_errores.rowCount(), 0)

    def test_cancha_inicial_solo_messi_y_rivales(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("CROACIA_2022", ir_a_jugar=True)
            frame = ventana.cancha.frames[0]
            esperados = {"MESSI"} | set(ventana.nivel_actual.rivales)
            self.assertEqual(set(frame.posiciones), esperados)
            self.assertNotIn("ALVAREZ", frame.posiciones)

    def test_celebraciones_8bit_offscreen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("CROACIA_2022", ir_a_jugar=True)
            ventana.show()
            QApplication.processEvents()

            cancha = ventana.cancha
            cancha.iniciar_celebracion_8bit(
                "nivel",
                "¡NIVEL COMPLETADO!",
                "Gol de Álvarez • Trofeo de prueba",
            )
            self.assertEqual(cancha.celebracion_modo, "nivel")
            self.assertTrue(cancha.celebracion_timer.isActive())
            for _ in range(10):
                cancha._avanzar_celebracion()
            cancha.repaint()

            cancha.iniciar_celebracion_8bit(
                "balon_de_oro",
                "¡BALÓN DE ORO GANADO!",
                "Completaste los 4 niveles • Gol de Álvarez",
            )
            self.assertEqual(cancha.celebracion_modo, "balon_de_oro")
            self.assertTrue(cancha.celebracion_timer.isActive())
            for _ in range(10):
                cancha._avanzar_celebracion()
            cancha.repaint()

            cancha.reiniciar()
            self.assertIsNone(cancha.celebracion_modo)
            self.assertFalse(cancha.celebracion_timer.isActive())

            audio_8bit.reproducir_festejo_nivel()
            audio_8bit.reproducir_festejo_balon_de_oro()
            ventana.close()


if __name__ == "__main__":
    unittest.main()