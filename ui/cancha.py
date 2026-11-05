import math
import random
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from juego.modelos import Frame, Nivel, Resultado
from juego.motor import formatear_accion, nombre_visible


COLORES_CONFETI = ("#75AADB", "#FFFFFF", "#FBBF24", "#22C55E", "#EF4444", "#A855F7")

PELOTA_PIXELES = (
    "......KKKK......",
    "....KKWWWWKK....",
    "...KWWWWWWWWK...",
    "..KWWWWWWWWWWK..",
    "..KWWKKWWKKWWK..",
    ".KWWWKKKKKKWWWK.",
    ".KWWWWKKKKWWWWK.",
    ".KWWWWWKKWWWWWK.",
    ".KWWWWWKKWWWWWK.",
    ".KWWWWKKKKWWWWK.",
    ".KWWWKKKKKKWWWK.",
    "..KWWKKWWKKWWK..",
    "..KWWWWWWWWWWK..",
    "...KGGWWWWGGK...",
    "....KKGGGGKK....",
    "......KKKK......",
)

BALON_ORO_PIXELES = (
    "......BBBB......",
    "....BBYYYYBB....",
    "...BYYHHHHYYB...",
    "..BYYHHHHHHYYB..",
    "..BYHHHYYHHHYB..",
    ".BYYHHHHHHHHYYB.",
    ".BYHHHYYYYHHHYB.",
    ".BYHHYYDDYYHHYB.",
    ".BYHHYYDDYYHHYB.",
    ".BYHHHYYYYHHHYB.",
    ".BYYHHHHHHHHYYB.",
    "..BYHHHYYHHHYB..",
    "..BYYHHHHHHYYB..",
    "...BYYDDDDYYB...",
    "....BBDDDDBB....",
    "......BBBB......",
)

PALETA_PELOTA = {"W": "#FFFFFF", "K": "#0F172A", "G": "#94A3B8"}
PALETA_BALON = {"H": "#FEF08A", "Y": "#FBBF24", "D": "#D97706", "B": "#334155"}


