from typing import List
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from juego.modelos import Nivel
from juego.progreso import GestorProgreso


class PaginaNiveles(QWidget):
    nivel_seleccionado = Signal(str)

    def __init__(self, niveles: List[Nivel], progreso: GestorProgreso, parent=None):
        super().__init__(parent)
        self.niveles = niveles
        self.progreso = progreso

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        cab = QHBoxLayout()
        titulo = QLabel("MODO CARRERA · SELECCIÓN DE PARTIDO")
        titulo.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.lbl_progreso = QLabel()
        self.lbl_progreso.setStyleSheet("font-size: 12pt; color: #FBBF24; font-weight: bold;")
        cab.addWidget(titulo)
        cab.addStretch()
        cab.addWidget(self.lbl_progreso)
        layout.addLayout(cab)

        self.barra = QProgressBar()
        self.barra.setRange(0, len(niveles))
        layout.addWidget(self.barra)

        self.grilla = QGridLayout()
        self.grilla.setSpacing(16)
        layout.addLayout(self.grilla)
        layout.addStretch()

        nota = QLabel("Todos los niveles están desbloqueados desde el inicio para facilitar la demostración.")
        nota.setStyleSheet("color: #9CA3AF;")
        layout.addWidget(nota)

        self.actualizar_tarjetas()

    def actualizar_tarjetas(self) -> None:
        while self.grilla.count():
            item = self.grilla.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        comp = self.progreso.cantidad_completados
        total = len(self.niveles)
        self.lbl_progreso.setText(f"Progreso: {comp}/{total}")
        self.barra.setValue(comp)

        for idx, n in enumerate(self.niveles):
            card = QFrame()
            card.setObjectName("tarjeta")
            v = QVBoxLayout(card)
            v.setContentsMargins(16, 16, 16, 16)
            v.setSpacing(8)

            ganado = self.progreso.esta_completado(n.id)
            estado_txt = "COMPLETADO" if ganado else "PENDIENTE"
            color_est = "#22C55E" if ganado else "#9CA3AF"

            lbl_est = QLabel(estado_txt)
            lbl_est.setStyleSheet(f"color: {color_est}; font-weight: bold;")
            lbl_nom = QLabel(f"{n.nombre} · {n.subtitulo}")
            lbl_nom.setStyleSheet("font-size: 13pt; font-weight: bold;")
            lbl_desc = QLabel(n.descripcion)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #9CA3AF;")
            lbl_trof = QLabel(f"Trofeo: {n.trofeo.nombre}")
            lbl_trof.setStyleSheet("color: #FBBF24; font-weight: 600;")

            btn = QPushButton("Rejugar" if ganado else "Jugar")
            btn.setObjectName("btnPrimario")
            btn.clicked.connect(lambda _=False, nid=n.id: self.nivel_seleccionado.emit(nid))

            v.addWidget(lbl_est)
            v.addWidget(lbl_nom)
            v.addWidget(lbl_desc)
            v.addWidget(lbl_trof)
            v.addStretch()
            v.addWidget(btn)

            self.grilla.addWidget(card, idx // 2, idx % 2)