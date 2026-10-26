import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from messiscript import analizar


class PruebasMessiScript(unittest.TestCase):
    def test_casos_de_gramatica_y_semantica(self):
        casos = json.loads(Path(__file__).with_name("casos_prueba.json").read_text(encoding="utf-8"))
        for nombre, codigo, esperado in casos:
            with self.subTest(caso=nombre):
                resultado = analizar(codigo)
                self.assertEqual(resultado["valido"], esperado, resultado)
                self.assertEqual(bool(resultado["errores"]), not esperado)

    def test_expansion_y_simbolos(self):
        codigo = "INICIAR CROACIA_2022 VAR PASOS = 2 REPETIR 2 { MOVER DERECHA PASOS MOVER ARRIBA 1 } PASE ALVAREZ FIN"
        resultado = analizar(codigo)
        self.assertTrue(resultado["valido"], resultado)
        self.assertEqual(resultado["simbolos"], {"PASOS": 2})
        self.assertEqual(resultado["acciones"], [
            {"tipo": "MOVER", "direccion": "DERECHA", "pasos": 2},
            {"tipo": "MOVER", "direccion": "ARRIBA", "pasos": 1},
            {"tipo": "MOVER", "direccion": "DERECHA", "pasos": 2},
            {"tipo": "MOVER", "direccion": "ARRIBA", "pasos": 1},
            {"tipo": "PASE", "jugador": "ALVAREZ"},
        ])

    def test_repeticiones_anidadas(self):
        r = analizar("INICIAR FINAL_2022 REPETIR 2 { REPETIR 2 { REMATAR } } FIN")
        self.assertTrue(r["valido"], r)
        self.assertEqual(len(r["acciones"]), 4)

    def test_inyeccion_escenarios(self):
        fuente = "INICIAR MISMO_NIVEL PASE ALVAREZ FIN"
        self.assertFalse(analizar(fuente)["valido"])
        self.assertTrue(analizar(fuente, escenarios={"MISMO_NIVEL": {"jugadores": ["MESSI", "ALVAREZ"]}})["valido"])

    def test_limite_de_acciones(self):
        r = analizar("INICIAR FINAL_2022 REPETIR 10 { REPETIR 10 { REPETIR 10 { REMATAR } } } FIN")
        self.assertFalse(r["valido"])
        self.assertEqual(r["acciones"], [])
        self.assertIn("acciones por programa", str(r["errores"]))

    def test_no_acumula_errores_entre_analisis(self):
        self.assertFalse(analizar("INICIAR CROACIA_2022 FIN")["valido"])
        self.assertTrue(analizar("INICIAR CROACIA_2022 REMATAR FIN")["valido"])

    def test_posicion_error(self):
        r = analizar("INICIAR CROACIA_2022\nMOVER ARRIBA\nFIN")
        self.assertFalse(r["valido"])
        self.assertEqual(r["errores"][0]["linea"], 3)
        self.assertGreaterEqual(r["errores"][0]["columna"], 1)

    def test_comentario_de_bloque_sin_cerrar(self):
        for fuente in ("INICIAR CROACIA_2022 REMATAR FIN /* sin cerrar", "/* falta cierre"):
            with self.subTest(fuente=fuente):
                r = analizar(fuente)
                self.assertFalse(r["valido"])
                self.assertIn("sin cerrar", r["errores"][0]["mensaje"])

    def test_caracteres_invalidos(self):
        for c in ("\u0100", "\u2603", "@"):
            with self.subTest(caracter=c):
                r = analizar("INICIAR CROACIA_2022 REMATAR FIN " + c + " REMATAR")
                self.assertFalse(r["valido"])

    def test_comentarios_unicode(self):
        self.assertTrue(analizar("/* jugada de Messi: ⚽ */ INICIAR FINAL_2022 REMATAR FIN")["valido"])

    def test_concurrentes(self):
        entradas = ["INICIAR CROACIA_2022 REMATAR FIN", "INICIAR CROACIA_2022 FIN"] * 10
        with ThreadPoolExecutor(max_workers=4) as pool:
            resultados = list(pool.map(analizar, entradas))
        self.assertEqual([r["valido"] for r in resultados], [True, False] * 10)


if __name__ == "__main__":
    unittest.main()