class CanchaWidget(QWidget):
    frame_cambiado = Signal(int, int, str)  # indice_accion, total_acciones, texto
    reproduccion_finalizada = Signal(object)  # Resultado

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 340)
        self.nivel: Optional[Nivel] = None
        self.frames: List[Frame] = []
        self.resultado_actual: Optional[Resultado] = None
        self.idx_frame: int = 0
        self.velocidad: float = 1.0
        self.intervalo_base_ms: int = 120

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._avanzar_frame)

        self.celebracion_modo: Optional[str] = None
        self.celebracion_titulo = ""
        self.celebracion_subtitulo = ""
        self.celebracion_tick = 0
        self.celebracion_total_ticks = 0
        self.celebracion_particulas: List[dict] = []
        self.celebracion_timer = QTimer(self)
        self.celebracion_timer.setInterval(40)
        self.celebracion_timer.timeout.connect(self._avanzar_celebracion)

    def cargar_nivel(self, nivel: Nivel) -> None:
        self.timer.stop()
        self._detener_celebracion()
        self.nivel = nivel
        self.resultado_actual = None
        pos_iniciales = {
            "MESSI": (float(nivel.inicio["MESSI"][0]), float(nivel.inicio["MESSI"][1]))
        }
        for k, v in nivel.rivales.items():
            pos_iniciales[k] = (float(v[0]), float(v[1]))
        balon = pos_iniciales[nivel.pelota]
        self.frames = [
            Frame(
                indice=0,
                posiciones=pos_iniciales,
                balon=balon,
                poseedor=nivel.pelota,
                accion_indice=0,
                accion=None,
                rastro=[balon],
                estado="inicial",
                mensaje=f"Objetivo: {nivel.pista}",
            )
        ]
        self.idx_frame = 0
        self.update()

    def iniciar_reproduccion(self, resultado: Resultado, total_acciones: int) -> None:
        self.timer.stop()
        self._detener_celebracion()
        self.resultado_actual = resultado
        self.frames = resultado.frames
        self.idx_frame = 0
        self._total_acciones = total_acciones
        self.update()
        self._actualizar_intervalo()
        self.timer.start()

    def pausar_o_reanudar(self) -> bool:
        if self.timer.isActive():
            self.timer.stop()
            return False
        if self.frames and self.idx_frame < len(self.frames) - 1:
            self.timer.start()
            return True
        return False

    def reiniciar(self) -> None:
        self.timer.stop()
        if self.nivel:
            self.cargar_nivel(self.nivel)

    def cambiar_velocidad(self, mult: float) -> None:
        self.velocidad = max(0.25, mult)
        self._actualizar_intervalo()

    def _actualizar_intervalo(self) -> None:
        ms = max(25, int(self.intervalo_base_ms / self.velocidad))
        self.timer.setInterval(ms)

    def _avanzar_frame(self) -> None:
        if not self.frames:
            self.timer.stop()
            return
        if self.idx_frame < len(self.frames) - 1:
            self.idx_frame += 1
            fr = self.frames[self.idx_frame]
            self.frame_cambiado.emit(
                fr.accion_indice,
                getattr(self, "_total_acciones", 0),
                formatear_accion(fr.accion),
            )
            self.update()
        else:
            self.timer.stop()
            if self.resultado_actual is not None:
                self.reproduccion_finalizada.emit(self.resultado_actual)

    def iniciar_celebracion_8bit(self, modo: str, titulo: str, subtitulo: str) -> None:
        self._detener_celebracion()
        self.celebracion_modo = modo
        self.celebracion_titulo = titulo
        self.celebracion_subtitulo = subtitulo
        self.celebracion_tick = 0
        self.celebracion_total_ticks = 80 if modo == "balon_de_oro" else 70

        cantidad = random.randint(75, 90) if modo == "balon_de_oro" else random.randint(60, 80)
        self.celebracion_particulas = []
        for _ in range(cantidad):
            angulo = random.uniform(0.0, math.tau)
            velocidad = random.uniform(1.8, 6.5)
            self.celebracion_particulas.append(
                {
                    "x": 0.0,
                    "y": 0.0,
                    "vx": math.cos(angulo) * velocidad,
                    "vy": math.sin(angulo) * velocidad - 1.0,
                    "size": random.choice((6, 8)),
                    "color": random.choice(COLORES_CONFETI),
                    "fase": random.uniform(0.0, math.tau),
                    "oscilacion": random.uniform(0.12, 0.35),
                }
            )

        self.celebracion_timer.start()
        self.update()

    def _avanzar_celebracion(self) -> None:
        if not self.celebracion_modo:
            self.celebracion_timer.stop()
            return

        self.celebracion_tick += 1
        for particula in self.celebracion_particulas:
            particula["vy"] += 0.18
            particula["vx"] *= 0.995
            particula["x"] += particula["vx"] + math.sin(particula["fase"]) * particula["oscilacion"]
            particula["y"] += particula["vy"]
            particula["fase"] += 0.35

        if self.celebracion_tick >= self.celebracion_total_ticks:
            self._detener_celebracion()
            return

        self.update()

    def _detener_celebracion(self) -> None:
        self.celebracion_timer.stop()
        self.celebracion_modo = None
        self.celebracion_titulo = ""
        self.celebracion_subtitulo = ""
        self.celebracion_tick = 0
        self.celebracion_total_ticks = 0
        self.celebracion_particulas = []
        self.update()

    def _pintar_celebracion(
        self,
        painter: QPainter,
        ox: float,
        oy: float,
        cancha_w: float,
        cancha_h: float,
        celda: float,
    ) -> None:
        if not self.celebracion_modo:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        centro_x = ox + cancha_w / 2.0
        centro_y = oy + cancha_h / 2.0

        # Confeti pixelado que estalla desde el centro de la cancha.
        painter.setClipRect(QRectF(ox, oy, cancha_w, cancha_h))
        painter.setPen(Qt.PenStyle.NoPen)
        for particula in self.celebracion_particulas:
            painter.setBrush(QBrush(QColor(particula["color"])))
            painter.drawRect(
                QRectF(
                    centro_x + particula["x"],
                    centro_y + particula["y"],
                    particula["size"],
                    particula["size"],
                )
            )
        painter.setClipping(False)

        if self.celebracion_modo == "balon_de_oro":
            pixeles = BALON_ORO_PIXELES
            paleta = PALETA_BALON
            color_borde = QColor("#FBBF24")
            color_titulo = QColor("#FBBF24")
        else:
            pixeles = PELOTA_PIXELES
            paleta = PALETA_PELOTA
            color_borde = QColor("#22C55E")
            color_titulo = QColor("#22C55E")

        # Rebote retro al aparecer el sprite.
        progreso = min(1.0, max(0.0, (self.celebracion_tick - 2) / 12.0))
        c1 = 1.70158
        c3 = c1 + 1.0
        escala = 1.0 + c3 * (progreso - 1.0) ** 3 + c1 * (progreso - 1.0) ** 2
        escala = max(0.05, escala)
        bloque_base = max(3, int(min(cancha_w, cancha_h) * 0.014))
        bloque = max(2, int(bloque_base * escala))
        columnas = len(pixeles[0])
        filas = len(pixeles)
        sprite_w = columnas * bloque
        sprite_h = filas * bloque
        sprite_x = centro_x - sprite_w / 2.0
        sprite_y = oy + cancha_h * 0.38 - sprite_h / 2.0

        for fila, cadena in enumerate(pixeles):
            for columna, clave in enumerate(cadena):
                color = paleta.get(clave)
                if not color:
                    continue
                painter.fillRect(
                    QRectF(
                        sprite_x + columna * bloque,
                        sprite_y + fila * bloque,
                        bloque,
                        bloque,
                    ),
                    QColor(color),
                )

        if self.celebracion_modo == "balon_de_oro":
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(10):
                if (self.celebracion_tick // 4 + i) % 3 == 0:
                    angulo = i * math.tau / 10.0 + self.celebracion_tick * 0.05
                    radio = max(sprite_w, sprite_h) * (0.62 + 0.08 * (i % 3))
                    destello_x = centro_x + math.cos(angulo) * radio
                    destello_y = sprite_y + sprite_h / 2.0 + math.sin(angulo) * radio * 0.65
                    tam = 4 if i % 2 else 6
                    painter.fillRect(
                        QRectF(destello_x, destello_y, tam, tam),
                        QColor("#FEF08A"),
                    )

        # Cartel arcade central.
        panel_w = max(220.0, min(cancha_w - 28.0, 560.0))
        panel_h = min(96.0, max(62.0, cancha_h * 0.26))
        panel_x = ox + (cancha_w - panel_w) / 2.0
        panel_y = min(oy + cancha_h * 0.58, oy + cancha_h - panel_h - 8.0)
        panel = QRectF(panel_x, panel_y, panel_w, panel_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(11, 18, 32, 235)))
        painter.drawRect(panel)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color_borde, 4))
        painter.drawRect(panel)
        painter.setPen(QPen(color_borde, 2))
        painter.drawRect(panel.adjusted(5, 5, -5, -5))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color_borde))
        cm = 6
        for esquina_x, esquina_y in (
            (panel.left(), panel.top()),
            (panel.right() - cm, panel.top()),
            (panel.left(), panel.bottom() - cm),
            (panel.right() - cm, panel.bottom() - cm),
        ):
            painter.drawRect(QRectF(esquina_x, esquina_y, cm, cm))

        flags_centro = int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        flags_texto = flags_centro | int(Qt.TextFlag.TextWordWrap)

        tam_titulo = max(10, min(18, int(panel_w / 28)))
        tam_subtitulo = max(8, tam_titulo - 4)

        fuente_titulo = QFont("Cascadia Code", tam_titulo, QFont.Weight.Bold)
        fuente_titulo.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(fuente_titulo)
        painter.setPen(color_titulo)
        painter.drawText(
            QRectF(panel_x + 14, panel_y + 8, panel_w - 28, panel_h * 0.42),
            flags_texto,
            self.celebracion_titulo,
        )

        fuente_subtitulo = QFont("Cascadia Code", tam_subtitulo, QFont.Weight.DemiBold)
        fuente_subtitulo.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(fuente_subtitulo)
        painter.setPen(QColor("#E5E7EB"))
        painter.drawText(
            QRectF(panel_x + 14, panel_y + panel_h * 0.43, panel_w - 28, panel_h * 0.34),
            flags_texto,
            self.celebracion_subtitulo,
        )

        if self.celebracion_modo == "balon_de_oro":
            painter.setPen(QColor("#FEF08A"))
            painter.drawText(
                QRectF(panel_x + 14, panel_y + panel_h * 0.77, panel_w - 28, panel_h * 0.2),
                flags_centro,
                "4/4 NIVELES COMPLETADOS",
            )

        painter.restore()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111827"))

        if not self.nivel or not self.frames:
            return

        fr = self.frames[min(self.idx_frame, len(self.frames) - 1)]
        cols = self.nivel.columnas
        filas = self.nivel.filas

        margen_izq = 24
        margen_der = 5
        margen_sup = 16
        margen_inf = 37
        disp_w = max(100, self.width() - margen_izq - margen_der)
        disp_h = max(100, self.height() - margen_sup - margen_inf)
        celda = min(disp_w / cols, disp_h / filas)
        cancha_w = celda * cols
        cancha_h = celda * filas
        ox = margen_izq + (disp_w - cancha_w) / 2.0
        oy = margen_sup + (disp_h - cancha_h) / 2.0

        def centro_celda(cx: float, cy: float) -> QPointF:
            return QPointF(ox + (cx + 0.5) * celda, oy + (cy + 0.5) * celda)

        # 1. Césped en franjas verticales
        num_franjas = 10
        ancho_franja = cancha_w / num_franjas
        for i in range(num_franjas):
            color = QColor("#166534") if i % 2 == 0 else QColor("#15803D")
            painter.fillRect(QRectF(ox + i * ancho_franja, oy, ancho_franja, cancha_h), color)

        # 2. Matriz de puntos sobre cada celda
        painter.save()
        color_punto = QColor("#A7F3D0")
        color_punto.setAlpha(150)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color_punto))
        radio_punto = min(2.5, max(1.8, celda * 0.10))
        for cx in range(cols):
            for cy in range(filas):
                painter.drawEllipse(centro_celda(cx, cy), radio_punto, radio_punto)
        painter.restore()

        # 3. Coordenadas de la matriz
        painter.save()
        painter.setPen(QColor("#9CA3AF"))
        painter.setFont(QFont("Segoe UI", 7))
        for cx in range(cols):
            rect_x = QRectF(ox + cx * celda, oy - 15, celda, 13)
            painter.drawText(
                rect_x,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                str(cx),
            )
        for cy in range(filas):
            rect_y = QRectF(ox - 22, oy + cy * celda, 20, celda)
            painter.drawText(
                rect_y,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(cy),
            )
        painter.restore()

        # 4. Líneas reglamentarias
        pen_linea = QPen(QColor("#F8FAFC"), 2)
        painter.setPen(pen_linea)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(ox, oy, cancha_w, cancha_h))
        # Línea media y círculo central
        painter.drawLine(QPointF(ox + cancha_w / 2, oy), QPointF(ox + cancha_w / 2, oy + cancha_h))
        r_central = celda * 3.0
        painter.drawEllipse(QPointF(ox + cancha_w / 2, oy + cancha_h / 2), r_central, r_central)
        # Área grande derecha (6x12)
        area_w = 6 * celda
        area_h = 12 * celda
        area_y = oy + ((filas - 12) / 2.0) * celda
        painter.drawRect(QRectF(ox + cancha_w - area_w, area_y, area_w, area_h))

        # 5. Arco rival
        arco_top = oy + self.nivel.arco_y * celda
        arco_h = self.nivel.arco_alto * celda
        painter.setPen(QPen(QColor("#FBBF24"), 4))
        painter.drawRect(QRectF(ox + cancha_w - 4, arco_top, 8, arco_h))

        # 6. Rastro punteado de la jugada
        if len(fr.rastro) > 1:
            pen_rastro = QPen(QColor("#FDE047"), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen_rastro)
            for i in range(len(fr.rastro) - 1):
                p1 = centro_celda(*fr.rastro[i])
                p2 = centro_celda(*fr.rastro[i + 1])
                painter.drawLine(p1, p2)

        # 7. Dibujar Jugadores (Rivales y Argentina)
        radio_jug = max(12.0, celda * 0.65)
        fuente_etiq = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(fuente_etiq)

        # Rivales
        for riv_id in self.nivel.rivales:
            if riv_id not in fr.posiciones:
                continue
            pt = centro_celda(*fr.posiciones[riv_id])
            es_gk = riv_id == self.nivel.arquero
            painter.setBrush(QBrush(QColor("#FACC15" if es_gk else "#DC2626")))
            painter.setPen(QPen(QColor("#0F172A" if es_gk else "#FFFFFF"), 1.5))
            painter.drawEllipse(pt, radio_jug, radio_jug)

            etiq = "GK" if es_gk else riv_id[:2]
            painter.setPen(QColor("#0F172A" if es_gk else "#FFFFFF"))
            painter.drawText(
                QRectF(pt.x() - radio_jug, pt.y() - radio_jug, radio_jug * 2, radio_jug * 2),
                Qt.AlignmentFlag.AlignCenter,
                etiq,
            )

        # Aliados (Argentina)
        destacados = {
            "MESSI",
            fr.poseedor,
            self.nivel.objetivo.receptor,
            self.nivel.objetivo.rematador,
        }
        for jug_id in self.nivel.jugadores:
            if jug_id not in fr.posiciones:
                continue
            pt = centro_celda(*fr.posiciones[jug_id])
            es_messi = jug_id == "MESSI"
            painter.setBrush(QBrush(QColor("#38BDF8" if es_messi else "#75AADB")))
            painter.setPen(QPen(QColor("#FBBF24" if es_messi else "#FFFFFF"), 2.2 if es_messi else 1.5))
            painter.drawEllipse(pt, radio_jug, radio_jug)

            iniciales = "10" if es_messi else jug_id[:2]
            painter.setPen(QColor("#0B1220"))
            painter.drawText(
                QRectF(pt.x() - radio_jug, pt.y() - radio_jug, radio_jug * 2, radio_jug * 2),
                Qt.AlignmentFlag.AlignCenter,
                iniciales,
            )

            if jug_id in destacados:
                nom = nombre_visible(self.nivel, jug_id)
                painter.setPen(QColor("#F8FAFC"))
                painter.drawText(
                    QRectF(pt.x() - 40, pt.y() + radio_jug + 1, 80, 16),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    nom,
                )

        # 8. Pelota
        pt_balon = centro_celda(*fr.balon)
        r_balon = max(6.0, celda * 0.35)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor("#0F172A"), 1.8))
        painter.drawEllipse(pt_balon, r_balon, r_balon)

        # 9. Borde de estado (Gol / Fallo) y Banner inferior
        if fr.estado == "gol":
            painter.setPen(QPen(QColor("#22C55E"), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(ox, oy, cancha_w, cancha_h))
        elif fr.estado == "fallo":
            painter.setPen(QPen(QColor("#EF4444"), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(ox, oy, cancha_w, cancha_h))

        # Chip de estado abajo de la cancha
        chip_rect = QRectF(8, oy + cancha_h + 6, self.width() - 16, 24)
        color_texto = "#E5E7EB"
        if fr.estado == "gol":
            color_texto = "#22C55E"
        elif fr.estado == "fallo":
            color_texto = "#EF4444"
        painter.setPen(QColor(color_texto))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        texto_chip = f"{formatear_accion(fr.accion)}  ·  {fr.mensaje}"
        painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, texto_chip)

        # 10. Celebracion 8 bits sobre el centro de la cancha.
        self._pintar_celebracion(painter, ox, oy, cancha_w, cancha_h, celda)