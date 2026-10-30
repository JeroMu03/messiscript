"""Paquete de lógica de juego, niveles y simulación para MessiScript."""

from .modelos import Frame, Nivel, Objetivo, Resultado, Trofeo, Jugador, EstadoReproduccion
from .motor import simular
from .niveles import (
    cargar_niveles,
    construir_escenarios,
    obtener_nivel,
)
from .progreso import GestorProgreso

__all__ = [
    "Frame",
    "Nivel",
    "Objetivo",
    "Resultado",
    "Trofeo",
    "Jugador",
    "EstadoReproduccion",
    "simular",
    "cargar_niveles",
    "construir_escenarios",
    "obtener_nivel",
    "GestorProgreso",
]