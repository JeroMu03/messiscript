"""Validacion semantica y expansion de repeticiones (sin motor de partido)."""

import json
from pathlib import Path

MAX_PASOS = 20
MAX_REPETICIONES = 10
MAX_ACCIONES = 300


def escenarios_demo():
    """Escenarios ilustrativos; reemplazables al integrar el videojuego."""
    return json.loads(Path(__file__).with_name("escenarios.json").read_text(encoding="utf-8"))


def validar_y_expandir(programa, escenarios=None):
    """Devuelve (errores, acciones, simbolos). No comprueba colisiones ni posesion."""
    disponibles = escenarios_demo() if escenarios is None else escenarios
    errores = []
    simbolos = {}
    acciones = []

    def err(nodo, mensaje):
        errores.append({"tipo": "semantico", "linea": nodo["linea"],
                        "columna": nodo["columna"], "mensaje": mensaje})

    escenario = programa["escenario"]
    if escenario not in disponibles:
        errores.append({"tipo": "semantico", "linea": 1, "columna": 1,
                        "mensaje": f"Escenario desconocido: {escenario}."})
    jugadores = (disponibles.get(escenario, {}).get("jugadores", [])
                 if isinstance(disponibles.get(escenario), dict) else [])

    for declaracion in programa["declaraciones"]:
        nombre = declaracion["nombre"]
        if nombre in simbolos:
            err(declaracion, f"Variable ya declarada: {nombre}.")
        else:
            simbolos[nombre] = declaracion["valor"]

    def resolver_cantidad(cantidad, limite, contexto):
        if cantidad["tipo"] == "numero":
            valor = cantidad["valor"]
        else:
            nombre = cantidad["nombre"]
            if nombre not in simbolos:
                err(cantidad, f"Variable no declarada: {nombre}.")
                return None
            valor = simbolos[nombre]
        if not 1 <= valor <= limite:
            err(cantidad, f"{contexto}: debe estar entre 1 y {limite} (valor: {valor}).")
            return None
        return valor

    def recorrer(instrucciones):
        for instruccion in instrucciones:
            tipo = instruccion["tipo"]
            if tipo == "mover":
                n = resolver_cantidad(instruccion["cantidad"], MAX_PASOS, "Pasos")
                if n is not None:
                    acciones.append({"tipo": "MOVER", "direccion": instruccion["direccion"], "pasos": n})
            elif tipo == "pase":
                jugador = instruccion["jugador"]
                if escenario in disponibles and jugador not in jugadores:
                    err(instruccion, f"El jugador {jugador} no esta en el escenario {escenario}.")
                elif jugador == "MESSI":
                    err(instruccion, "Messi no puede pasarse la pelota a si mismo.")
                else:
                    acciones.append({"tipo": "PASE", "jugador": jugador})
            elif tipo == "rematar":
                acciones.append({"tipo": "REMATAR"})
            elif tipo == "repetir":
                n = resolver_cantidad(instruccion["cantidad"], MAX_REPETICIONES, "Repeticiones")
                if n is not None:
                    for _ in range(n):
                        recorrer(instruccion["instrucciones"])
                        if len(acciones) > MAX_ACCIONES:
                            err(instruccion, f"Se excedieron las {MAX_ACCIONES} acciones por programa.")
                            return
            if len(acciones) > MAX_ACCIONES:
                return

    recorrer(programa["instrucciones"])
    if len(acciones) > MAX_ACCIONES and not any("acciones por programa" in e["mensaje"] for e in errores):
        err(programa["instrucciones"][0], f"Se excedieron las {MAX_ACCIONES} acciones por programa.")
    return errores, (acciones if not errores else []), simbolos
