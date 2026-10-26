# -*- coding: utf-8 -*-
"""Ejecutor minimo para los archivos originales de Python 2.7."""
from __future__ import print_function

import argparse
import io

from Scanner import Scanner
from Parser import Errors, Parser


def main():
    argumentos = argparse.ArgumentParser(description='Analizador original para Python 2.7.')
    argumentos.add_argument('archivo')
    args = argumentos.parse_args()
    with io.open(args.archivo, 'r', encoding='utf-8-sig') as archivo:
        codigo = archivo.read()
    scanner = Scanner(codigo)
    parser = Parser()
    Errors.count = 0
    Errors.Init(args.archivo, '', False, parser.getParsingPos, parser.errorMessages)
    parser.Parse(scanner)
    Errors.Summarize(scanner.buffer)
    return 0 if Errors.count == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
