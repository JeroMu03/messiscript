import json
from pathlib import Path
from typing import List, Optional

RUTA_DEFECTO = Path.home() / ".messiscript" / "progreso.json"
TOTAL_NIVELES = 4
ORDEN_MEDALLAS = {"bronce": 1, "plata": 2, "oro": 3}


def calcular_medalla(acciones: int, meta: int, pista_usada: bool) -> str:
  if not pista_usada:
      return "oro"
  return "plata" if acciones <= meta else "bronce"


class GestorProgreso:
  def __init__(self, ruta: Optional[Path] = None):
      self.ruta = ruta or RUTA_DEFECTO
      self.niveles_completados: List[str] = []
      self.ultimo_nivel: Optional[str] = None
      self.aviso_corrupto: bool = False
      self.medallas = {}
      self.pistas_consultadas = []
      self.cargar()

  def cargar(self) -> None:
      if not self.ruta.exists():
          self.niveles_completados = []
          self.ultimo_nivel = None
          self.medallas = {}
          self.pistas_consultadas = []
          return
      try:
          datos = json.loads(self.ruta.read_text(encoding="utf-8"))
          completados = datos.get("niveles_completados", [])
          if not isinstance(completados, list):
              raise ValueError("niveles_completados no es una lista")
          self.niveles_completados = [str(x) for x in completados]
          self.ultimo_nivel = datos.get("ultimo_nivel")
          marcas = datos.get("medallas", {})
          if not isinstance(marcas, dict):
              marcas = {}
          self.medallas = {}
          for nivel_id in self.niveles_completados:
              marca = marcas.get(nivel_id, {})
              if not isinstance(marca, dict):
                  marca = {}
              medalla = marca.get("medalla", "bronce")
              acciones = marca.get("acciones")
              self.medallas[nivel_id] = {"medalla": medalla if medalla in ORDEN_MEDALLAS else "bronce",
                                         "acciones": acciones if isinstance(acciones, int) and acciones >= 0 else None}
          pistas = datos.get("pistas_consultadas", [])
          self.pistas_consultadas = [str(x) for x in pistas] if isinstance(pistas, list) else []
      except Exception:
          self.aviso_corrupto = True
          self.niveles_completados = []
          self.ultimo_nivel = None
          self.medallas = {}
          self.pistas_consultadas = []
          self.guardar()

  def guardar(self) -> None:
      self.ruta.parent.mkdir(parents=True, exist_ok=True)
      contenido = {
          "version": 2,
          "niveles_completados": self.niveles_completados,
          "ultimo_nivel": self.ultimo_nivel,
          "medallas": self.medallas,
          "pistas_consultadas": self.pistas_consultadas,
      }
      self.ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")

  def registrar_victoria(self, nivel_id: str, medalla: str = "bronce", acciones: Optional[int] = None) -> None:
      if medalla not in ORDEN_MEDALLAS:
          raise ValueError("Medalla desconocida")
      if nivel_id not in self.niveles_completados:
          self.niveles_completados.append(nivel_id)
      self.ultimo_nivel = nivel_id
      previa = self.medallas.get(nivel_id, {})
      rango_previo = ORDEN_MEDALLAS.get(previa.get("medalla"), 0)
      acciones_previas = previa.get("acciones")
      if (ORDEN_MEDALLAS[medalla] > rango_previo or
          (ORDEN_MEDALLAS[medalla] == rango_previo and acciones is not None and
           (acciones_previas is None or acciones < acciones_previas))):
          self.medallas[nivel_id] = {"medalla": medalla, "acciones": acciones}
      self.guardar()

  def registrar_pista(self, nivel_id: str) -> None:
      if nivel_id not in self.pistas_consultadas:
          self.pistas_consultadas.append(nivel_id)
          self.guardar()

  def texto_medalla(self, nivel_id: str) -> str:
      marca = self.medallas.get(nivel_id)
      if not marca:
          return "Medalla: pendiente"
      texto = f"Medalla: {marca['medalla'].capitalize()}"
      if marca.get("acciones") is not None:
          texto += f" · {marca['acciones']} acciones"
      return texto

  def esta_completado(self, nivel_id: str) -> bool:
      return nivel_id in self.niveles_completados

  @property
  def cantidad_completados(self) -> int:
      return len(self.niveles_completados)

  @property
  def balon_de_oro_desbloqueado(self) -> bool:
      return len(self.niveles_completados) >= TOTAL_NIVELES

  def reiniciar(self) -> None:
      self.niveles_completados = []
      self.ultimo_nivel = None
      self.medallas = {}
      self.pistas_consultadas = []
      self.guardar()
