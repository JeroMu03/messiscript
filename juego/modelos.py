from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

class EstadoReproduccion(str, Enum):
  INICIAL = "INICIAL"
  ANALIZANDO = "ANALIZANDO"
  REPRODUCIENDO = "REPRODUCIENDO"
  PAUSADO = "PAUSADO"
  EXITO = "EXITO"
  FALLO = "FALLO"
  ERROR = "ERROR"

@dataclass
class Jugador:
  id: str
  nombre: str
  posicion: Tuple[int, int]
  equipo: str
  rol: str

@dataclass
class Objetivo:
  tipo: str
  asistente: Optional[str] = None
  rematador: Optional[str] = None
  receptor: Optional[str] = None
  max_acciones: int = 20

@dataclass
class Trofeo:
  id: str
  nombre: str
  descripcion: str

@dataclass
class Nivel:
  id: str
  nombre: str
  subtitulo: str
  escenario: str
  descripcion: str
  codigo_inicial: str
  pista: str
  columnas: int
  filas: int
  jugadores: List[str]
  nombres: Dict[str, str]
  inicio: Dict[str, Tuple[int, int]]
  rivales: Dict[str, Tuple[int, int]]
  arquero: str
  pelota: str
  arco_x: int
  arco_y: int
  arco_alto: int
  objetivo: Objetivo
  trofeo: Trofeo

@dataclass
class Frame:
  indice: int
  posiciones: Dict[str, Tuple[float, float]]
  balon: Tuple[float, float]
  poseedor: Optional[str]
  accion_indice: int
  accion: Optional[dict]
  rastro: List[Tuple[float, float]] = field(default_factory=list)
  estado: str = "inicial"
  mensaje: str = ""

@dataclass
class Resultado:
  exito: bool
  motivo: str
  frames: List[Frame]
  acciones_ejecutadas: int
  trofeo: Optional[Trofeo] = None