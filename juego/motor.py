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
  if t == "POSICIONAR":
      return f"POSICIONAR {accion.get('jugador', '')} ({accion.get('x', 0)}, {accion.get('y', 0)})"
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


def aliados_iniciales(nivel: Nivel) -> Dict[str, Tuple[int, int]]:
  # La prueba táctica parte del equipo ubicado; los otros niveles conservan su mecánica.
  return dict(nivel.inicio) if nivel.tactica else {"MESSI": nivel.inicio["MESSI"]}


def reglas_tacticas(nivel: Nivel) -> List[dict]:
  if not nivel.tactica:
      return []
  return nivel.tactica.get("reglas", [{**nivel.tactica, "protegido": "MESSI", "tipo": "arrastre", "ejemplo": [21, 5]}])


def flechas_tacticas(nivel: Nivel, posiciones: dict, resueltas: Optional[dict] = None) -> List[dict]:
  flechas = []
  for regla in reglas_tacticas(nivel):
      clave, marcador = regla["jugador_clave"], regla["marcador"]
      resuelta = (resueltas or {}).get(clave, False)
      if resuelta and regla["tipo"] == "desmarque":
          flechas.append({"origen": nivel.inicio[clave], "destino": posiciones[clave],
                          "color": "#86EFAC", "texto": f"{clave} libre"})
      else:
          destino = clave if resuelta else regla["protegido"]
          flechas.append({"origen": posiciones[marcador], "destino": posiciones[destino],
                          "color": "#FBBF24" if resuelta else "#FB7185",
                          "texto": "Marca atraída" if resuelta else f"{marcador}: amenaza a {destino}"})
  return flechas

