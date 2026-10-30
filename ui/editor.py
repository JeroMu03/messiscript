from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from .resaltador import ResaltadorMessiScript


class _GutterNumeros(QWidget):
    def __init__(self, editor: "EditorWidget"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.ancho_gutter(), 0)

    def paintEvent(self, event) -> None:
        self.editor.pintar_gutter(event)


class EditorWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gutter = _GutterNumeros(self)
        self.resaltador = ResaltadorMessiScript(self.document())
        self._lineas_error: set[int] = set()

        self.blockCountChanged.connect(self._actualizar_margen_gutter)
        self.updateRequest.connect(self._actualizar_area_gutter)
        self.cursorPositionChanged.connect(self._actualizar_selecciones_extra)

        self._actualizar_margen_gutter(0)
        self._actualizar_selecciones_extra()

    def ancho_gutter(self) -> int:
        digitos = len(str(max(1, self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * max(2, digitos)

    def _actualizar_margen_gutter(self, _) -> None:
        self.setViewportMargins(self.ancho_gutter(), 0, 0, 0)

    def _actualizar_area_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._actualizar_margen_gutter(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.ancho_gutter(), cr.height()))

    def pintar_gutter(self, event) -> None:
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), QColor("#0B1220"))

        bloque = self.firstVisibleBlock()
        num_bloque = bloque.blockNumber()
        top = round(self.blockBoundingGeometry(bloque).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(bloque).height())

        while bloque.isValid() and top <= event.rect().bottom():
            if bloque.isVisible() and bottom >= event.rect().top():
                numero = str(num_bloque + 1)
                es_err = (num_bloque + 1) in self._lineas_error
                painter.setPen(QColor("#EF4444") if es_err else QColor("#9CA3AF"))
                painter.drawText(
                    0,
                    top,
                    self.gutter.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    numero,
                )
            bloque = bloque.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(bloque).height())
            num_bloque += 1

    def limpiar_errores(self) -> None:
        self._lineas_error.clear()
        self._actualizar_selecciones_extra()
        self.gutter.update()

    def marcar_errores(self, errores: list[dict]) -> None:
        self._lineas_error = {max(1, int(e.get("linea", 1))) for e in errores}
        self._actualizar_selecciones_extra()
        self.gutter.update()

    def ir_a_posicion(self, linea: int, columna: int) -> None:
        bloque = self.document().findBlockByNumber(max(0, linea - 1))
        if not bloque.isValid():
            return
        cursor = QTextCursor(self.document())
        desplazamiento = min(max(0, columna - 1), max(0, len(bloque.text())))
        cursor.setPosition(bloque.position() + desplazamiento)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def _actualizar_selecciones_extra(self) -> None:
        selecciones = []

        # Línea actual
        if not self.isReadOnly():
            sel_actual = QTextEdit.ExtraSelection()
            sel_actual.format.setBackground(QColor("#1F2937"))
            sel_actual.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel_actual.cursor = self.textCursor()
            sel_actual.cursor.clearSelection()
            selecciones.append(sel_actual)

        # Líneas con error
        for num_linea in self._lineas_error:
            bloque = self.document().findBlockByNumber(num_linea - 1)
            if bloque.isValid():
                sel_err = QTextEdit.ExtraSelection()
                sel_err.format.setBackground(QColor(239, 68, 68, 45))
                sel_err.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
                sel_err.format.setUnderlineColor(QColor("#EF4444"))
                sel_err.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cur = QTextCursor(bloque)
                cur.clearSelection()
                sel_err.cursor = cur
                selecciones.append(sel_err)

        self.setExtraSelections(selecciones)