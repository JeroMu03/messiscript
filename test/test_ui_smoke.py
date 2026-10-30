import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from ui.ventana import VentanaPrincipal


class TestUISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_carga_nivel_error_y_ejecucion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("INGLATERRA_2026", ir_a_jugar=True)
            self.assertIn("INICIAR INGLATERRA_2026", ventana.editor.toPlainText())

            # Ejecutar el código inicial válido
            ventana.ejecutar_jugada()
            self.assertGreater(ventana.paneles.tabla_acciones.rowCount(), 0)
            ventana.cancha.timer.stop()

            # Provocar un error quitando FIN
            ventana.editor.setPlainText("INICIAR INGLATERRA_2026\nMOVER DERECHA 2")
            ventana.ejecutar_jugada()
            self.assertGreater(ventana.paneles.tabla_errores.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()