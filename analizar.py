"""Uso: python analizar.py ejemplo.messi"""

import argparse
import json
from pathlib import Path

from messiscript import analizar


def main() -> int:
    args_parser = argparse.ArgumentParser(description="Analiza un programa MessiScript.")
    args_parser.add_argument("archivo", type=Path, help="Archivo UTF-8 con el programa.")
    args = args_parser.parse_args()
    try:
        codigo = args.archivo.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"valido": False, "errores": [{"mensaje": str(exc)}]}, ensure_ascii=True, indent=2))
        return 2
    resultado = analizar(codigo, str(args.archivo))
    print(json.dumps(resultado, ensure_ascii=True, indent=2))
    return 0 if resultado["valido"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
