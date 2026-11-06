import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox
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
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("INGLATERRA_2026", ir_a_jugar=True)
            ventana.cancha.cargar_nivel(replace(ventana.nivel_actual, tactica={}))
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

    def test_mexico_prueba_tactica_y_reinicio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("MEXICO_2022", ir_a_jugar=True)
            cancha = ventana.cancha
            inicial = cancha.frames[0]
            self.assertIn("DI_MARIA", inicial.posiciones)
            self.assertIn("amenaza a MESSI", inicial.flechas[0]["texto"])
            ventana.editor.setPlainText(ventana.nivel_actual.codigo_inicial)
            ventana.ejecutar_jugada()
            cancha.timer.stop()
            self.assertEqual(cancha.frames[0].posiciones, inicial.posiciones)
            cancha.idx_frame = next(i for i, f in enumerate(cancha.frames) if f.estado == "posicionando")
            cancha._actualizar_intervalo()
            self.assertEqual(cancha.timer.interval(), 40)
            cancha.grab()
            cancha.reiniciar()
            self.assertEqual(cancha.frames[0].posiciones, inicial.posiciones)
            self.assertEqual(cancha.frames[0].flechas, inicial.flechas)
            ventana.close()

    def test_croacia_plantel_amenazas_y_ayuda(self):
        from ui.ayuda import _html_entorno
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.seleccionar_nivel("CROACIA_2022", ir_a_jugar=True)
            cancha = ventana.cancha
            inicial = cancha.frames[0]
            self.assertEqual(set(inicial.posiciones), set(ventana.nivel_actual.inicio) | set(ventana.nivel_actual.rivales))
            self.assertEqual(len(inicial.flechas), 2)
            ayuda = _html_entorno(ventana.nivel_actual)
            self.assertIn("MAC_ALLISTER", ayuda)
            self.assertIn("LOVREN", ayuda)
            ventana.editor.setPlainText(ventana.nivel_actual.codigo_inicial)
            ventana.ejecutar_jugada()
            cancha.timer.stop()
            self.assertTrue(cancha.resultado_actual.exito)
            self.assertEqual(cancha.frames[0].posiciones, inicial.posiciones)
            cancha.grab()
            cancha.reiniciar()
            self.assertEqual(cancha.frames[0].flechas, inicial.flechas)
            ventana.close()

    def test_sonido_gol_una_vez_al_entrar_la_pelota(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.editor.setPlainText(ventana.nivel_actual.codigo_inicial)
            ventana.ejecutar_jugada()
            cancha = ventana.cancha
            cancha.timer.stop()
            with patch.object(ventana.sonido_gol, "reproducir") as sonido:
                while cancha.idx_frame < len(cancha.frames) - 1:
                    cancha._avanzar_frame()
                sonido.assert_called_once_with()
                cancha._avanzar_frame()
                sonido.assert_called_once_with()
            ventana.close()

    def test_jugada_fallida_sin_sonido_gol(self):
        with tempfile.TemporaryDirectory() as tmp:
            ventana = VentanaPrincipal(ruta_progreso=Path(tmp) / "progreso.json")
            ventana.editor.setPlainText("INICIAR MEXICO_2022\nREMATAR\nFIN")
            ventana.ejecutar_jugada()
            cancha = ventana.cancha
            cancha.timer.stop()
            with patch.object(ventana.sonido_gol, "reproducir") as sonido:
                while cancha.idx_frame < len(cancha.frames) - 1:
                    cancha._avanzar_frame()
                cancha._avanzar_frame()
                sonido.assert_not_called()
            ventana.close()

    def test_boton_reinicia_progreso_con_confirmacion(self):
        from juego.progreso import GestorProgreso
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "progreso.json"
            ventana = VentanaPrincipal(ruta_progreso=ruta)
            for nivel in ventana.niveles:
                ventana.progreso.registrar_victoria(nivel.id)
            ventana._refrescar_progreso_global()
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
                ventana.btn_reiniciar_progreso.click()
            self.assertEqual(ventana.progreso.cantidad_completados, 4)
            ventana.editor.setPlainText(ventana.nivel_actual.codigo_inicial)
            ventana.ejecutar_jugada()
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                ventana.btn_reiniciar_progreso.click()
            self.assertEqual(GestorProgreso(ruta).cantidad_completados, 0)
            self.assertEqual(ventana.lbl_top_trofeos.text(), "0/4 🏆")
            self.assertFalse(ventana.cancha.timer.isActive())
            self.assertFalse(ventana.cancha.celebracion_timer.isActive())
            self.assertEqual(ventana.pagina_trofeos.barra.value(), 0)
            self.assertIn("Bloqueado", ventana.pagina_trofeos.lbl_balon_titulo.text())
            ventana.close()


if __name__ == "__main__":
    unittest.main()
