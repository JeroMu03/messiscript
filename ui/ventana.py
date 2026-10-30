from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from juego.modelos import EstadoReproduccion, Nivel, Resultado
from juego.motor import simular
from juego.niveles import cargar_niveles, construir_escenarios, obtener_nivel
from juego.progreso import GestorProgreso
from messiscript import analizar

from .ayuda import DialogoAyuda
from .cancha import CanchaWidget
from .editor import EditorWidget
from .niveles_vista import PaginaNiveles
from .paneles import PanelesInferiores
from .trofeos_vista import PaginaTrofeos


class VentanaPrincipal(QMainWindow):
    def __init__(self, ruta_progreso=None):
        super().__init__()
        self.setWindowTitle("MessiScript v2 · Modo Carrera")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 700)

        self.niveles = cargar_niveles()
        self.escenarios = construir_escenarios(self.niveles)
        self.progreso = GestorProgreso(ruta_progreso)
        self.nivel_actual: Nivel = self.niveles[0]
        self.estado_rep = EstadoReproduccion.INICIAL

        self._cargar_estilos()
        self._construir_ui()
        self._configurar_atajos()
        self.seleccionar_nivel(self.niveles[0].id, ir_a_jugar=False)

    def _cargar_estilos(self) -> None:
        ruta_qss = Path(__file__).resolve().parent / "estilos.qss"
        if ruta_qss.exists():
            self.setStyleSheet(ruta_qss.read_text(encoding="utf-8"))

    def _construir_ui(self) -> None:
        # Toolbar superior
        tb = QToolBar("Navegación")
        tb.setMovable(False)
        self.addToolBar(tb)

        lbl_logo = QLabel("  ⚽ MessiScript · Carrera   ")
        lbl_logo.setStyleSheet("font-size: 12pt; font-weight: bold; color: #75AADB;")
        tb.addWidget(lbl_logo)

        btn_niveles = QPushButton("Niveles (Ctrl+1)")
        btn_niveles.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_jugar = QPushButton("Cancha / Editor")
        btn_jugar.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_trofeos = QPushButton("Trofeos (Ctrl+2)")
        btn_trofeos.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_ayuda = QPushButton("Ayuda (F1)")
        btn_ayuda.clicked.connect(self.mostrar_ayuda)

        tb.addWidget(btn_niveles)
        tb.addWidget(btn_jugar)
        tb.addWidget(btn_trofeos)
        tb.addWidget(btn_ayuda)

        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred
        )
        tb.addWidget(spacer)

        self.lbl_top_trofeos = QLabel()
        self.lbl_top_trofeos.setStyleSheet("font-weight: bold; color: #FBBF24; padding-right: 12px;")
        tb.addWidget(self.lbl_top_trofeos)

        # Stack central
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.pagina_niveles = PaginaNiveles(self.niveles, self.progreso)
        self.pagina_niveles.nivel_seleccionado.connect(
            lambda nid: self.seleccionar_nivel(nid, ir_a_jugar=True)
        )

        self.pagina_juego = self._crear_pagina_juego()

        self.pagina_trofeos = PaginaTrofeos(self.niveles, self.progreso)
        self.pagina_trofeos.progreso_borrado.connect(self._refrescar_progreso_global)

        self.stack.addWidget(self.pagina_niveles)
        self.stack.addWidget(self.pagina_juego)
        self.stack.addWidget(self.pagina_trofeos)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._refrescar_progreso_global()

    def _crear_pagina_juego(self) -> QWidget:
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(10)

        # Encabezado del nivel
        cab = QHBoxLayout()
        self.lbl_titulo_nivel = QLabel()
        self.lbl_titulo_nivel.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.lbl_objetivo_nivel = QLabel()
        self.lbl_objetivo_nivel.setStyleSheet("color: #75AADB; font-weight: 600;")
        cab.addWidget(self.lbl_titulo_nivel)
        cab.addStretch()
        cab.addWidget(self.lbl_objetivo_nivel)
        v.addLayout(cab)

        splitter_vert = QSplitter(Qt.Orientation.Vertical)
        splitter_horiz = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo: Editor
        panel_ed = QWidget()
        v_ed = QVBoxLayout(panel_ed)
        v_ed.setContentsMargins(0, 0, 0, 0)
        self.editor = EditorWidget()
        v_ed.addWidget(self.editor)

        botones_ed = QHBoxLayout()
        self.btn_ejecutar = QPushButton("▶ Ejecutar (F5)")
        self.btn_ejecutar.setObjectName("btnPrimario")
        self.btn_ejecutar.clicked.connect(self.ejecutar_jugada)

        btn_restaurar = QPushButton("Restaurar ejemplo")
        btn_restaurar.clicked.connect(self.restaurar_codigo_inicial)

        botones_ed.addWidget(self.btn_ejecutar)
        botones_ed.addWidget(btn_restaurar)
        botones_ed.addStretch()
        v_ed.addLayout(botones_ed)

        # Panel derecho: Cancha + controles
        panel_can = QWidget()
        v_can = QVBoxLayout(panel_can)
        v_can.setContentsMargins(0, 0, 0, 0)
        self.cancha = CanchaWidget()
        self.cancha.frame_cambiado.connect(self._al_cambiar_frame)
        self.cancha.reproduccion_finalizada.connect(self._al_terminar_reproduccion)
        v_can.addWidget(self.cancha, 1)

        controles_can = QHBoxLayout()
        self.btn_pausa = QPushButton("⏸ Pausar / Reanudar (Espacio)")
        self.btn_pausa.clicked.connect(self.alternar_pausa)
        btn_reiniciar = QPushButton("↺ Reiniciar (R)")
        btn_reiniciar.clicked.connect(self.reiniciar_simulacion)

        lbl_vel = QLabel("Velocidad:")
        self.combo_vel = QComboBox()
        self.combo_vel.addItems(["0.5x", "1x", "2x"])
        self.combo_vel.setCurrentText("1x")
        self.combo_vel.currentTextChanged.connect(self._cambiar_velocidad)

        self.lbl_accion_actual = QLabel("Acción 0/0")
        self.lbl_accion_actual.setStyleSheet("color: #9CA3AF; font-weight: 600;")

        controles_can.addWidget(self.btn_pausa)
        controles_can.addWidget(btn_reiniciar)
        controles_can.addWidget(lbl_vel)
        controles_can.addWidget(self.combo_vel)
        controles_can.addStretch()
        controles_can.addWidget(self.lbl_accion_actual)
        v_can.addLayout(controles_can)

        splitter_horiz.addWidget(panel_ed)
        splitter_horiz.addWidget(panel_can)
        splitter_horiz.setSizes([340, 920])

        self.paneles = PanelesInferiores()
        self.paneles.error_seleccionado.connect(self.editor.ir_a_posicion)

        splitter_vert.addWidget(splitter_horiz)
        splitter_vert.addWidget(self.paneles)
        splitter_vert.setSizes([580, 160])

        v.addWidget(splitter_vert)
        return contenedor

    def _configurar_atajos(self) -> None:
        QShortcut(QKeySequence("F5"), self, activated=self.ejecutar_jugada)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.ejecutar_jugada)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.stack.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.stack.setCurrentIndex(2))
        QShortcut(QKeySequence("F1"), self, activated=self.mostrar_ayuda)

    def seleccionar_nivel(self, nivel_id: str, ir_a_jugar: bool = True) -> None:
        self.nivel_actual = obtener_nivel(nivel_id, self.niveles)
        self.lbl_titulo_nivel.setText(f"{self.nivel_actual.nombre} · {self.nivel_actual.subtitulo}")
        self.lbl_objetivo_nivel.setText(f"Objetivo: {self.nivel_actual.pista}")
        self.editor.setPlainText(self.nivel_actual.codigo_inicial)
        self.editor.limpiar_errores()
        self.cancha.cargar_nivel(self.nivel_actual)
        self.lbl_accion_actual.setText("Acción 0/0 · Listo")
        self.estado_rep = EstadoReproduccion.INICIAL
        self._actualizar_statusbar("Listo para ejecutar.")
        if ir_a_jugar:
            self.stack.setCurrentIndex(1)

    def restaurar_codigo_inicial(self) -> None:
        self.editor.setPlainText(self.nivel_actual.codigo_inicial)
        self.editor.limpiar_errores()
        self.reiniciar_simulacion()

    def ejecutar_jugada(self) -> None:
        self.stack.setCurrentIndex(1)
        self.estado_rep = EstadoReproduccion.ANALIZANDO
        codigo = self.editor.toPlainText()
        res = analizar(codigo, escenarios=self.escenarios)
        self.paneles.cargar_resultado_analisis(res)

        if not res.get("valido", False):
            self.estado_rep = EstadoReproduccion.ERROR
            errores = res.get("errores", [])
            self.editor.marcar_errores(errores)
            if errores:
                primero = errores[0]
                self.editor.ir_a_posicion(int(primero.get("linea", 1)), int(primero.get("columna", 1)))
            self._actualizar_statusbar(f"Error de compilación ({len(errores)} errores).")
            return

        # Validar que el escenario del código coincida con el nivel abierto
        esc_codigo = res.get("escenario")
        if esc_codigo != self.nivel_actual.escenario:
            err_esc = [{
                "tipo": "semantico",
                "linea": 1,
                "columna": 1,
                "mensaje": f"Este nivel espera INICIAR {self.nivel_actual.escenario} (se usó {esc_codigo}).",
            }]
            self.editor.marcar_errores(err_esc)
            self.paneles.cargar_resultado_analisis({"valido": False, "errores": err_esc, "acciones": []})
            self.estado_rep = EstadoReproduccion.ERROR
            self._actualizar_statusbar(f"Escenario incorrecto: se esperaba {self.nivel_actual.escenario}.")
            return

        self.editor.limpiar_errores()
        acciones = res.get("acciones", [])
        simulacion = simular(acciones, self.nivel_actual)
        self.estado_rep = EstadoReproduccion.REPRODUCIENDO
        self._actualizar_statusbar(f"Reproduciendo {len(acciones)} acciones...")
        self.cancha.iniciar_reproduccion(simulacion, len(acciones))

    def alternar_pausa(self) -> None:
        activo = self.cancha.pausar_o_reanudar()
        self.estado_rep = EstadoReproduccion.REPRODUCIENDO if activo else EstadoReproduccion.PAUSADO
        self._actualizar_statusbar("Reproduciendo..." if activo else "Pausado.")

    def reiniciar_simulacion(self) -> None:
        self.cancha.reiniciar()
        self.estado_rep = EstadoReproduccion.INICIAL
        self.lbl_accion_actual.setText("Acción 0/0 · Reiniciado")
        self._actualizar_statusbar("Cancha reiniciada al estado inicial.")

    def _cambiar_velocidad(self, texto: str) -> None:
        mult = float(texto.replace("x", ""))
        self.cancha.cambiar_velocidad(mult)
        self._actualizar_statusbar(f"Velocidad ajustada a {texto}.")

    def _al_cambiar_frame(self, idx_acc: int, total_acc: int, texto_acc: str) -> None:
        self.lbl_accion_actual.setText(f"Acción {idx_acc}/{total_acc} · {texto_acc}")
        self.paneles.resaltar_accion(idx_acc)

    def _al_terminar_reproduccion(self, resultado: Resultado) -> None:
        if resultado.exito:
            self.estado_rep = EstadoReproduccion.EXITO
            self.progreso.registrar_victoria(self.nivel_actual.id)
            self._refrescar_progreso_global()
            self._actualizar_statusbar(f"¡ÉXITO! {resultado.motivo} — Trofeo: {self.nivel_actual.trofeo.nombre}")
            QMessageBox.information(
                self,
                "¡Objetivo Cumplido!",
                f"{resultado.motivo}\n\n🏆 Trofeo desbloqueado: {self.nivel_actual.trofeo.nombre}\n{self.nivel_actual.trofeo.descripcion}",
            )
        else:
            self.estado_rep = EstadoReproduccion.FALLO
            self._actualizar_statusbar(f"Jugada fallida: {resultado.motivo}")

    def _refrescar_progreso_global(self) -> None:
        comp = self.progreso.cantidad_completados
        total = len(self.niveles)
        self.lbl_top_trofeos.setText(f"{comp}/{total} 🏆")
        self.pagina_niveles.actualizar_tarjetas()
        self.pagina_trofeos.actualizar_vitrina()

    def _actualizar_statusbar(self, msg: str) -> None:
        self.status.showMessage(f"[{self.estado_rep.value}] Nivel: {self.nivel_actual.nombre}  |  {msg}")

    def mostrar_ayuda(self) -> None:
        dlg = DialogoAyuda(self)
        dlg.exec()