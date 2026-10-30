import math
from typing import Dict, List, Optional, Tuple

from .modelos import Frame, Nivel, Resultado

ALCANCE_REMATE = 9.5
RADIO_INTERCEPCION = 0.72

DELTAS = {
  "DERECHA": (1, 0),
  "IZQUIERDA": (-1, 0),
  "ARRIBA": (0, -1),
  "ABAJO": (0, 1),
}

def nombre_visible(nivel: Nivel, jugador_id: str) -> str:
  return nivel.nombres.get(jugador_id, jugador_id.replace("-", " ").title())

def formatear_accion(accion: Optional[dict]) -> str:
  if not accion:
      return "Posición inicial"
  t = accion.get("tipo", "")
  if t == "MOVER":
      return f"MOVER {accion.get('direccion', '')} {accion.get('pasos', 1)}"
  if t == "PASE":
      return f"PASE {accion.get('jugador', '')}"
  return "REMATAR"

def _combinar_posiciones(
  aliados: Dict[str, Tuple[int, int]],
  rivales: Dict[str, Tuple[int, int]],
) -> Dict[str, Tuple[float, float]]:
  todas: Dict[str, Tuple[float, float]] = {}
  for k, v in aliados.items():
    todas[k] = (float(v[0]), float(v[1]))
  for k, v in rivales.items():
    todas[k] = (float(v[0]), float(v[1]))
  return todas

def _rival_en_linea(
  origen: Tuple[float, float],
  destino: Tuple[float, float],
  rivales: Dict[str, Tuple[int, int]],
  pasos: int = 8,
) -> Optional[Tuple[str, int]]:
  ox, oy = origen
  dx, dy = destino
  for i in range(1, pasos + 1):
      t = i / pasos
      px = ox + (dx - ox) * t
      py = oy + (dy - oy) * t
      for riv_id, (rx, ry) in rivales.items():
          if math.hypot(px - rx, py - ry) <= RADIO_INTERCEPCION:
              return riv_id, i
  return None

def _evaluar_objetivo(
  nivel: Nivel,
  hubo_gol: bool,
  autor_gol: Optional[str],
  ultimo_pase: Optional[Tuple[str, str]],
) -> Tuple[bool, str]:
  obj = nivel.objetivo
  if obj.tipo == "gol":
      if not hubo_gol:
          return False, "La jugada terminó sin convertir el gol."
      if obj.rematador and autor_gol != obj.rematador:
          return False, f"El gol debía convertirlo {nombre_visible(nivel, obj.rematador)}."
      return True, f"¡Gol de {nombre_visible(nivel, autor_gol or '')}!"

  if obj.tipo == "asistencia":
      if not ultimo_pase:
          return False, "No se completó la asistencia requerida."
      pasador, receptor = ultimo_pase
      if obj.asistente and pasador != obj.asistente:
          return False, f"La asistencia debía darla {nombre_visible(nivel, obj.asistente)}."
      if obj.receptor and receptor != obj.receptor:
          return False, f"El pase debía recibirlo {nombre_visible(nivel, obj.receptor)}."
      return True, f"¡Asistencia de {nombre_visible(nivel, pasador)} a {nombre_visible(nivel, receptor)}!"

  if obj.tipo == "gol_con_asistencia":
      if not hubo_gol or not ultimo_pase:
          return (
              False,
              f"La jugada no termina en gol con asistencia de {nombre_visible(nivel, obj.asistente or 'MESSI')} a {nombre_visible(nivel, obj.rematador or '')}.",
          )
      pasador, receptor = ultimo_pase
      if (obj.asistente and pasador != obj.asistente) or (
          obj.rematador and (receptor != obj.rematador or autor_gol != obj.rematador)
      ):
          return (
              False,
              f"La jugada no termina en gol con asistencia de {nombre_visible(nivel, obj.asistente or 'MESSI')} a {nombre_visible(nivel, obj.rematador or '')}.",
          )
      return (
          True,
          f"¡Gol de {nombre_visible(nivel, autor_gol or '')} con asistencia de {nombre_visible(nivel, pasador)}!",
      )

  return False, "Objetivo no reconocido."