def _rival_en_linea(
  origen: Tuple[float, float],
  destino: Tuple[float, float],
  rivales: Dict[str, Tuple[int, int]],
  pasos: int = 8,
  aereo: bool = False,
) -> Optional[Tuple[str, int]]:
  ox, oy = origen
  dx, dy = destino
  for i in range(1, pasos + 1):
      t = i / pasos
      # Un centro alto pasa por encima de la marca; se disputa cerca del despegue o la caída.
      if aereo and math.sin(math.pi * t) > 0.35:
          continue
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
  aliados = aliados_iniciales(nivel)
  rivales = dict(nivel.rivales)
  poseedor: Optional[str] = nivel.pelota
  balon = (float(aliados[poseedor][0]), float(aliados[poseedor][1]))
  rastro: List[Tuple[float, float]] = [balon]
  frames: List[Frame] = []

  ultimo_pase: Optional[Tuple[str, str]] = None
  ultimo_pase_fue_centro = False
  hubo_gol = False
  autor_gol: Optional[str] = None
  acciones_ejecutadas = 0
  reglas = reglas_tacticas(nivel)
  claves = [regla["jugador_clave"] for regla in reglas]
  resueltas = {}

  def agregar_frame(
      acc_idx: int,
      acc_dict: Optional[dict],
      estado: str,
      mensaje: str,
      flechas: Optional[List[dict]] = None,
      duracion_ms: int = 120,
      altura_balon: float = 0.0,
      responsable_fallo: Optional[str] = None,
      consejo_fallo: str = "",
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
              flechas=(flechas if flechas is not None else
                       flechas_tacticas(nivel, _combinar_posiciones(aliados, rivales), resueltas)
                       if estado not in ("gol", "fallo", "rematando") else []),
              duracion_ms=duracion_ms,
              altura_balon=altura_balon,
              responsable_fallo=responsable_fallo,
              consejo_fallo=consejo_fallo,
          )
      )

  agregar_frame(0, None, "inicial", "Listo para reproducir la jugada.")

  def robar_pelota(regla: dict, idx: int, acc: dict) -> Resultado:
      nonlocal poseedor
      marcador = regla["marcador"]
      origen = rivales[marcador]
      destino = aliados[poseedor]
      clave = regla["jugador_clave"]
      x, y = regla["ejemplo"]
      motivo = f"{marcador} le quitó la pelota a {poseedor}: faltó el desmarque de {clave} (probá POSICIONAR {clave} {x} {y})."
      for p in range(1, 19):
          t = p / 18
          rivales[marcador] = (origen[0] + (destino[0] - origen[0]) * t,
                               origen[1] + (destino[1] - origen[1]) * t)
          if p == 18:
              poseedor = marcador
          agregar_frame(idx, acc, "fallo" if p == 18 else "presionando",
                        motivo if p == 18 else f"¡{marcador} va a robar la pelota!", duracion_ms=40,
                        responsable_fallo=marcador if p == 18 else None,
                        consejo_fallo=f"Faltó desmarcar a {clave} para escapar de {marcador}." if p == 18 else "")
      return Resultado(False, motivo, frames, acciones_ejecutadas)

  for idx, acc in enumerate(acciones, start=1):
      tipo = acc.get("tipo", "")
      acciones_ejecutadas = idx

      # Antes de conducir, pasar o rematar hay que liberar a Messi de la presión.
      if tipo in ("MOVER", "PASE", "REMATAR"):
          for regla in reglas:
              if poseedor == regla["protegido"] and not resueltas.get(regla["jugador_clave"]):
                  return robar_pelota(regla, idx, acc)

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
                      agregar_frame(idx, acc, "fallo", motivo, responsable_fallo=riv_id,
                                    consejo_fallo=f"Esquivá a {riv_id}: cambiá el recorrido antes de avanzar.")
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
          habilitados = [nivel.tactica["receptor_habilitado"]] if "receptor_habilitado" in nivel.tactica else claves
          if reglas and receptor not in habilitados:
              motivo = f"{receptor} es parte del contexto de esta jugada; el compañero habilitado es {', '.join(habilitados)}."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)
          if receptor not in aliados:
              motivo = f"{nombre_visible(nivel, receptor)} no está en la cancha."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)

          origen = (float(aliados[poseedor][0]), float(aliados[poseedor][1]))
          destino = (float(aliados[receptor][0]), float(aliados[receptor][1]))
          centro = nivel.tactica.get("centro")
          es_centro = bool(centro and receptor == centro["receptor"])
          if es_centro:
              x0, y0, x1, y1 = centro["zona_origen"]
              if poseedor != centro["pasador"] or not (x0 <= origen[0] <= x1 and y0 <= origen[1] <= y1):
                  motivo = f"El centro debe hacerlo {centro['pasador']} desde la banda: X={x0}–{x1}, Y={y0}–{y1}."
                  agregar_frame(idx, acc, "fallo", motivo, consejo_fallo="Llevá a Messi a la banda antes de tirar el centro.")
                  return Resultado(False, motivo, frames, acciones_ejecutadas)
          pasos_vuelo = 18 if es_centro else 8
          corte = _rival_en_linea(origen, destino, rivales, pasos=pasos_vuelo, aereo=es_centro)
          pasos_totales = corte[1] if corte else pasos_vuelo
          pasador_actual = poseedor

          for p in range(1, pasos_totales + 1):
              t = p / pasos_vuelo
              balon = (
                  origen[0] + (destino[0] - origen[0]) * t,
                  origen[1] + (destino[1] - origen[1]) * t,
              )
              rastro.append(balon)
              es_final = p == pasos_totales
              if corte and es_final:
                  poseedor = None
                  motivo = f"El pase fue interceptado por {nombre_visible(nivel, corte[0])}."
                  agregar_frame(idx, acc, "fallo", motivo, responsable_fallo=corte[0],
                                consejo_fallo=f"{corte[0]} cortó la línea de pase. Cambiá el ángulo o desmarcá al receptor.")
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

              poseedor = receptor if es_final else None
              agregar_frame(
                  idx,
                  acc,
                  "centrando" if es_centro else "pasando",
                  (f"{receptor} conecta el centro de {pasador_actual}." if es_final else f"Centro aéreo de {pasador_actual} hacia {receptor}...")
                  if es_centro else
                  f"{nombre_visible(nivel, receptor)} controla el pase." if es_final else f"Pase hacia {nombre_visible(nivel, receptor)}...",
                  duracion_ms=40 if es_centro else 120,
                  altura_balon=math.sin(math.pi * t) if es_centro and not es_final else 0.0,
              )

          ultimo_pase = (pasador_actual, receptor)
          ultimo_pase_fue_centro = es_centro
          poseedor = receptor
          for regla in reglas:
              if receptor == regla["protegido"] and not resueltas.get(regla["jugador_clave"]):
                  return robar_pelota(regla, idx, acc)

      elif tipo == "POSICIONAR":
          jugador = acc.get("jugador", "")
          x = int(acc.get("x", 0))
          y = int(acc.get("y", 0))

          if reglas and jugador not in claves:
              motivo = f"En esta jugada solo podés reposicionar a {', '.join(claves)}; {jugador} mantiene su posición."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)

          if not (0 <= x < nivel.columnas and 0 <= y < nivel.filas):
              motivo = f"{nombre_visible(nivel, jugador)} no puede posicionarse fuera de la cancha ({x}, {y})."
              agregar_frame(idx, acc, "fallo", motivo)
              return Resultado(False, motivo, frames, acciones_ejecutadas)

          for riv_id, (rx, ry) in rivales.items():
              if (x, y) == (rx, ry):
                  motivo = f"La celda ({x}, {y}) está ocupada por {nombre_visible(nivel, riv_id)}."
                  agregar_frame(idx, acc, "fallo", motivo)
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

          for comp_id, (cx, cy) in aliados.items():
              if comp_id != jugador and (x, y) == (cx, cy):
                  motivo = f"La celda ({x}, {y}) está ocupada por {nombre_visible(nivel, comp_id)}."
                  agregar_frame(idx, acc, "fallo", motivo)
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

          regla = next((r for r in reglas if r["jugador_clave"] == jugador), None)
          marcador = regla["marcador"] if regla else None
          if jugador in aliados:
              origen = aliados[jugador]
              destino = (x, y)
              origen_marca = rivales.get(marcador)
              destino_marca = origen_marca
              if regla:
                  x0, y0, x1, y1 = regla["zona_arrastre"]
                  desplazamiento = math.dist(nivel.inicio[jugador], destino)
                  atrae = x0 <= x <= x1 and y0 <= y <= y1 and desplazamiento >= regla["desplazamiento_minimo"]
                  # El marcador sigue al extremo desde una celda libre a su costado.
                  ocupadas = {pos for k, pos in aliados.items() if k != jugador} | {pos for k, pos in rivales.items() if k != marcador}
                  candidatas = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
                  libres = [pos for pos in candidatas if pos not in ocupadas and 0 <= pos[0] < nivel.columnas and 0 <= pos[1] < nivel.filas]
                  if regla["tipo"] == "desmarque":
                      resueltas[jugador] = atrae
                  elif atrae and libres:
                      destino_marca = min(libres, key=lambda pos: math.dist(origen_marca, pos))
                      resueltas[jugador] = True
                  else:
                      destino_marca = nivel.rivales[marcador]
                      resueltas[jugador] = False

              for p in range(1, 19):
                  t = p / 18
                  aliados[jugador] = (origen[0] + (x - origen[0]) * t, origen[1] + (y - origen[1]) * t)
                  if poseedor == jugador:
                      balon = aliados[jugador]
                      rastro.append(balon)
                  flechas = [{"origen": origen, "destino": destino, "color": "#38BDF8", "texto": f"Desmarque {jugador}"}]
                  if marcador:
                      rivales[marcador] = (origen_marca[0] + (destino_marca[0] - origen_marca[0]) * t,
                                           origen_marca[1] + (destino_marca[1] - origen_marca[1]) * t)
                      flechas += flechas_tacticas(nivel, _combinar_posiciones(aliados, rivales), resueltas)
                  agregar_frame(idx, acc, "posicionando", f"{jugador} se desplaza hacia ({x}, {y}).", flechas, 40)

          aliados[jugador] = (x, y)
          agregar_frame(
              idx,
              acc,
              "posicionando",
              (f"{jugador} completó el desmarque: {regla['protegido']} quedó libre de la amenaza de {marcador}." if regla and resueltas.get(jugador) else
               f"{jugador} está en ({x}, {y}). La amenaza sigue: usá la zona 2×2 X={regla['zona_arrastre'][0]}–{regla['zona_arrastre'][2]}, Y={regla['zona_arrastre'][1]}–{regla['zona_arrastre'][3]}." if regla else
               f"{nombre_visible(nivel, jugador)} se posiciona en ({x}, {y})."),
          )

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
                  agregar_frame(idx, acc, "fallo", motivo, responsable_fallo=riv_id,
                                consejo_fallo=f"{riv_id} tapó el remate. Buscá otro ángulo antes de definir.")
                  return Resultado(False, motivo, frames, acciones_ejecutadas)

              agregar_frame(
                  idx,
                  acc,
                  "gol" if es_final else "rematando",
                  "¡GOL!" if es_final else "Cabezazo en dirección al arco..." if ultimo_pase_fue_centro else "Remate en dirección al arco...",
              )

          hubo_gol = True
          autor_gol = rematador_actual
          break

  exito, motivo = _evaluar_objetivo(nivel, hubo_gol, autor_gol, ultimo_pase)
  if exito and ultimo_pase_fue_centro:
      motivo = f"¡Gol de {nombre_visible(nivel, autor_gol)} de cabeza tras el centro de {nombre_visible(nivel, ultimo_pase[0])}!"
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
