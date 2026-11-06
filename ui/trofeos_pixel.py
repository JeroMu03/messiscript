"""Trofeos originales de píxeles dibujados en Qt, sin archivos externos."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


COPA = (
    "......KKKKKK......",
    "....KKHHYYHHKK....",
    "...KHHHYYHHYYYK...",
    "..KHHYYHHYYYYDDK..",
    ".KHHYHHYYYYYDDDYK.",
    ".KHYHHYYYYYDDDYYK.",
    ".KYHHYYYYYDDDYYYK.",
    ".KYHYYYYYDDDYYYHK.",
    ".KDYYYYYDDDYYYHHK.",
    ".KDDYYYDDDYYYHHDK.",
    "..KDDYDDDYYHHDDK..",
    "..KDDDDYYHHDDDDK..",
    "...KDDYYHHDDDDK...",
    "...KDHYYDDDDYDK...",
    "....KYYDDDDYDK....",
    "....KYDDDDYHDK....",
    ".....KDDDYHDK.....",
    ".....KDDYHDDK.....",
    ".....KDYHDDDK.....",
    ".....KYHDDDDK.....",
    "....KKGGGGGGKK....",
    "....KHHYYHYYDK....",
    "...KHHYYHHYYDDK...",
    "..KKGGGGGGGGGGKK..",
    ".KKGGGGGGGGGGGGKK.",
    ".KKKKKKKKKKKKKKKK.",
)

OESTE = [(4,5),(8,6),(7,4),(10,5),(13,4),(14,6),(12,7),(15,8),(14,10),
         (12,11),(12,13),(10,14),(11,16),(9,17),(8,15),(7,18),(5,19),
         (5,17),(2,18),(3,15),(1,14),(5,14),(4,12),(7,12),(8,10),(6,10),(7,8),(4,7)]
ESTE = [(19,3),(21,4),(23,2),(24,5),(27,3),(27,6),(30,5),(28,8),(31,9),
        (28,11),(30,12),(28,13),(24,12),(25,15),(22,14),(23,17),(20,16),
        (19,19),(17,18),(18,15),(16,14),(18,12),(17,10),(19,9),(18,7),(20,6)]


def _mapa_islas():
    poligonos = [QPolygonF([QPointF(x, y) for x, y in puntos]) for puntos in (OESTE, ESTE)]
    celdas = {(x, y) for x in range(32) for y in range(22)
              if any(p.containsPoint(QPointF(x + .5, y + .5), Qt.FillRule.OddEvenFill) for p in poligonos)}
    celdas |= {(10,2),(11,2),(12,1),(3,19),(2,20),(15,20),(25,18),(26,18),(30,15)}
    return tuple("".join(
        "." if (x,y) not in celdas else
        "K" if any((x+dx,y+dy) not in celdas for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))) else
        "W" if 8 <= y <= 12 else "B"
        for x in range(32)) for y in range(22))


ISLAS = _mapa_islas()
CANDADO = (
    "...LLLLL...",
    "..LL...LL..",
    "..L.....L..",
    "..L.....L..",
    ".LLLLLLLLL.",
    ".LHHHHHHHL.",
    ".LHHKKKHHL.",
    ".LHHHKHHHL.",
    ".LHHHKHHHL.",
    ".LLLLLLLLL.",
)


class TrofeoPixel(QWidget):
    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self.tipo = tipo
        self.desbloqueado = False
        self.setMinimumSize(220, 172)
        self.setMaximumHeight(190)

    def actualizar(self, desbloqueado):
        self.desbloqueado = bool(desbloqueado)
        nombre = "Copa del Mundo" if self.tipo == "copa" else "Islas Malvinas"
        self.setAccessibleName(f"{nombre}: {'desbloqueado' if self.desbloqueado else 'bloqueado con candado'}")
        self.update()

    @staticmethod
    def _sprite(painter, filas, paleta, x, y, pixel):
        for iy, fila in enumerate(filas):
            for ix, valor in enumerate(fila):
                if valor in paleta:
                    painter.fillRect(QRectF(x + ix * pixel, y + iy * pixel, pixel, pixel), QColor(paleta[valor]))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        fondo = "#0D2435" if self.desbloqueado else "#374151"
        p.fillRect(self.rect(), QColor(fondo))
        secundario = QColor("#14334A" if self.desbloqueado else "#414B5A")
        for y in range(0, self.height(), 16):
            for x in range(0, self.width(), 16):
                if (x // 16 + y // 16) % 2 == 0:
                    p.fillRect(x, y, 16, 16, secundario)
        sprite = COPA if self.tipo == "copa" else ISLAS
        paleta = {"K":"#101827", "H":"#FEF08A", "Y":"#E9B443", "D":"#AE7B27", "G":"#166534", "W":"#FFFFFF", "B":"#75C9F1"}
        if not self.desbloqueado:
            paleta = {"K":"#1F2937", "H":"#9CA3AF", "Y":"#788390", "D":"#596473", "G":"#4B5563", "W":"#9CA3AF", "B":"#788390"}
        pixel = max(1, int(min((self.width() - 48) / len(sprite[0]), (self.height() - 24) / len(sprite))))
        x = (self.width() - len(sprite[0]) * pixel) // 2
        y = (self.height() - len(sprite) * pixel) // 2
        self._sprite(p, sprite, paleta, x, y, pixel)
        if not self.desbloqueado:
            tam = 3
            lx, ly = self.width() // 2 + 24, self.height() // 2 + 24
            p.fillRect(lx - 5, ly - 5, 43, 40, QColor("#1F2937"))
            self._sprite(p, CANDADO, {"L":"#CBD5E1", "H":"#F3F4F6", "K":"#334155"}, lx, ly, tam)


class TarjetaTrofeoPixel(QFrame):
    def __init__(self, tipo, nombre, requisito, parent=None):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        self.nombre = nombre
        self.requisito = requisito
        self.desbloqueado = False
        v = QVBoxLayout(self)
        self.icono = TrofeoPixel(tipo)
        self.estado = QLabel()
        self.estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo = QLabel(nombre)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.descripcion = QLabel()
        self.descripcion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.descripcion.setWordWrap(True)
        self.descripcion.setStyleSheet("color: #94A3B8;")
        v.addWidget(self.icono)
        v.addWidget(titulo)
        v.addWidget(self.estado)
        v.addWidget(self.descripcion)
        self.actualizar(False)

    def actualizar(self, desbloqueado):
        self.desbloqueado = bool(desbloqueado)
        self.icono.actualizar(desbloqueado)
        self.estado.setText("★ DESBLOQUEADO" if desbloqueado else "BLOQUEADO · CON CANDADO")
        self.estado.setStyleSheet(f"color: {'#FBBF24' if desbloqueado else '#9CA3AF'}; font-weight: bold;")
        self.descripcion.setText("¡Trofeo conseguido!" if desbloqueado else self.requisito)
