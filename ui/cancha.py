from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from juego.modelos import Frame, Nivel, Resultado
from juego.motor import formatear_accion, nombre_visible


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

    def cargar_nivel(self, nivel: Nivel) -> None:
        self.timer.stop()
        self.nivel = nivel
        self.resultado_actual = None
        pos_iniciales = {}
        for k, v in nivel.inicio.items():
            pos_iniciales[k] = (float(v[0]), float(v[1]))
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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111827"))

        if not self.nivel or not self.frames:
            return

        fr = self.frames[min(self.idx_frame, len(self.frames) - 1)]
        cols = self.nivel.columnas
        filas = self.nivel.filas

        margen = 5
        disp_w = max(100, self.width() - 2 * margen)
        disp_h = max(100, self.height() - 2 * margen - 32)
        celda = min(disp_w / cols, disp_h / filas)
        cancha_w = celda * cols
        cancha_h = celda * filas
        ox = (self.width() - cancha_w) / 2.0
        oy = margen + (disp_h - cancha_h) / 2.0

        def centro_celda(cx: float, cy: float) -> QPointF:
            return QPointF(ox + (cx + 0.5) * celda, oy + (cy + 0.5) * celda)

        # 1. Césped en franjas verticales
        num_franjas = 10
        ancho_franja = cancha_w / num_franjas
        for i in range(num_franjas):
            color = QColor("#166534") if i % 2 == 0 else QColor("#15803D")
            painter.fillRect(QRectF(ox + i * ancho_franja, oy, ancho_franja, cancha_h), color)

        # 2. Líneas reglamentarias
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

        # 3. Arco rival
        arco_top = oy + self.nivel.arco_y * celda
        arco_h = self.nivel.arco_alto * celda
        painter.setPen(QPen(QColor("#FBBF24"), 4))
        painter.drawRect(QRectF(ox + cancha_w - 4, arco_top, 8, arco_h))

        # 4. Rastro punteado de la jugada
        if len(fr.rastro) > 1:
            pen_rastro = QPen(QColor("#FDE047"), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen_rastro)
            for i in range(len(fr.rastro) - 1):
                p1 = centro_celda(*fr.rastro[i])
                p2 = centro_celda(*fr.rastro[i + 1])
                painter.drawLine(p1, p2)

        # 5. Dibujar Jugadores (Rivales y Argentina)
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

        # 6. Pelota
        pt_balon = centro_celda(*fr.balon)
        r_balon = max(6.0, celda * 0.35)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(QColor("#0F172A"), 1.8))
        painter.drawEllipse(pt_balon, r_balon, r_balon)

        # 7. Borde de estado (Gol / Fallo) y Banner inferior
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