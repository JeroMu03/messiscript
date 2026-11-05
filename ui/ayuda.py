from PySide6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout


TEXTO_AYUDA = """
<h2>Guía Rápida de MessiScript v2</h2>
<p><b>Estructura de un programa:</b></p>
<pre>
INICIAR ESCENARIO
VAR PASOS = 2
POSICIONAR COMPANERO 25 10
REPETIR 2 {
    MOVER DERECHA PASOS
    MOVER ARRIBA 1
}
PASE COMPANERO
REMATAR
FIN
</pre>
<h3>Reglas del Lenguaje y del Motor</h3>
<ul>
  <li><b>Sensibilidad a mayúsculas:</b> Todos los comandos y nombres van en MAYÚSCULAS.</li>
  <li><b>VAR NOMBRE = N:</b> Declara constantes enteras al principio del programa (después de INICIAR).</li>
  <li><b>MOVER [DERECHA|IZQUIERDA|ARRIBA|ABAJO] N:</b> Mueve al jugador con la pelota (1 a 20 pasos).</li>
  <li><b>REPETIR N { ... }:</b> Repite un bloque de instrucciones (1 a 10 veces).</li>
  <li><b>POSICIONAR JUGADOR X Y:</b> Ubica a un compañero de Messi en la celda (X, Y). Al iniciar solo están Messi y los rivales en la cancha; usá esta sentencia para incorporar compañeros. X va de 0 a 29 e Y de 0 a 19. Messi ya tiene posición fija y no puede reposicionarse.</li>
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


def _html_entorno(nivel) -> str:
    if nivel is None:
        return ""

    def nombre(jugador: str) -> str:
        return nivel.nombres.get(jugador, jugador.replace("_", " ").title())

    def posicion(p) -> str:
        return f"({p[0]}, {p[1]})"

    jugadores = "".join(
        f"<li><b>{nombre(jugador)}</b> — <code>{jugador}</code> — "
        f"posición de referencia {posicion(nivel.inicio[jugador])}</li>"
        for jugador in nivel.jugadores
        if jugador in nivel.inicio
    )
    rivales = "".join(
        f"<li><b>{nombre(rival)}</b> — <code>{rival}</code> — {posicion(pos)}</li>"
        for rival, pos in nivel.rivales.items()
    )

    objetivo = nivel.objetivo
    detalles = [objetivo.tipo]
    if objetivo.asistente:
        detalles.append(f"asistente {nombre(objetivo.asistente)}")
    if objetivo.rematador:
        detalles.append(f"rematador {nombre(objetivo.rematador)}")
    if objetivo.receptor:
        detalles.append(f"receptor {nombre(objetivo.receptor)}")
    detalles.append(f"máximo {objetivo.max_acciones} acciones")

    return f"""
    <hr>
    <h3>Entorno del escenario: {nivel.escenario}</h3>
    <ul>
      <li><b>Nivel:</b> {nivel.nombre}</li>
      <li><b>Objetivo:</b> {', '.join(detalles)}</li>
      <li><b>Pelota inicial:</b> {nombre(nivel.pelota)}</li>
      <li><b>Arco rival:</b> X={nivel.arco_x}, Y={nivel.arco_y}..{nivel.arco_y + nivel.arco_alto - 1}</li>
      <li><b>Límites de coordenadas:</b> X de 0 a {nivel.columnas - 1}, Y de 0 a {nivel.filas - 1}</li>
    </ul>
    <h4>Jugadores del escenario</h4>
    <p>Solo Messi y los rivales están en la cancha al iniciar. Usá
    <code>POSICIONAR JUGADOR X Y</code> para incorporar a un compañero. Las
    posiciones de referencia son una ayuda; podés elegir otra celda libre.</p>
    <ul>{jugadores}</ul>
    <h4>Rivales fijos</h4>
    <ul>{rivales}</ul>
    """


class DialogoAyuda(QDialog):
    def __init__(self, parent=None, nivel=None):
        super().__init__(parent)
        self.setWindowTitle("Ayuda · Sintaxis y Reglas de MessiScript")
        self.resize(620, 480)
        layout = QVBoxLayout(self)
        visor = QTextEdit()
        visor.setReadOnly(True)
        visor.setHtml(TEXTO_AYUDA + _html_entorno(nivel))
        layout.addWidget(visor)
        btn = QPushButton("Cerrar")
        btn.setObjectName("btnPrimario")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
