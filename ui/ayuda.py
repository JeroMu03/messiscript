from PySide6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout
from juego.motor import reglas_tacticas


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
  <li><b>POSICIONAR JUGADOR X Y:</b> Ubica a un compañero de Messi en la celda (X, Y). En los niveles estándar permite incorporar compañeros; si ya está en cancha, se desplaza con una animación. En las pruebas tácticas de México, Croacia, la Final e Inglaterra, el equipo ya está ubicado y solo podés reposicionar a los jugadores clave indicados en Ayuda / Entorno. X va de 0 a 29 e Y de 0 a 19. Messi no puede reposicionarse con esta sentencia; usá MOVER para conducir la pelota.</li>
  <li><b>PASE JUGADOR:</b> Envía la pelota a un compañero del escenario. <b>El control pasa al receptor</b>.</li>
  <li><b>REMATAR:</b> Patea al arco desde el jugador que tiene la pelota (debe estar cerca del arco y sin rivales bloqueando la línea).</li>
</ul>
<h3>Zonas, desafío y medallas</h3>
<ul>
  <li>Antes de ejecutar, hacé clic en una ficha del cajón o la cancha para iluminar sus cuatro casillas válidas. En Inglaterra también podés seleccionar a Messi para ver la zona del centro.</li>
  <li><b>Modo desafío:</b> oculta puntos, zonas, flechas de intención y pistas del escenario. Pista queda deshabilitada; Ayuda conserva solo la sintaxis general. Cambiar de modo reinicia la cancha.</li>
  <li><b>Medallas:</b> Oro al completar sin consultar Pista en ese nivel; Plata al completar con Pista dentro de la meta de acciones indicada; Bronce al completar con más acciones. Las repeticiones se cuentan como acciones expandidas. Siempre se conserva tu mejor medalla y, en empate, tu menor cantidad de acciones.</li>
  <li>El registro de Pistas consultadas se conserva al cambiar de nivel o cerrar el juego. Reiniciar progreso borra ese registro y las medallas. Los trofeos de versiones anteriores se conservan con Bronce y se pueden mejorar.</li>
  <li><b>Repetir jugada:</b> reproduce el último intento del nivel sin recompilar el editor ni modificar premios. Al cambiar de nivel se descarta la repetición anterior.</li>
  <li>Al fallar, se resalta al defensor responsable y se muestra un consejo. Reiniciar vuelve a mostrar las ayudas del modo elegido.</li>
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

    instrucciones = ("Solo Messi y los rivales están en la cancha al iniciar. Usá "
                     "<code>POSICIONAR JUGADOR X Y</code> para incorporar a un compañero. "
                     "Las posiciones de referencia son una ayuda; podés elegir otra celda libre.")
    if nivel.tactica:
        instrucciones = "<b>Prueba táctica:</b> el plantel empieza ubicado. Podés reposicionar a los jugadores clave; los demás mantienen su ubicación. "
        for regla in reglas_tacticas(nivel):
            clave, marcador = regla["jugador_clave"], regla["marcador"]
            x0, y0, x1, y1 = regla["zona_arrastre"]
            x, y = regla["ejemplo"]
            efecto = (f"atrae a {marcador} y libera a {regla['protegido']}" if regla["tipo"] == "arrastre" else
                      f"escapa de {marcador} para recibir; si no se adelanta, {marcador} le roba la pelota al recibir el pase")
            instrucciones += (
                f"<br><b>{clave}:</b> {efecto}. Zona 2×2: X entre {x0} y {x1}, Y entre {y0} y {y1}. "
                "Cualquiera de esas cuatro casillas sirve para resolver el desmarque. "
                f"Ejemplo: <code>POSICIONAR {clave} {x} {y}</code>; no hace falta usar exactamente ese punto. "
            )
        instrucciones += "<br>Rosa: amenaza de robo; celeste: movimiento animado; dorado: marca atraída; verde: receptor libre. "
        if "receptor_habilitado" in nivel.tactica:
            instrucciones += (f"El pase habilitado es <code>PASE {nivel.tactica['receptor_habilitado']}</code>. "
                              + nivel.tactica.get("indicacion_final", "Subí una celda y avanzá dos hacia la derecha, repetí para esquivar a GVARDIOL, asistí a Julián y rematá."))
        else:
            instrucciones += "Liberá la marca antes de conducir, pasar o rematar. Después podés usar <code>MOVER DERECHA 4</code> y <code>REMATAR</code>."

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
    <p>{instrucciones}</p>
    <ul>{jugadores}</ul>
    <h4>Rivales (posiciones iniciales)</h4>
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
