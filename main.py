import sys

def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "Error: PySide6 no está instalado en este entorno.\n"
            "Instalá las dependencias de la interfaz con:\n"
            "  pip install -r requirements-ui.txt",
            file=sys.stderr,
        )
        return 1

    from ui.ventana import VentanaPrincipal

    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())