import json
from pathlib import Path
from typing import List, Optional

RUTA_DEFECTO = Path.home() / ".messiscript" / "progreso.json"
TOTAL_NIVELES = 4


class GestorProgreso:
  def __init__(self, ruta: Optional[Path] = None):
      self.ruta = ruta or RUTA_DEFECTO
      self.niveles_completados: List[str] = []
      self.ultimo_nivel: Optional[str] = None
      self.aviso_corrupto: bool = False
      self.cargar()

  def cargar(self) -> None:
      if not self.ruta.exists():
          self.niveles_completados = []
          self.ultimo_nivel = None
          return
      try:
          datos = json.loads(self.ruta.read_text(encoding="utf-8"))
          completados = datos.get("niveles_completados", [])
          if not isinstance(completados, list):
              raise ValueError("niveles_completados no es una lista")
          self.niveles_completados = [str(x) for x in completados]
          self.ultimo_nivel = datos.get("ultimo_nivel")
      except Exception:
          self.aviso_corrupto = True
          self.niveles_completados = []
          self.ultimo_nivel = None
          self.guardar()

  def guardar(self) -> None:
      self.ruta.parent.mkdir(parents=True, exist_ok=True)
      contenido = {
          "version": 1,
          "niveles_completados": self.niveles_completados,
          "ultimo_nivel": self.ultimo_nivel,
      }
      self.ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")

  def registrar_victoria(self, nivel_id: str) -> None:
      if nivel_id not in self.niveles_completados:
          self.niveles_completados.append(nivel_id)
      self.ultimo_nivel = nivel_id
      self.guardar()

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
      self.guardar()