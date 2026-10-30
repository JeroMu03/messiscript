import json
from pathlib import Path
from typing import Dict, List, Optional

from .modelos import Nivel, Objetivo, Trofeo

RUTA_NIVELES = Path(__file__).resolve().parent / "niveles.json"


def _validar_posicion(pos: list, cols: int, filas: int, etiqueta: str) -> tuple[int, int]:
  if not isinstance(pos, (list, tuple)) or len(pos) != 2:
      raise ValueError(f"Posición inválida para {etiqueta}: {pos}")
  x, y = int(pos[0]), int(pos[1])
  if not (0 <= x < cols and 0 <= y < filas):
      raise ValueError(f"Posición fuera de cancha para {etiqueta}: ({x}, {y})")
  return (x, y)


def cargar_niveles(ruta: Optional[Path] = None) -> List[Nivel]:
  archivo = ruta or RUTA_NIVELES
  datos = json.loads(archivo.read_text(encoding="utf-8"))
  niveles: List[Nivel] = []
  ids_vistos = set()

  for item in datos:
      nivel_id = item["id"]
      if nivel_id in ids_vistos:
          raise ValueError(f"ID de nivel duplicado: {nivel_id}")
      ids_vistos.add(nivel_id)

      cols = int(item["cancha"]["columnas"])
      filas = int(item["cancha"]["filas"])
      jugadores = list(item["jugadores"])

      inicio = {}
      for jug, pos in item["inicio"].items():
          if jug not in jugadores:
              raise ValueError(f"Jugador '{jug}' en inicio no figura en plantel de {nivel_id}")
          inicio[jug] = _validar_posicion(pos, cols, filas, f"{nivel_id}.{jug}")

      rivales = {
          riv: _validar_posicion(pos, cols, filas, f"{nivel_id}.{riv}")
          for riv, pos in item["rivales"].items()
      }

      pelota = item["pelota"]
      if pelota not in inicio:
          raise ValueError(f"Portador inicial '{pelota}' no tiene posición en {nivel_id}")

      arco = item["arco"]
      arco_x, arco_y, arco_alto = int(arco["x"]), int(arco["y"]), int(arco["alto"])
      if not (0 <= arco_x < cols and 0 <= arco_y < filas and arco_y + arco_alto <= filas):
          raise ValueError(f"Arco fuera de rango en {nivel_id}")

      obj_raw = item["objetivo"]
      objetivo = Objetivo(
          tipo=obj_raw["tipo"],
          asistente=obj_raw.get("asistente"),
          receptor=obj_raw.get("receptor"),
          rematador=obj_raw.get("rematador"),
          max_acciones=int(obj_raw.get("max_acciones", 20)),
      )
      for rol in (objetivo.asistente, objetivo.receptor, objetivo.rematador):
          if rol and rol not in jugadores:
              raise ValueError(f"Objetivo referencia jugador inexistente '{rol}' en {nivel_id}")

      trofeo_raw = item["trofeo"]
      if not trofeo_raw.get("id") or not trofeo_raw.get("nombre"):
          raise ValueError(f"Trofeo incompleto en {nivel_id}")
      trofeo = Trofeo(
          id=trofeo_raw["id"],
          nombre=trofeo_raw["nombre"],
          descripcion=trofeo_raw.get("descripcion", ""),
      )

      niveles.append(
          Nivel(
              id=nivel_id,
              nombre=item["nombre"],
              subtitulo=item["subtitulo"],
              escenario=item["escenario"],
              descripcion=item["descripcion"],
              codigo_inicial=item["codigo_inicial"],
              pista=item["pista"],
              columnas=cols,
              filas=filas,
              jugadores=jugadores,
              nombres=dict(item.get("nombres", {})),
              inicio=inicio,
              rivales=rivales,
              arquero=item["arquero"],
              pelota=pelota,
              arco_x=arco_x,
              arco_y=arco_y,
              arco_alto=arco_alto,
              objetivo=objetivo,
              trofeo=trofeo,
          )
      )

  return niveles


def construir_escenarios(niveles: Optional[List[Nivel]] = None) -> Dict[str, Dict[str, List[str]]]:
  lista = niveles if niveles is not None else cargar_niveles()
  return {n.escenario: {"jugadores": list(n.jugadores)} for n in lista}


def obtener_nivel(nivel_id: str, niveles: Optional[List[Nivel]] = None) -> Nivel:
  lista = niveles if niveles is not None else cargar_niveles()
  for n in lista:
      if n.id == nivel_id or n.escenario == nivel_id:
          return n
  raise KeyError(f"No existe el nivel '{nivel_id}'")