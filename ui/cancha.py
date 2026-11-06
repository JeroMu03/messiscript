import math
import random
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from juego.modelos import Frame, Nivel, Resultado
from juego.motor import aliados_iniciales, flechas_tacticas, formatear_accion, nombre_visible, reglas_tacticas


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


def pintar_ficha_messi(painter: QPainter, centro: QPointF, radio: float) -> None:
    """Emblema de tres piezas, escalable y con los colores de la ficha original."""
    silueta = QPainterPath()
    silueta.moveTo(15, 8)
    silueta.cubicTo(28, 9, 42, 20, 49, 26)
    silueta.lineTo(28, 18)
    silueta.cubicTo(41, 30, 36, 48, 39, 64)
    silueta.lineTo(45, 79)
    silueta.lineTo(20, 55)
    silueta.lineTo(20, 26)
    silueta.cubicTo(20, 18, 19, 12, 15, 8)
    silueta.closeSubpath()
    silueta.moveTo(121, 8)
    silueta.cubicTo(108, 9, 94, 20, 87, 26)
    silueta.lineTo(108, 18)
    silueta.cubicTo(95, 30, 100, 48, 97, 64)
    silueta.lineTo(91, 79)
    silueta.lineTo(116, 55)
    silueta.lineTo(116, 26)
    silueta.cubicTo(116, 18, 117, 12, 121, 8)
    silueta.closeSubpath()
    silueta.moveTo(58, 49)
    silueta.lineTo(68, 59)
    silueta.lineTo(77, 49)
    silueta.lineTo(77, 92)
    silueta.lineTo(68, 99)
    silueta.lineTo(58, 92)
    silueta.closeSubpath()

    painter.save()
    painter.translate(centro.x() - radio, centro.y() - radio * 91 / 106)
    painter.scale(2 * radio / 106, 2 * radio / 106)
    painter.translate(-15, -8)
    borde = QPen(QColor("#FBBF24"), 1.5 if radio >= 12 else 1)
    borde.setCosmetic(True)
    borde.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(borde)
    painter.setBrush(QColor("#38BDF8"))
    painter.drawPath(silueta)
    painter.restore()


