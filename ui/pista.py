from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout


class DialogoPista(QDialog):
    def __init__(self, nivel, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Pista 💡 · {nivel.nombre}")
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Código resuelto de {nivel.nombre}. Copialo en el editor para probarlo."))
        aviso = QLabel("Pista consultada: los nuevos intentos de este nivel podrán ganar Plata o Bronce. Tu mejor medalla anterior se conserva.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #FBBF24;")
        layout.addWidget(aviso)

        self.codigo = QPlainTextEdit()
        self.codigo.setReadOnly(True)
        self.codigo.setFont(QFont("Cascadia Code", 11))
        self.codigo.setPlainText(nivel.codigo_inicial)
        layout.addWidget(self.codigo, 1)

        botones = QHBoxLayout()
        self.btn_copiar = QPushButton("Copiar código")
        self.btn_copiar.setObjectName("btnPrimario")
        self.btn_copiar.clicked.connect(self.copiar_codigo)
        botones.addWidget(self.btn_copiar)
        botones.addStretch()
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        botones.addWidget(cerrar)
        layout.addLayout(botones)

    def copiar_codigo(self):
        QApplication.clipboard().setText(self.codigo.toPlainText())
        self.btn_copiar.setText("Copiado ✓")
