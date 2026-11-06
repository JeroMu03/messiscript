"""Música MP3 en bucle con el reproductor nativo de Windows."""

import ctypes
import os
import sys
from pathlib import Path


RUTA_TEMA = Path(__file__).resolve().parent.parent / "assets" / "audio" / "muchachos_8bit.mp3"
RUTA_GOL = RUTA_TEMA.with_name("gol.mp3")


class MusicaFondo:
    def __init__(self, ruta=RUTA_TEMA, bucle=True, volumen=350):
        self.ruta = Path(ruta)
        self.bucle = bucle
        self.volumen = volumen
        self.alias = f"messiscript_musica_{id(self)}"
        self.activa = False
        self.silenciada = False
        self.error = ""
        self._winmm = None

    def _enviar(self, comando):
        respuesta = ctypes.create_unicode_buffer(512)
        codigo = self._winmm.mciSendStringW(comando, respuesta, len(respuesta), None)
        if codigo:
            detalle = ctypes.create_unicode_buffer(512)
            self._winmm.mciGetErrorStringW(codigo, detalle, len(detalle))
            raise RuntimeError(detalle.value or f"Error de audio {codigo}")
        return respuesta.value

    def iniciar(self):
        if self.activa:
            return True
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return False
        if sys.platform != "win32":
            self.error = "La música de fondo requiere Windows."
            return False
        if not self.ruta.is_file():
            self.error = "No se encontró el tema de fondo."
            return False
        try:
            self._winmm = ctypes.WinDLL("winmm")
            self._winmm.mciSendStringW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
            self._winmm.mciSendStringW.restype = ctypes.c_uint
            self._winmm.mciGetErrorStringW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
            self._winmm.mciGetErrorStringW.restype = ctypes.c_int
            self._enviar(f'open "{self.ruta.resolve()}" type mpegvideo alias {self.alias}')
            self.activa = True
            self._enviar(f"setaudio {self.alias} volume to {0 if self.silenciada else self.volumen}")
            self._enviar(f"play {self.alias}" + (" repeat" if self.bucle else ""))
            self.error = ""
            return True
        except (OSError, RuntimeError) as exc:
            self.error = str(exc)
            self.detener()
            return False

    def silenciar(self, silenciada):
        silenciada = bool(silenciada)
        if self.activa:
            try:
                self._enviar(f"setaudio {self.alias} volume to {0 if silenciada else self.volumen}")
            except RuntimeError as exc:
                self.error = str(exc)
                return False
        self.silenciada = silenciada
        return True

    def detener(self):
        if self.activa:
            try:
                self._enviar(f"close {self.alias}")
            except RuntimeError:
                pass
            finally:
                self.activa = False


class SonidoGol(MusicaFondo):
    def __init__(self):
        super().__init__(RUTA_GOL, bucle=False, volumen=850)

    def reproducir(self):
        if not self.activa:
            return self.iniciar()
        try:
            self._enviar(f"play {self.alias} from 0")
            return True
        except RuntimeError as exc:
            self.error = str(exc)
            self.detener()
            return False