class CanchaWidget(QWidget):
    frame_cambiado = Signal(int, int, str)  # indice_accion, total_acciones, texto
    reproduccion_finalizada = Signal(object)  # Resultado
    gol_marcado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(660, 320)
        self.nivel: Optional[Nivel] = None
        self.frames: List[Frame] = []
        self.resultado_actual: Optional[Resultado] = None
        self.modo_desafio = False
        self.jugador_seleccionado = None
        self._zonas_click = []
        self.setToolTip("Hacé clic en una ficha de la cancha o del cajón para ver su zona de destino.")
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
        self.jugador_seleccionado = None
        self.resultado_actual = None
        pos_iniciales = {k: (float(v[0]), float(v[1])) for k, v in aliados_iniciales(nivel).items()}
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
                flechas=flechas_tacticas(nivel, pos_iniciales),
            )
        ]
        self.idx_frame = 0
        self.update()

    def iniciar_reproduccion(self, resultado: Resultado, total_acciones: int) -> None:
        self.timer.stop()
        self._detener_celebracion()
        self.resultado_actual = resultado
        self.jugador_seleccionado = None
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
        base = self.frames[self.idx_frame].duracion_ms if self.frames else self.intervalo_base_ms
        ms = max(25, int(base / self.velocidad))
        self.timer.setInterval(ms)

    def _avanzar_frame(self) -> None:
        if not self.frames:
            self.timer.stop()
            return
        if self.idx_frame < len(self.frames) - 1:
            estado_anterior = self.frames[self.idx_frame].estado
            self.idx_frame += 1
            self._actualizar_intervalo()
            fr = self.frames[self.idx_frame]
            if fr.estado == "gol" and estado_anterior != "gol":
                self.gol_marcado.emit()
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

    def cambiar_modo_desafio(self, activo: bool) -> None:
        self.modo_desafio = activo
        self.jugador_seleccionado = None
        self.update()

    def zona_jugador(self, jugador):
        if not self.nivel:
            return None
        if jugador == "MESSI":
            return self.nivel.tactica.get("centro", {}).get("zona_origen")
        return next((r["zona_arrastre"] for r in reglas_tacticas(self.nivel) if r["jugador_clave"] == jugador), None)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        if self.modo_desafio or self.resultado_actual is not None:
            return
        seleccionado = next((jugador for rect, jugador in reversed(self._zonas_click) if rect.contains(event.position())), None)
        if not self.zona_jugador(seleccionado):
            seleccionado = None
        self.jugador_seleccionado = None if seleccionado == self.jugador_seleccionado else seleccionado
        self.update()

    def _pintar_cajon(self, painter: QPainter, rect: QRectF, fr: Frame) -> None:
        """Plantel del escenario, sincronizado con el frame de la jugada."""
        painter.save()
        painter.setPen(QPen(QColor("#334155"), 1))
        painter.setBrush(QColor("#0B1220"))
        painter.drawRoundedRect(rect, 12, 12)
        centro = Qt.AlignmentFlag.AlignCenter
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(QRectF(rect.x() + 8, rect.y() + 10, rect.width() - 16, 22), centro, "Fichas del escenario")
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(QRectF(rect.x() + 8, rect.y() + 34, rect.width() - 16, 18), centro, f"Argentina · {len(self.nivel.jugadores)} jugadores")

        filas = max(1, math.ceil(len(self.nivel.jugadores) / 2))
        espacio = 8.0
        ancho = (rect.width() - 24 - espacio) / 2
        alto = min(104.0, (rect.height() - 110 - espacio * (filas - 1)) / filas)
        for i, jug_id in enumerate(self.nivel.jugadores):
            ficha = QRectF(rect.x() + 12 + (i % 2) * (ancho + espacio), rect.y() + 62 + (i // 2) * (alto + espacio), ancho, alto)
            self._zonas_click.append((ficha, jug_id))
            en_cancha = jug_id in fr.posiciones
            con_pelota = jug_id == fr.poseedor
            borde = "#FBBF24" if con_pelota else "#334155"
            if jug_id == self.jugador_seleccionado:
                borde = "#38BDF8"
            painter.setPen(QPen(QColor(borde), 1.5 if con_pelota else 1))
            painter.setBrush(QColor("#172A3C" if en_cancha else "#111C2E"))
            painter.drawRoundedRect(ficha, 8, 8)

            compacto = alto < 54
            radio = 7.0 if compacto else min(18.0, max(8.0, (alto - 46) / 2))
            punto = QPointF(ficha.center().x(), ficha.y() + (3 if compacto else 7) + radio)
            painter.setBrush(QColor("#38BDF8" if jug_id == "MESSI" else "#75AADB"))
            painter.setPen(QPen(QColor("#FBBF24" if jug_id == "MESSI" else "#E0F2FE"), 2))
            if jug_id == "MESSI":
                pintar_ficha_messi(painter, punto, radio)
            else:
                painter.drawEllipse(punto, radio, radio)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#0B1220"))
            if jug_id != "MESSI":
                painter.drawText(QRectF(punto.x() - radio, punto.y() - radio, radio * 2, radio * 2), centro, jug_id[:2])

            painter.setPen(QColor("#F8FAFC"))
            fuente_nombre = QFont("Segoe UI", 8, QFont.Weight.Bold)
            ancho_nombre = painter.fontMetrics().horizontalAdvance(jug_id)
            if ancho_nombre > ancho - 8:
                fuente_nombre.setPointSizeF(8 * (ancho - 8) / ancho_nombre)
            painter.setFont(fuente_nombre)
            painter.drawText(QRectF(ficha.x() + 4, ficha.bottom() - (14 if compacto else 30), ancho - 8, 14 if compacto else 16), centro, jug_id)
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor("#FBBF24" if con_pelota else "#86EFAC" if en_cancha else "#94A3B8"))
            estado = "Con pelota" if con_pelota else "En cancha" if en_cancha else "Disponible"
            if self.nivel.tactica and not con_pelota:
                estado = "Movible · clave" if any(jug_id == r["jugador_clave"] for r in reglas_tacticas(self.nivel)) else "Posición fija"
            if not compacto:
                painter.drawText(QRectF(ficha.x() + 4, ficha.bottom() - 15, ancho - 8, 13), centro, estado)

        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QColor("#94A3B8"))
        indicacion = ("Rosa: robo · Celeste: movimiento\nOro: marca atraída\nVerde: receptor libre" if "reglas" in self.nivel.tactica else
                      "Rosa: robo · Celeste: desmarque\nOro: marca atraída" if self.nivel.tactica else
                      "Usá POSICIONAR para sumar\nuna ficha a la cancha.")
        if self.modo_desafio:
            indicacion = "Desafío activo\nSin zonas ni flechas de ayuda"
        elif self.resultado_actual is None:
            indicacion = "Elegí una ficha para iluminar\nsu zona de destino 2×2"
        painter.drawText(QRectF(rect.x() + 10, rect.bottom() - 43, rect.width() - 20, 38), int(centro) | int(Qt.TextFlag.TextWordWrap), indicacion)
        painter.restore()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        self._zonas_click = []
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
        ancho_cajon = max(188.0, min(260.0, self.width() * 0.25))
        separacion = 20
        disp_w = max(100, self.width() - margen_izq - margen_der - ancho_cajon - separacion)
        disp_h = max(100, self.height() - margen_sup - margen_inf)
        celda = min(disp_w / cols, disp_h / filas)
        cancha_w = celda * cols
        cancha_h = celda * filas
        ox = margen_izq + (disp_w - cancha_w) / 2.0
        oy = margen_sup + (disp_h - cancha_h) / 2.0

        self._pintar_cajon(
            painter,
            QRectF(self.width() - margen_der - ancho_cajon, margen_sup, ancho_cajon, disp_h),
            fr,
        )

        def centro_celda(cx: float, cy: float) -> QPointF:
            return QPointF(ox + (cx + 0.5) * celda, oy + (cy + 0.5) * celda)

        # 1. Césped en franjas verticales
        num_franjas = 10
        ancho_franja = cancha_w / num_franjas
        for i in range(num_franjas):
            color = QColor("#166534") if i % 2 == 0 else QColor("#15803D")
            painter.fillRect(QRectF(ox + i * ancho_franja, oy, ancho_franja, cancha_h), color)

        if not self.modo_desafio and self.resultado_actual is None:
            zona = self.zona_jugador(self.jugador_seleccionado)
            if zona:
                x0, y0, x1, y1 = zona
                painter.save()
                painter.setBrush(QColor(56, 189, 248, 100))
                painter.setPen(QPen(QColor("#7DD3FC"), 2))
                for x in range(x0, x1 + 1):
                    for y in range(y0, y1 + 1):
                        painter.drawRect(QRectF(ox + x * celda, oy + y * celda, celda, celda))
                painter.restore()

        # 2. Matriz de puntos sobre cada celda
        if self.resultado_actual is None and not self.modo_desafio:
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

        # Flechas de intención antes de dibujar las fichas, para no taparlas.
        painter.save()
        painter.setClipRect(QRectF(ox, oy, cancha_w, cancha_h))
        etiquetas = []
        zonas_jugadores = [QRectF(pt.x() - radio_jug - 4, pt.y() - radio_jug - 4, radio_jug * 2 + 8, radio_jug * 2 + 8)
                           for pt in (centro_celda(*pos) for pos in fr.posiciones.values())]
        for flecha in ([] if self.modo_desafio else fr.flechas):
            inicio = centro_celda(*flecha["origen"])
            final = centro_celda(*flecha["destino"])
            dx, dy = final.x() - inicio.x(), final.y() - inicio.y()
            longitud = math.hypot(dx, dy)
            if longitud < 1:
                continue
            ux, uy = dx / longitud, dy / longitud
            normal_x, normal_y = -uy, ux
            color = QColor(flecha["color"])
            painter.setPen(QPen(color, 2.5, Qt.PenStyle.DashLine))
            if flecha["color"] == "#38BDF8":
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(final, radio_jug, radio_jug)
            if longitud < radio_jug * 4 or flecha["color"] == "#38BDF8":
                # Curva por fuera de las fichas para mostrar amenazas a corta distancia.
                a = QPointF(inicio.x() + normal_x * (radio_jug + 3), inicio.y() + normal_y * (radio_jug + 3))
                b = QPointF(final.x() + normal_x * (radio_jug + 3), final.y() + normal_y * (radio_jug + 3))
                control = QPointF((a.x() + b.x()) / 2 + normal_x * 24, (a.y() + b.y()) / 2 + normal_y * 24)
                camino = QPainterPath(a)
                camino.quadTo(control, b)
                painter.drawPath(camino)
                tx, ty = b.x() - control.x(), b.y() - control.y()
                tangente = math.hypot(tx, ty)
                ux_f, uy_f = tx / tangente, ty / tangente
            else:
                a = QPointF(inicio.x() + ux * (radio_jug + 3), inicio.y() + uy * (radio_jug + 3))
                b = QPointF(final.x() - ux * (radio_jug + 5), final.y() - uy * (radio_jug + 5))
                painter.drawLine(a, b)
                ux_f, uy_f = ux, uy
            painter.setPen(QPen(color, 3))
            for signo in (-1, 1):
                painter.drawLine(b, QPointF(b.x() - ux_f * 9 + signo * uy_f * 5, b.y() - uy_f * 9 - signo * ux_f * 5))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            texto = flecha.get("texto", "")
            ancho_texto = painter.fontMetrics().horizontalAdvance(texto) + 12
            for distancia, desplazamiento in ((d, y) for d in (45, 70, 95, -45, -70, -95) for y in (0, -30, 30, -60, 60)):
                etiqueta = QRectF((inicio.x() + final.x() - ancho_texto) / 2 + normal_x * distancia,
                                  (inicio.y() + final.y()) / 2 + normal_y * distancia - 10 + desplazamiento, ancho_texto, 20)
                if (QRectF(ox, oy, cancha_w, cancha_h).contains(etiqueta)
                        and not any(etiqueta.intersects(zona) for zona in zonas_jugadores + etiquetas)):
                    break
            etiquetas.append(etiqueta)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(11, 18, 32, 225))
            painter.drawRoundedRect(etiqueta, 4, 4)
            painter.setPen(color)
            painter.drawText(etiqueta, Qt.AlignmentFlag.AlignCenter, texto)
        painter.restore()

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
            *(regla["jugador_clave"] for regla in reglas_tacticas(self.nivel)),
        }
        for jug_id in self.nivel.jugadores:
            if jug_id not in fr.posiciones:
                continue
            pt = centro_celda(*fr.posiciones[jug_id])
            self._zonas_click.append((QRectF(pt.x() - radio_jug, pt.y() - radio_jug, radio_jug * 2, radio_jug * 2), jug_id))
            es_messi = jug_id == "MESSI"
            es_clave = any(jug_id == r["jugador_clave"] for r in reglas_tacticas(self.nivel))
            color_ficha = "#38BDF8" if es_messi else "#75AADB" if es_clave or not self.nivel.tactica else "#7C9EAE"
            painter.setBrush(QBrush(QColor(color_ficha)))
            painter.setPen(QPen(QColor("#FBBF24" if es_messi else "#FFFFFF"), 2.2 if es_messi else 1.5))
            if es_messi:
                pintar_ficha_messi(painter, pt, radio_jug)
            else:
                painter.drawEllipse(pt, radio_jug, radio_jug)

            iniciales = "10" if es_messi else jug_id[:2]
            painter.setPen(QColor("#0B1220"))
            if not es_messi:
                painter.drawText(
                    QRectF(pt.x() - radio_jug, pt.y() - radio_jug, radio_jug * 2, radio_jug * 2),
                    Qt.AlignmentFlag.AlignCenter,
                    iniciales,
                )

            tapa_responsable = (fr.responsable_fallo in fr.posiciones and
                               fr.posiciones[fr.responsable_fallo] == fr.posiciones[jug_id])
            if jug_id in destacados and not tapa_responsable:
                nom = nombre_visible(self.nivel, jug_id)
                painter.setPen(QColor("#F8FAFC"))
                painter.drawText(
                    QRectF(pt.x() - 40, pt.y() + radio_jug + 1, 80, 16),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    nom,
                )

        # 8. Pelota
        pt_balon = centro_celda(*fr.balon)
        if fr.poseedor == "MESSI" and math.dist(fr.balon, fr.posiciones["MESSI"]) < 0.05:
            pt_balon += QPointF(radio_jug * 0.95, -radio_jug * 0.65)
        r_balon = max(6.0, celda * 0.35)
        if fr.altura_balon > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 95))
            painter.drawEllipse(pt_balon, r_balon * 0.9, r_balon * 0.4)
            pt_balon += QPointF(0, -fr.altura_balon * celda * 2)
            r_balon *= 1 + fr.altura_balon * 0.35
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
        chip_rect = QRectF(8, oy + cancha_h + 6, margen_izq + disp_w - 8, 24)
        color_texto = "#E5E7EB"
        if fr.estado == "gol":
            color_texto = "#22C55E"
        elif fr.estado == "fallo":
            color_texto = "#EF4444"
        painter.setPen(QColor(color_texto))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        mensaje = fr.mensaje
        if self.modo_desafio:
            if fr.estado == "inicial":
                mensaje = "Modo desafío: resolvé la jugada sin ayudas visuales ni Pista."
            elif fr.estado == "fallo":
                mensaje = fr.consejo_fallo or "La jugada falló. Revisá el recorrido y las marcas."
            elif "La amenaza sigue" in mensaje:
                mensaje = "Todavía queda una marca sin resolver."
        texto_chip = f"{formatear_accion(fr.accion)}  ·  {mensaje}"
        texto_chip = painter.fontMetrics().elidedText(texto_chip, Qt.TextElideMode.ElideRight, int(chip_rect.width()))
        painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, texto_chip)

        if fr.estado == "fallo" and fr.responsable_fallo in fr.posiciones:
            painter.save()
            responsable = centro_celda(*fr.posiciones[fr.responsable_fallo])
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#FB7185"), 4))
            painter.drawEllipse(responsable, radio_jug + 6, radio_jug + 6)
            if fr.poseedor == fr.responsable_fallo:
                painter.setBrush(QColor("#DC2626"))
                painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
                painter.drawEllipse(responsable, radio_jug, radio_jug)
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(QRectF(responsable.x() - radio_jug, responsable.y() - radio_jug, radio_jug * 2, radio_jug * 2), Qt.AlignmentFlag.AlignCenter, fr.responsable_fallo[:2])
                balon_robado = responsable + QPointF(radio_jug * 0.95, -radio_jug * 0.65)
                painter.setBrush(QColor("#FFFFFF"))
                painter.setPen(QPen(QColor("#0F172A"), 1.5))
                painter.drawEllipse(balon_robado, r_balon, r_balon)
            painter.setPen(QColor("#FDA4AF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(responsable.x() - 80, responsable.y() - radio_jug - 26, 160, 18), Qt.AlignmentFlag.AlignCenter, fr.responsable_fallo)
            painter.restore()

        # 10. Celebracion 8 bits sobre el centro de la cancha.
        self._pintar_celebracion(painter, ox, oy, cancha_w, cancha_h, celda)