def simular(acciones: List[dict], nivel: Nivel) -> Resultado:
  aliados = dict(nivel.inicio)
  rivales = dict(nivel.rivales)
  poseedor: Optional[str] = nivel.pelota
  balon = (float(aliados[poseedor][0]), float(aliados[poseedor][1]))
  rastro: List[Tuple[float, float]] = [balon]
  frames: List[Frame] = []

  ultimo_pase: Optional[Tuple[str, str]] = None
  hubo_gol = False
  autor_gol: Optional[str] = None
  acciones_ejecutadas = 0

  def agregar_frame(
      acc_idx: int,
      acc_dict: Optional[dict],
      estado: str,
      mensaje: str,
  ) -> None:
      frames.append(
          Frame(
              indice=len(frames),
              posiciones=_combinar_posiciones(aliados, rivales),
              balon=balon,
              poseedor=poseedor,
              accion_indice=acc_idx,
              accion=acc_dict,
              rastro=list(rastro),
              estado=estado,
              mensaje=mensaje,
          )
      )

  agregar_frame(0, None, "inicial", "Listo para reproducir la jugada.")

  for idx, acc in enumerate(acciones, start=1):
      tipo = acc.get("tipo", "")
      acciones_ejecutadas = idx

      if tipo == "MOVER":
          dx, dy = DELTAS.get(acc.get("direccion", ""), (0, 0))
          pasos = int(acc.get("pasos", 1))
          for _ in range(pasos):
              ax, ay = aliados[poseedor]
              nx, ny = ax + dx, ay + dy
              portador_nom = nombre_visible(nivel, poseedor)

              if not (0 <= nx < nivel.columnas and 0 <= ny < nivel.filas):
                  balon = (float(nx), float(ny))
                  rastro.append(balon)
                  motivo = f"{portador_nom} salió de la cancha."
                  agregar_frame(idx, acc, "fallo", motivo)
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

              for riv_id, (rx, ry) in rivales.items():
                  if (nx, ny) == (rx, ry):
                      aliados[poseedor] = (nx, ny)
                      balon = (float(nx), float(ny))
                      rastro.append(balon)
                      poseedor = None
                      motivo = f"{portador_nom} chocó con {nombre_visible(nivel, riv_id)}."
                      agregar_frame(idx, acc, "fallo", motivo)
                      return Resultado(False, motivo, frames, acciones_ejecutadas)

              for comp_id, (cx, cy) in aliados.items():
                  if comp_id != poseedor and (nx, ny) == (cx, cy):
                      motivo = f"La celda ({nx}, {ny}) está ocupada por {nombre_visible(nivel, comp_id)}."
                      agregar_frame(idx, acc, "fallo", motivo)
                      return Resultado(False, motivo, frames, acciones_ejecutadas)

              aliados[poseedor] = (nx, ny)
              balon = (float(nx), float(ny))
              rastro.append(balon)
              agregar_frame(idx, acc, "moviendo", f"{portador_nom} avanza a ({nx}, {ny}).")

      elif tipo == "PASE":
          receptor = acc.get("jugador", "")
          if receptor not in aliados:
              motivo = f"{nombre_visible(nivel, receptor)} no está en la cancha."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)

          origen = (float(aliados[poseedor][0]), float(aliados[poseedor][1]))
          destino = (float(aliados[receptor][0]), float(aliados[receptor][1]))
          corte = _rival_en_linea(origen, destino, rivales, pasos=8)
          pasos_totales = corte[1] if corte else 8
          pasador_actual = poseedor

          for p in range(1, pasos_totales + 1):
              t = p / 8.0
              balon = (
                  origen[0] + (destino[0] - origen[0]) * t,
                  origen[1] + (destino[1] - origen[1]) * t,
              )
              rastro.append(balon)
              es_final = p == pasos_totales
              if corte and es_final:
                  poseedor = None
                  motivo = f"El pase fue interceptado por {nombre_visible(nivel, corte[0])}."
                  agregar_frame(idx, acc, "fallo", motivo)
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

              poseedor = receptor if es_final else None
              agregar_frame(
                  idx,
                  acc,
                  "pasando",
                  f"{nombre_visible(nivel, receptor)} controla el pase."
                  if es_final
                  else f"Pase hacia {nombre_visible(nivel, receptor)}...",
              )

          ultimo_pase = (pasador_actual, receptor)
          poseedor = receptor

      elif tipo == "REMATAR":
          origen = (float(aliados[poseedor][0]), float(aliados[poseedor][1]))
          gk_pos = rivales.get(nivel.arquero, (nivel.arco_x - 1, nivel.arco_y + 2))
          opciones_y = [
              nivel.arco_y + 1,
              nivel.arco_y + nivel.arco_alto - 1,
              nivel.arco_y + (nivel.arco_alto // 2),
          ]
          mejor_y = max(opciones_y, key=lambda cy: abs(cy - gk_pos[1]))
          destino = (float(nivel.arco_x), float(mejor_y))

          if math.hypot(destino[0] - origen[0], destino[1] - origen[1]) > ALCANCE_REMATE:
              balon = (
                  origen[0] + (destino[0] - origen[0]) * 0.55,
                  origen[1] + (destino[1] - origen[1]) * 0.55,
              )
              rastro.append(balon)
              poseedor = None
              motivo = "El remate se fue desviado (demasiado lejos del arco)."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)

          bloqueo = _rival_en_linea(origen, destino, rivales, pasos=8)
          pasos_totales = bloqueo[1] if bloqueo else 8
          rematador_actual = poseedor

          for p in range(1, pasos_totales + 1):
              t = p / 8.0
              balon = (
                  origen[0] + (destino[0] - origen[0]) * t,
                  origen[1] + (destino[1] - origen[1]) * t,
              )
              rastro.append(balon)
              es_final = p == pasos_totales
              poseedor = None

              if bloqueo and es_final:
                  riv_id = bloqueo[0]
                  if riv_id == nivel.arquero:
                      motivo = f"{nombre_visible(nivel, riv_id)} atajó el remate."
                  else:
                      motivo = f"El remate fue bloqueado por {nombre_visible(nivel, riv_id)}."
                  agregar_frame(idx, acc, "fallo", motivo)
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

              agregar_frame(
                  idx,
                  acc,
                  "gol" if es_final else "rematando",
                  "¡GOL!" if es_final else "Remate en dirección al arco...",
              )

          hubo_gol = True
          autor_gol = rematador_actual
          break

  exito, motivo = _evaluar_objetivo(nivel, hubo_gol, autor_gol, ultimo_pase)
  if frames:
      frames[-1].estado = "gol" if exito else "fallo"
      frames[-1].mensaje = motivo

  return Resultado(
      exito=exito,
      motivo=motivo,
      frames=frames,
      acciones_ejecutadas=acciones_ejecutadas,
      trofeo=nivel.trofeo if exito else None,
  )