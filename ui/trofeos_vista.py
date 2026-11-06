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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from juego.modelos import Nivel
from juego.progreso import GestorProgreso
from .trofeos_pixel import TarjetaTrofeoPixel


class PaginaTrofeos(QWidget):
    progreso_borrado = Signal()

    def __init__(self, niveles: List[Nivel], progreso: GestorProgreso, parent=None):
        super().__init__(parent)
        self.niveles = niveles
        self.progreso = progreso

        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        contenido = QWidget()
        scroll.setWidget(contenido)
        exterior.addWidget(scroll)
        layout = QVBoxLayout(contenido)
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
        reglas = QLabel("Medallas: Oro sin consultar Pista · Plata con pocas acciones · Bronce por completar. Se conserva tu mejor medalla por nivel.")
        reglas.setWordWrap(True)
        reglas.setStyleSheet("color: #94A3B8;")
        layout.addWidget(reglas)

        titulo_especiales = QLabel("COLECCIÓN DE TROFEOS · 8 BITS")
        titulo_especiales.setStyleSheet("font-size: 12pt; font-weight: bold; color: #7DD3FC;")
        layout.addWidget(titulo_especiales)
        especiales = QHBoxLayout()
        self.trofeos_especiales = {
            "FINAL_2022": TarjetaTrofeoPixel("copa", "Copa del Mundo 2022", "Ganá la Final 2022 para desbloquearla."),
            "INGLATERRA_2026": TarjetaTrofeoPixel("islas", "Islas Malvinas", "Ganá la semifinal de Inglaterra 2026 para desbloquearlas."),
        }
        for tarjeta in self.trofeos_especiales.values():
            especiales.addWidget(tarjeta, 1)
        layout.addLayout(especiales)

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
        for nivel_id, tarjeta in self.trofeos_especiales.items():
            tarjeta.actualizar(self.progreso.esta_completado(nivel_id))
        while self.grilla.count():
            it = self.grilla.takeAt(0)
            if it.widget():
                it.widget().hide()
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
            lbl_medalla = QLabel(self.progreso.texto_medalla(n.id))
            lbl_medalla.setWordWrap(True)
            lbl_medalla.setStyleSheet("color: #7DD3FC; font-weight: bold;")
            v.addWidget(lbl_medalla)
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
            "¿Seguro que querés reiniciar todos los trofeos, medallas y el progreso a 0/4? También se borra el registro de pistas consultadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self.progreso.reiniciar()
            self.actualizar_vitrina()
            self.progreso_borrado.emit()
