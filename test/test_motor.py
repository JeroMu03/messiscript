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

    def test_final_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("FINAL_2022")
        self.assertTrue(res.exito, res.motivo)

    def test_inglaterra_codigo_inicial_gana(self):
        res = self._ejecutar_codigo("INGLATERRA_2026")
        self.assertTrue(res.exito, res.motivo)
        self.assertEqual(res.trofeo.id, "pase_final_2026")

    def test_movimiento_fuera_de_cancha(self):
        codigo = "INICIAR INGLATERRA_2026\nMOVER ARRIBA 10\nFIN"
        res = self._ejecutar_codigo("INGLATERRA_2026", codigo)
        self.assertFalse(res.exito)
        self.assertIn("salió de la cancha", res.motivo)

    def test_pase_interceptado(self):
        # En FINAL_2022, Koundé está en [21, 12] entre Messi [18, 12] y Álvarez [22, 10] si pasa directo a través de un rival
        nivel = obtener_nivel("CROACIA_2022", self.niveles)
        # Si Messi se mueve 3 a la derecha en vez de subir, choca con Gvardiol en [19, 12]
        codigo = "INICIAR CROACIA_2022\nMOVER DERECHA 3\nFIN"
        res = self._ejecutar_codigo("CROACIA_2022", codigo)
        self.assertFalse(res.exito)

    def test_remate_desde_muy_lejos(self):
        codigo = "INICIAR MEXICO_2022\nREMATAR\nFIN"
        res = self._ejecutar_codigo("MEXICO_2022", codigo)
        self.assertFalse(res.exito)
        self.assertIn("lejos", res.motivo)

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


if __name__ == "__main__":
    unittest.main()