"""Convierte las salidas originales; ejecutar con Python 3.12.

Usa lib2to3, disponible en Python 3.12. La ejecucion del analizador convertido
no necesita este modulo ni dependencias externas.
"""

from pathlib import Path


def main() -> None:
    try:
        from lib2to3.refactor import RefactoringTool, get_fixers_from_package
    except ImportError:
        raise SystemExit("Para regenerar esta conversion, ejecuta el script con Python 3.12.")

    root = Path(__file__).resolve().parent
    # El parser v2 ya incorpora nuevas producciones. La salida Python 2 v1
    # incluida como historica NO se debe convertir encima de los archivos v2.
    generado = (root / "python2_original" / "Parser.py").read_text(encoding="utf-8")
    if "def Repeticion(" not in generado or "def Declaracion(" not in generado or "self.programa" not in generado:
        raise SystemExit(
            "La salida Python 2 no incluye el parser v2 con construccion del AST. "
            "Regenera con CocoRPy27 despues de incorporar acciones semanticas "
            "para el AST en MessiScript.atg. No se sobrescribio el parser funcional v2."
        )
    destino = root / "messiscript"
    destino.mkdir(exist_ok=True)
    fixer = RefactoringTool(get_fixers_from_package("lib2to3.fixes"))
    for nombre in ("Scanner.py", "Parser.py"):
        fuente = (root / "python2_original" / nombre).read_text(encoding="utf-8")
        archivo = destino / nombre
        salida = str(fixer.refactor_string(fuente, str(archivo)))
        if nombre == "Scanner.py":
            # Token.next es un enlace de lista, no el metodo de un iterador.
            salida = salida.replace(".__next__", ".next")
            # El runtime antiguo omite el error si el archivo termina dentro
            # de un comentario de bloque. Conservar el Scanner original aparte.
            inicio = salida.index("   def Comment0(")
            fin = salida.index("   def Comment1(", inicio)
            bloque = salida[inicio:fin]
            bloque = bloque.replace(
                "      line0 = self.line\n",
                "      line0 = self.line\n      commentStartCol = self.pos - self.lineStart + 1\n",
                1,
            )
            anterior = "elif self.ch == Buffer.EOF:\n               return False"
            nuevo = 'elif self.ch == Buffer.EOF:\n               raise ValueError("Comentario de bloque sin cerrar.", line0, commentStartCol)'
            if anterior not in bloque:
                raise SystemExit("Cambio inesperado en Comment0: revisar la conversion antes de continuar.")
            bloque = bloque.replace(anterior, nuevo, 1)
            salida = salida[:inicio] + bloque + salida[fin:]
        archivo.write_text(salida, encoding="utf-8")
        print("Convertido:", nombre)


if __name__ == "__main__":
    main()
