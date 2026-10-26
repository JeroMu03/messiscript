"""Analizador de MessiScript v2: parser Coco/R extendido y semantica."""

from threading import RLock

from .Parser import Errors, Parser
from .Scanner import Scanner
from .semantica import validar_y_expandir

_lock = RLock()


def analizar(codigo: str, nombre_archivo: str = "<entrada>", escenarios=None) -> dict:
    """Analiza, valida y expande acciones; no simula fisica ni puntua goles.

    `escenarios` permite inyectar el plantel real desde una API o videojuego.
    El Scanner y el Parser comparten estado de errores heredado de Coco/R.
    """
    if not isinstance(codigo, str):
        raise TypeError("El codigo debe ser un str.")
    codigo = codigo.replace("\r\n", "\n").replace("\r", "\n")

    if "\u0100" in codigo:
        pos = codigo.index("\u0100")
        return {"valido": False, "errores": [{
            "tipo": "lexico", "linea": codigo.count("\n", 0, pos) + 1,
            "columna": pos - codigo.rfind("\n", 0, pos),
            "mensaje": "Caracter no permitido: U+0100.",
        }], "acciones": []}

    errores = []

    def registrar(linea, columna, mensaje):
        errores.append({"tipo": "sintactico", "linea": linea,
                        "columna": columna, "mensaje": mensaje})

    with _lock:
        parser = Parser()
        Errors.count = 0
        Errors.errors = []
        Errors.Init(nombre_archivo, "", False, parser.getParsingPos, parser.errorMessages)
        original_store = Errors.__dict__["storeError"]
        Errors.storeError = staticmethod(registrar)
        try:
            scanner = Scanner(codigo)
            # El Scanner v1 de Coco/R deja los tokens no reconocidos marcados
            # con noSym; distinguirlos de los errores de estructura gramatical.
            token = scanner.tokens.next
            while token.kind != Scanner.eofSym:
                if token.kind == Scanner.noSym:
                    errores.append({"tipo": "lexico", "linea": token.line,
                                    "columna": token.col,
                                    "mensaje": f"Simbolo no reconocido: {token.val!r}."})
                elif token.kind == Parser._numero and len(token.val) > 9:
                    errores.append({"tipo": "lexico", "linea": token.line,
                                    "columna": token.col,
                                    "mensaje": "Numero demasiado largo (maximo 9 digitos)."})
                token = token.next
            if not errores:
                parser.Parse(scanner)
        except ValueError as exc:
            if len(exc.args) == 3 and exc.args[0] == "Comentario de bloque sin cerrar.":
                mensaje, linea, columna = exc.args
                errores.append({"tipo": "lexico", "linea": linea,
                                "columna": columna, "mensaje": mensaje})
            else:
                raise
        finally:
            Errors.storeError = original_store

    if errores:
        return {"valido": False, "errores": errores, "acciones": []}

    programa = parser.programa
    errores_sem, acciones, simbolos = validar_y_expandir(programa, escenarios)
    return {"valido": not errores_sem, "errores": errores_sem,
            "acciones": acciones, "simbolos": simbolos,
            "escenario": programa["escenario"]}
