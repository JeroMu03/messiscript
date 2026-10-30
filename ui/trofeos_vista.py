from typing import List
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from juego.modelos import Nivel
from juego.progreso import GestorProgreso


class PaginaTrofeos(QWidget):
    progreso_borrado = Signal()

    def __init__(self, niveles: List[Nivel], progreso: GestorProgreso, parent=None):
        super().__init__(parent)
        self.niveles = niveles
        self.progreso = progreso

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        cab = QHBoxLayout()
        titulo = QLabel("VITRINA DE TROFEOS")
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.lbl_cuenta = QLabel()
        self.lbl_cuenta.setStyleSheet("font-size: 12pt; color: #FBBF24; font-weight: bold;")
        cab.addWidget(titulo)
        cab.addStretch()
        cab.addWidget(self.lbl_cuenta)
        layout.addLayout(cab)

        self.barra = QProgressBar()
        self.barra.setRange(0, len(niveles))
        layout.addWidget(self.barra)

        self.grilla = QGridLayout()
        self.grilla.setSpacing(16)
        layout.addLayout(self.grilla)

        self.card_balon = QFrame()
        self.card_balon.setObjectName("tarjeta")
        vb = QVBoxLayout(self.card_balon)
        self.lbl_balon_titulo = QLabel()
        self.lbl_balon_titulo.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self.lbl_balon_desc = QLabel()
        vb.addWidget(self.lbl_balon_titulo)
        vb.addWidget(self.lbl_balon_desc)
        layout.addWidget(self.card_balon)

        layout.addStretch()

        fila_btn = QHBoxLayout()
        btn_borrar = QPushButton("Borrar progreso")
        btn_borrar.setObjectName("btnPeligro")
        btn_borrar.clicked.connect(self._confirmar_borrado)
        fila_btn.addWidget(btn_borrar)
        fila_btn.addStretch()
        layout.addLayout(fila_btn)

        self.actualizar_vitrina()

    def actualizar_vitrina(self) -> None:
        while self.grilla.count():
            it = self.grilla.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        comp = self.progreso.cantidad_completados
        total = len(self.niveles)
        self.lbl_cuenta.setText(f"{comp}/{total} completados")
        self.barra.setValue(comp)

        for idx, n in enumerate(self.niveles):
            desbloqueado = self.progreso.esta_completado(n.id)
            card = QFrame()
            card.setObjectName("tarjeta")
            v = QVBoxLayout(card)
            estado = "DESBLOQUEADO" if desbloqueado else "BLOQUEADO"
            color = "#FBBF24" if desbloqueado else "#6B7280"
            lbl_e = QLabel(estado)
            lbl_e.setStyleSheet(f"color: {color}; font-weight: bold;")
            lbl_t = QLabel(n.trofeo.nombre)
            lbl_t.setStyleSheet("font-size: 12pt; font-weight: bold;")
            lbl_d = QLabel(n.trofeo.descripcion if desbloqueado else f"Completá {n.nombre} para desbloquear.")
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet("color: #9CA3AF;")
            v.addWidget(lbl_e)
            v.addWidget(lbl_t)
            v.addWidget(lbl_d)
            self.grilla.addWidget(card, 0, idx)

        if self.progreso.balon_de_oro_desbloqueado:
            self.lbl_balon_titulo.setText("★ BALÓN DE ORO DESBLOQUEADO ★")
            self.lbl_balon_titulo.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FBBF24;")
            self.lbl_balon_desc.setText("¡Completaste los 4 partidos históricos de la carrera de Messi!")
        else:
            self.lbl_balon_titulo.setText("BALÓN DE ORO (Bloqueado)")
            self.lbl_balon_titulo.setStyleSheet("font-size: 14pt; font-weight: bold; color: #9CA3AF;")
            self.lbl_balon_desc.setText("Se desbloquea automáticamente al completar los 4 niveles.")

    def _confirmar_borrado(self) -> None:
        resp = QMessageBox.question(
            self,
            "Borrar progreso",
            "¿Seguro que querés reiniciar todos los trofeos y el progreso a 0/4?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.progreso.reiniciar()
            self.actualizar_vitrina()
            self.progreso_borrado.emit()