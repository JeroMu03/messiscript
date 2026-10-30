from PySide6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout


TEXTO_AYUDA = """
<h2>Guía Rápida de MessiScript v2</h2>
<p><b>Estructura de un programa:</b></p>
<pre>
INICIAR INGLATERRA_2026
VAR PASOS = 2
REPETIR 1 {
    MOVER DERECHA PASOS
    MOVER ARRIBA 1
}
PASE LAUTARO
REMATAR
FIN
</pre>
<h3>Reglas del Lenguaje y del Motor</h3>
<ul>
  <li><b> sensibilidad a mayúsculas:</b> Todos los comandos y nombres van en MAYÚSCULAS.</li>
  <li><b>VAR NOMBRE = N:</b> Declara constantes enteras al principio del programa (después de INICIAR).</li>
  <li><b>MOVER [DERECHA|IZQUIERDA|ARRIBA|ABAJO] N:</b> Mueve al jugador con la pelota (1 a 20 pasos).</li>
  <li><b>REPETIR N { ... }:</b> Repite un bloque de instrucciones (1 a 10 veces).</li>
  <li><b>PASE JUGADOR:</b> Envía la pelota a un compañero del escenario. <b>El control pasa al receptor</b>.</li>
  <li><b>REMATAR:</b> Patea al arco desde el jugador que tiene la pelota (debe estar cerca del arco y sin rivales bloqueando la línea).</li>
</ul>
<h3>Atajos de Teclado</h3>
<ul>
  <li><b>F5 / Ctrl+Enter:</b> Analizar y ejecutar jugada</li>
  <li><b>Espacio:</b> Pausar / Reanudar animación</li>
  <li><b>R:</b> Reiniciar cancha al estado inicial</li>
  <li><b>Ctrl+1:</b> Ir a Niveles | <b>Ctrl+2:</b> Ir a Trofeos | <b>F1:</b> Ayuda</li>
</ul>
"""


class DialogoAyuda(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayuda · Sintaxis y Reglas de MessiScript")
        self.resize(620, 480)
        layout = QVBoxLayout(self)
        visor = QTextEdit()
        visor.setReadOnly(True)
        visor.setHtml(TEXTO_AYUDA)
        layout.addWidget(visor)
        btn = QPushButton("Cerrar")
        btn.setObjectName("btnPrimario")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)