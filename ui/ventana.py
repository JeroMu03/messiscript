from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QApplication,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QMainWindow,
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
from juego.progreso import GestorProgreso, calcular_medalla
from messiscript import analizar

from .musica import MusicaFondo, SonidoGol
from .ayuda import DialogoAyuda
from .cancha import CanchaWidget
from .editor import EditorWidget
from .niveles_vista import PaginaNiveles
from .paneles import PanelesInferiores
from .pista import DialogoPista
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
        self.modo_desafio = False
        self.ultimo_intento = None
        self._intento_en_curso = None
        self._es_repeticion = False
        self.metas_acciones = {n.id: len(analizar(n.codigo_inicial, escenarios=self.escenarios)["acciones"]) for n in self.niveles}
        self.estado_rep = EstadoReproduccion.INICIAL
        self.musica = MusicaFondo()
        self.sonido_gol = SonidoGol()

        self._cargar_estilos()
        self._construir_ui()
        self._configurar_atajos()
        self.seleccionar_nivel(self.niveles[0].id, ir_a_jugar=False)
        if not self.musica.iniciar():
            self.btn_musica.setEnabled(False)
            self.btn_musica.setText("Música: no disponible")
            self.btn_musica.setToolTip(self.musica.error)
        QApplication.instance().aboutToQuit.connect(self.musica.detener)
        QApplication.instance().aboutToQuit.connect(self.sonido_gol.detener)

    def closeEvent(self, event):
        self.musica.detener()
        self.sonido_gol.detener()
        super().closeEvent(event)

    def _reproducir_sonido_gol(self):
        self.sonido_gol.reproducir()

    def _al_reiniciar_progreso(self):
        self.reiniciar_simulacion()
        self.sonido_gol.detener()
        self.ultimo_intento = None
        self.btn_repetir.setEnabled(False)
        self._refrescar_progreso_global()
        self._actualizar_statusbar("Progreso reiniciado a 0/4.")

    def alternar_musica(self, silenciada):
        if self.musica.silenciar(silenciada):
            self.btn_musica.setText("Música: silenciada" if silenciada else "Música: activada")
        else:
            self.btn_musica.setChecked(self.musica.silenciada)
            self.status.showMessage(f"No se pudo cambiar el volumen: {self.musica.error}")

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

        self.btn_musica = QPushButton("Música: activada")
        self.btn_musica.setCheckable(True)
        self.btn_musica.setToolTip("Silenciar o activar Muchachos (8 bit), en bucle")
        self.btn_musica.toggled.connect(self.alternar_musica)
        tb.addWidget(self.btn_musica)

        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred
        )
        tb.addWidget(spacer)

        self.lbl_top_trofeos = QLabel()
        self.lbl_top_trofeos.setStyleSheet("font-weight: bold; color: #FBBF24; padding-right: 12px;")
        tb.addWidget(self.lbl_top_trofeos)
        self.btn_reiniciar_progreso = QPushButton("Reiniciar progreso")
        self.btn_reiniciar_progreso.setToolTip("Volver a 0/4 niveles y bloquear todos los premios")
        self.btn_reiniciar_progreso.clicked.connect(lambda: self.pagina_trofeos._confirmar_borrado())
        tb.addWidget(self.btn_reiniciar_progreso)

        # Stack central
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.pagina_niveles = PaginaNiveles(self.niveles, self.progreso)
        self.pagina_niveles.nivel_seleccionado.connect(
            lambda nid: self.seleccionar_nivel(nid, ir_a_jugar=True)
        )

        self.pagina_juego = self._crear_pagina_juego()

        self.pagina_trofeos = PaginaTrofeos(self.niveles, self.progreso)
        self.pagina_trofeos.progreso_borrado.connect(self._al_reiniciar_progreso)

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
        cab = QVBoxLayout()
        titulo = QHBoxLayout()
        self.lbl_titulo_nivel = QLabel()
        self.lbl_titulo_nivel.setStyleSheet("font-size: 13pt; font-weight: bold;")
        self.lbl_objetivo_nivel = QLabel()
        self.lbl_objetivo_nivel.setWordWrap(True)
        self.lbl_objetivo_nivel.setStyleSheet("color: #75AADB; font-weight: 600;")
        titulo.addWidget(self.lbl_titulo_nivel)
        titulo.addStretch()
        self.btn_desafio = QPushButton("Modo desafío")
        self.btn_desafio.setCheckable(True)
        self.btn_desafio.setToolTip("Oculta zonas, puntos, flechas de intención, pistas y ayuda del escenario")
        self.btn_desafio.toggled.connect(self.cambiar_modo_desafio)
        titulo.addWidget(self.btn_desafio)
        cab.addLayout(titulo)
        cab.addWidget(self.lbl_objetivo_nivel)
        self.lbl_medallas = QLabel()
        self.lbl_medallas.setWordWrap(True)
        self.lbl_medallas.setStyleSheet("color: #94A3B8;")
        cab.addWidget(self.lbl_medallas)
        v.addLayout(cab)

        splitter_vert = QSplitter(Qt.Orientation.Vertical)
        splitter_horiz = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo: Editor
        panel_ed = QWidget()
        v_ed = QVBoxLayout(panel_ed)
        v_ed.setContentsMargins(0, 0, 0, 0)
        self.lbl_ayuda_fichas = QLabel()
        self.lbl_ayuda_fichas.setWordWrap(True)
        self.lbl_ayuda_fichas.setStyleSheet("background: #0C2538; color: #7DD3FC; font-weight: bold; padding: 8px; border: 1px solid #38BDF8; border-radius: 6px;")
        v_ed.addWidget(self.lbl_ayuda_fichas)
        self.editor = EditorWidget()
        v_ed.addWidget(self.editor)

        botones_ed = QGridLayout()
        self.btn_ejecutar = QPushButton("▶ Ejecutar (F5)")
        self.btn_ejecutar.setObjectName("btnPrimario")
        self.btn_ejecutar.clicked.connect(self.ejecutar_jugada)

        self.btn_ayuda_nivel = QPushButton("❓ Ayuda / Entorno")
        self.btn_ayuda_nivel.setToolTip("Ver jugadores, rivales y coordenadas del escenario actual")
        self.btn_ayuda_nivel.clicked.connect(self.mostrar_ayuda)

        self.btn_pista = QPushButton("Pista 💡")
        self.btn_pista.setToolTip("Ver y copiar el código resuelto del nivel actual")
        self.btn_pista.clicked.connect(self.mostrar_pista)

        btn_plantilla = QPushButton("Nueva plantilla")
        btn_plantilla.clicked.connect(self.restaurar_plantilla)

        botones_ed.addWidget(self.btn_ejecutar, 0, 0)
        botones_ed.addWidget(self.btn_ayuda_nivel, 0, 1)
        botones_ed.addWidget(self.btn_pista, 1, 0)
        botones_ed.addWidget(btn_plantilla, 1, 1)
        v_ed.addLayout(botones_ed)

        # Panel derecho: Cancha + controles
        panel_can = QWidget()
        v_can = QVBoxLayout(panel_can)
        v_can.setContentsMargins(0, 0, 0, 0)
        self.cancha = CanchaWidget()
        self.cancha.frame_cambiado.connect(self._al_cambiar_frame)
        self.cancha.reproduccion_finalizada.connect(self._al_terminar_reproduccion)
        self.cancha.gol_marcado.connect(self._reproducir_sonido_gol)
        v_can.addWidget(self.cancha, 1)

        controles_can = QGridLayout()
        self.btn_pausa = QPushButton("⏸ Pausar / Reanudar (Espacio)")
        self.btn_pausa.clicked.connect(self.alternar_pausa)
        btn_reiniciar = QPushButton("↺ Reiniciar (R)")
        btn_reiniciar.clicked.connect(self.reiniciar_simulacion)
        self.btn_repetir = QPushButton("↻ Repetir jugada")
        self.btn_repetir.setEnabled(False)
        self.btn_repetir.setToolTip("Reproduce el último intento sin recompilar ni sumar premios")
        self.btn_repetir.clicked.connect(self.repetir_jugada)

        lbl_vel = QLabel("Velocidad:")
        self.combo_vel = QComboBox()
        self.combo_vel.addItems(["0.5x", "1x", "2x"])
        self.combo_vel.setCurrentText("1x")
        self.combo_vel.currentTextChanged.connect(self._cambiar_velocidad)

        self.lbl_accion_actual = QLabel("Acción 0/0")
        self.lbl_accion_actual.setStyleSheet("color: #9CA3AF; font-weight: 600;")

        controles_can.addWidget(self.btn_pausa, 0, 0, 1, 2)
        controles_can.addWidget(self.btn_repetir, 0, 2)
        controles_can.addWidget(btn_reiniciar, 0, 3)
        controles_can.addWidget(lbl_vel, 1, 0)
        controles_can.addWidget(self.combo_vel, 1, 1)
        controles_can.addWidget(self.lbl_accion_actual, 1, 2, 1, 2)
        v_can.addLayout(controles_can)
        self.lbl_fallo = QLabel()
        self.lbl_fallo.setWordWrap(True)
        self.lbl_fallo.setStyleSheet("background: #311B29; color: #FDA4AF; padding: 8px; border-radius: 6px;")
        self.lbl_fallo.hide()
        v_can.addWidget(self.lbl_fallo)

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

    def _plantilla_nivel(self) -> str:
        return (
            f"INICIAR {self.nivel_actual.escenario}\n"
            "// Escribí tu jugada acá. Usá el botón Ayuda / Entorno para ver el escenario.\n"
            "FIN"
        )

    def seleccionar_nivel(self, nivel_id: str, ir_a_jugar: bool = True) -> None:
        self.nivel_actual = obtener_nivel(nivel_id, self.niveles)
        self.lbl_titulo_nivel.setText(f"{self.nivel_actual.nombre} · {self.nivel_actual.subtitulo}")
        self._actualizar_ayudas()
        self.ultimo_intento = None
        self._intento_en_curso = None
        self._es_repeticion = False
        self.btn_desafio.setEnabled(True)
        self.btn_repetir.setEnabled(False)
        self.lbl_fallo.hide()
        self.editor.setPlainText(self._plantilla_nivel())
        self.editor.limpiar_errores()
        self.cancha.cargar_nivel(self.nivel_actual)
        self.cancha.cambiar_modo_desafio(self.modo_desafio)
        self.lbl_accion_actual.setText("Acción 0/0 · Listo")
        self.estado_rep = EstadoReproduccion.INICIAL
        self._actualizar_statusbar("Listo para ejecutar.")
        if ir_a_jugar:
            self.stack.setCurrentIndex(1)

    def restaurar_plantilla(self) -> None:
        self.editor.setPlainText(self._plantilla_nivel())
        self.editor.limpiar_errores()
        self.reiniciar_simulacion()

    def ejecutar_jugada(self) -> None:
        self.cancha.timer.stop()
        self.cancha._detener_celebracion()
        self.sonido_gol.detener()
        self._intento_en_curso = None
        self.lbl_fallo.hide()
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
        self._intento_en_curso = {
            "nivel_id": self.nivel_actual.id, "resultado": simulacion, "acciones": len(acciones),
            "pista_usada": self.nivel_actual.id in self.progreso.pistas_consultadas,
            "desafio": self.modo_desafio,
        }
        self.ultimo_intento = dict(self._intento_en_curso)
        self._es_repeticion = False
        self.btn_repetir.setEnabled(True)
        self.estado_rep = EstadoReproduccion.REPRODUCIENDO
        self._actualizar_statusbar(f"Reproduciendo {len(acciones)} acciones...")
        self.cancha.iniciar_reproduccion(simulacion, len(acciones))
        self.cancha.cambiar_modo_desafio(self.modo_desafio)
        self.btn_desafio.setEnabled(False)

    def alternar_pausa(self) -> None:
        activo = self.cancha.pausar_o_reanudar()
        self.estado_rep = EstadoReproduccion.REPRODUCIENDO if activo else EstadoReproduccion.PAUSADO
        self._actualizar_statusbar("Reproduciendo..." if activo else "Pausado.")

    def reiniciar_simulacion(self) -> None:
        self.cancha.reiniciar()
        self.cancha.cambiar_modo_desafio(self.modo_desafio)
        self._intento_en_curso = None
        self.lbl_fallo.hide()
        self.btn_desafio.setEnabled(True)
        self.sonido_gol.detener()
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
        self.btn_desafio.setEnabled(True)
        if self._es_repeticion:
            self.estado_rep = EstadoReproduccion.EXITO if resultado.exito else EstadoReproduccion.FALLO
            self._mostrar_fallo(resultado)
            self._actualizar_statusbar("Repetición finalizada. El progreso y las medallas se mantienen.")
            return
        intento = self._intento_en_curso
        self._intento_en_curso = None
        if not intento or intento["nivel_id"] != self.nivel_actual.id:
            return
        if resultado.exito:
            self.estado_rep = EstadoReproduccion.EXITO
            medalla = calcular_medalla(intento["acciones"], self.metas_acciones[self.nivel_actual.id], intento["pista_usada"])
            self.progreso.registrar_victoria(self.nivel_actual.id, medalla, intento["acciones"])
            self._refrescar_progreso_global()

            if self.progreso.balon_de_oro_desbloqueado:
                self.cancha.iniciar_celebracion_8bit(
                    "balon_de_oro",
                    "¡BALÓN DE ORO GANADO!",
                    f"Completaste los 4 niveles • {resultado.motivo}",
                )
                self._actualizar_statusbar(
                    f"¡BALÓN DE ORO DESBLOQUEADO! 4/4 niveles completados. {resultado.motivo}"
                )
            else:
                self.cancha.iniciar_celebracion_8bit(
                    "nivel",
                    "¡NIVEL COMPLETADO!",
                    f"{resultado.motivo} • Medalla de {medalla}",
                )
                self._actualizar_statusbar(
                    f"¡ÉXITO! {resultado.motivo} — Medalla de {medalla}"
                )
        else:
            self.estado_rep = EstadoReproduccion.FALLO
            self._mostrar_fallo(resultado)
            self._actualizar_statusbar(self.lbl_fallo.text())

    def _mostrar_fallo(self, resultado):
        self.lbl_fallo.setVisible(not resultado.exito)
        if not resultado.exito:
            fr = resultado.frames[-1] if resultado.frames else None
            texto = fr.consejo_fallo if fr and fr.consejo_fallo else ("Revisá el recorrido y las marcas." if self.cancha.modo_desafio else resultado.motivo)
            if fr and fr.responsable_fallo:
                texto = f"Defensor destacado: {fr.responsable_fallo}. {texto}"
            self.lbl_fallo.setText(f"Jugada fallida: {texto}")

    def repetir_jugada(self):
        if not self.ultimo_intento or self.ultimo_intento["nivel_id"] != self.nivel_actual.id:
            return
        intento = self.ultimo_intento
        self._intento_en_curso = None
        self._es_repeticion = True
        self.lbl_fallo.hide()
        self.sonido_gol.detener()
        self.cancha.cambiar_modo_desafio(intento["desafio"])
        self.cancha.iniciar_reproduccion(intento["resultado"], intento["acciones"])
        self.estado_rep = EstadoReproduccion.REPRODUCIENDO
        self.btn_desafio.setEnabled(False)
        self._actualizar_statusbar("Repitiendo el último intento sin sumar premios.")

    def cambiar_modo_desafio(self, activo):
        if self.cancha.timer.isActive() or self._intento_en_curso:
            self.cancha.timer.stop()
        self.modo_desafio = activo
        self.cancha.cambiar_modo_desafio(activo)
        self.reiniciar_simulacion()
        self.btn_desafio.setText("Desafío: activado" if activo else "Modo desafío")
        self._actualizar_ayudas()

    def _actualizar_ayudas(self):
        self.lbl_ayuda_fichas.setText(
            "🏁 Modo desafío: las zonas de movimiento están ocultas."
            if self.modo_desafio else
            "💡 Hacé clic en un jugador clave, en la cancha o en el cajón, para iluminar las 4 casillas donde puede moverse."
        )
        objetivo = self.nivel_actual.objetivo
        if self.modo_desafio:
            texto = f"Desafío: asistí con {objetivo.asistente} y definí con {objetivo.rematador}." if objetivo.asistente else f"Desafío: convertí con {objetivo.rematador}."
            self.lbl_objetivo_nivel.setText(texto + " Sin zonas iluminadas, flechas de intención ni solución.")
        else:
            self.lbl_objetivo_nivel.setText(f"Objetivo: {self.nivel_actual.pista}")
        self.btn_pista.setEnabled(not self.modo_desafio)
        meta = self.metas_acciones[self.nivel_actual.id]
        criterio = f"Pista consultada: Plata hasta {meta} acciones, Bronce si usás más." if self.nivel_actual.id in self.progreso.pistas_consultadas else f"Oro: sin Pista · Plata: hasta {meta} acciones con Pista · Bronce: completar."
        self.lbl_medallas.setText(f"{criterio}  {self.progreso.texto_medalla(self.nivel_actual.id)}")

    def _refrescar_progreso_global(self) -> None:
        comp = self.progreso.cantidad_completados
        total = len(self.niveles)
        self.lbl_top_trofeos.setText(f"{comp}/{total} 🏆")
        self.pagina_niveles.actualizar_tarjetas()
        self.pagina_trofeos.actualizar_vitrina()
        self._actualizar_ayudas()

    def _actualizar_statusbar(self, msg: str) -> None:
        self.status.showMessage(f"[{self.estado_rep.value}] Nivel: {self.nivel_actual.nombre}  |  {msg}")

    def mostrar_ayuda(self) -> None:
        dlg = DialogoAyuda(self, None if self.modo_desafio else self.nivel_actual)
        dlg.exec()

    def mostrar_pista(self) -> None:
        if self.modo_desafio:
            return
        self.progreso.registrar_pista(self.nivel_actual.id)
        if self._intento_en_curso:
            self._intento_en_curso["pista_usada"] = True
        self._actualizar_ayudas()
        dlg = DialogoPista(self.nivel_actual, self)
        dlg.exec()
