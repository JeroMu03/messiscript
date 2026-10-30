from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
)

from juego.motor import formatear_accion


class PanelesInferiores(QTabWidget):
    error_seleccionado = Signal(int, int)  # linea, columna

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabla_errores = self._crear_tabla(["Tipo", "Línea", "Columna", "Mensaje"])
        self.tabla_acciones = self._crear_tabla(["#", "Instrucción", "Detalle"])
        self.tabla_simbolos = self._crear_tabla(["Identificador (VAR)", "Valor Constante"])

        self.tabla_errores.cellClicked.connect(self._al_hacer_click_error)

        self.addTab(self.tabla_errores, "Errores (0)")
        self.addTab(self.tabla_acciones, "Acciones (0)")
        self.addTab(self.tabla_simbolos, "Símbolos (0)")
        self._errores_actuales: list[dict] = []

    def _crear_tabla(self, cabeceras: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(cabeceras))
        t.setHorizontalHeaderLabels(cabeceras)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTriggers.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        return t

    def cargar_resultado_analisis(self, resultado: dict) -> None:
        errores = resultado.get("errores", [])
        acciones = resultado.get("acciones", [])
        simbolos = resultado.get("simbolos", {}) or {}

        self._errores_actuales = errores
        self.tabla_errores.setRowCount(len(errores))
        for i, err in enumerate(errores):
            self.tabla_errores.setItem(i, 0, QTableWidgetItem(str(err.get("tipo", "")).upper()))
            self.tabla_errores.setItem(i, 1, QTableWidgetItem(str(err.get("linea", 1))))
            self.tabla_errores.setItem(i, 2, QTableWidgetItem(str(err.get("columna", 1))))
            self.tabla_errores.setItem(i, 3, QTableWidgetItem(str(err.get("mensaje", ""))))

        self.tabla_acciones.setRowCount(len(acciones))
        for i, acc in enumerate(acciones):
            self.tabla_acciones.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.tabla_acciones.setItem(i, 1, QTableWidgetItem(str(acc.get("tipo", ""))))
            self.tabla_acciones.setItem(i, 2, QTableWidgetItem(formatear_accion(acc)))

        items_sim = list(simbolos.items())
        self.tabla_simbolos.setRowCount(len(items_sim))
        for i, (nombre, valor) in enumerate(items_sim):
            self.tabla_simbolos.setItem(i, 0, QTableWidgetItem(str(nombre)))
            self.tabla_simbolos.setItem(i, 1, QTableWidgetItem(str(valor)))

        self.setTabText(0, f"Errores ({len(errores)})")
        self.setTabText(1, f"Acciones ({len(acciones)})")
        self.setTabText(2, f"Símbolos ({len(items_sim)})")

        if errores:
            self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(1)

    def resaltar_accion(self, indice_1based: int) -> None:
        fila_activa = indice_1based - 1
        for r in range(self.tabla_acciones.rowCount()):
            color_fondo = QColor("#1D4ED8") if r == fila_activa else QColor("#111827")
            for c in range(self.tabla_acciones.columnCount()):
                item = self.tabla_acciones.item(r, c)
                if item:
                    item.setBackground(color_fondo)
        if 0 <= fila_activa < self.tabla_acciones.rowCount():
            self.tabla_acciones.scrollToItem(self.tabla_acciones.item(fila_activa, 0))

    def _al_hacer_click_error(self, fila: int, _col: int) -> None:
        if 0 <= fila < len(self._errores_actuales):
            err = self._errores_actuales[fila]
            self.error_seleccionado.emit(int(err.get("linea", 1)), int(err.get("columna", 1)))