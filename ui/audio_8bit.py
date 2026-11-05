"""Sintetizador procedural de festejos 8 bits, sin QtMultimedia."""

import functools
import io
import math
import os
import random
import threading
import wave

FRECUENCIA = 22050
DURACION_NIVEL = 1.8
DURACION_BALON = 3.0

_ultimo_wav = None


def _headless() -> bool:
    return os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def _pcm(valor: float) -> int:
    return max(0, min(255, int(128 + valor * 127)))


def _cuadrada(frecuencia: float, tiempo: float, duty: float = 0.5) -> float:
    if frecuencia <= 0:
        return 0.0
    fase = (frecuencia * tiempo) % 1.0
    return 1.0 if fase < duty else -1.0


def _envolvente(tiempo: float, duracion: float, ataque: float, caida: float) -> float:
    if tiempo < 0 or tiempo > duracion:
        return 0.0
    subida = min(1.0, tiempo / ataque) if ataque > 0 else 1.0
    bajada = min(1.0, (duracion - tiempo) / caida) if caida > 0 else 1.0
    return subida * bajada


def _crear_wav(muestras: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(FRECUENCIA)
        wav.writeframes(muestras)
    return buffer.getvalue()


@functools.lru_cache(maxsize=2)
def _muestras_festejo_nivel() -> bytes:
    total = int(FRECUENCIA * DURACION_NIVEL)
    rng = random.Random(20221118)
    salida = bytearray()
    ruido = 0.0

    notas = [
        (523.25, 0.16),
        (659.25, 0.16),
        (783.99, 0.16),
        (1046.50, 0.24),
        (783.99, 0.14),
        (1046.50, 0.24),
        (1318.51, 0.30),
        (1046.50, 0.42),
    ]
    eventos = []
    inicio = 0.12
    for frecuencia, duracion in notas:
        eventos.append((inicio, inicio + duracion, frecuencia))
        inicio += duracion

    for i in range(total):
        t = i / FRECUENCIA
        ovacion = _envolvente(t, DURACION_NIVEL, ataque=0.06, caida=0.55)
        modulacion = 0.62 + 0.38 * math.sin(2 * math.pi * 6.3 * t + 0.6 * math.sin(2 * math.pi * 1.7 * t))
        ruido = 0.72 * ruido + 0.28 * rng.uniform(-1.0, 1.0)
        griteria = ruido * ovacion * modulacion * 0.52

        melodia = 0.0
        for ini, fin, frecuencia in eventos:
            if ini <= t < fin:
                local = t - ini
                duracion = fin - ini
                env = _envolvente(local, duracion, ataque=0.008, caida=0.06)
                vibrato = 1.0 + 0.006 * math.sin(2 * math.pi * 6.0 * local)
                f = frecuencia * vibrato
                melodia += (
                    0.78 * _cuadrada(f, t, 0.5)
                    + 0.22 * _cuadrada(f * 2.0, t, 0.25)
                ) * env
        if 1.22 <= t < 1.72:
            local = t - 1.22
            env = _envolvente(local, 0.50, ataque=0.015, caida=0.18)
            melodia += (
                0.34 * _cuadrada(1046.50, t, 0.5)
                + 0.24 * _cuadrada(1318.51, t, 0.4)
                + 0.18 * _cuadrada(1567.98, t, 0.35)
            ) * env

        mezcla = griteria * 0.55 + melodia * 0.58
        mezcla = math.tanh(mezcla * 1.25) * 0.94
        salida.append(_pcm(mezcla))

    return bytes(salida)


@functools.lru_cache(maxsize=2)
def _muestras_festejo_balon() -> bytes:
    total = int(FRECUENCIA * DURACION_BALON)
    rng = random.Random(1986)
    salida = bytearray()
    ruido = 0.0

    acordes = [
        (0.10, 0.52, (261.63, 329.63, 392.00)),
        (0.62, 0.52, (349.23, 440.00, 523.25)),
        (1.14, 0.52, (392.00, 493.88, 587.33)),
        (1.66, 0.82, (261.63, 329.63, 392.00, 523.25)),
    ]
    melodia = [
        (0.10, 0.22, 523.25),
        (0.32, 0.22, 659.25),
        (0.54, 0.22, 783.99),
        (0.76, 0.36, 1046.50),
        (1.14, 0.22, 783.99),
        (1.36, 0.22, 987.77),
        (1.58, 0.30, 1174.66),
        (1.88, 0.56, 1046.50),
        (2.44, 0.48, 1318.51),
    ]

    for i in range(total):
        t = i / FRECUENCIA
        ovacion = _envolvente(t, DURACION_BALON, ataque=0.05, caida=0.65)
        modulacion = 0.58 + 0.42 * math.sin(2 * math.pi * 5.4 * t)
        ruido = 0.78 * ruido + 0.22 * rng.uniform(-1.0, 1.0)
        griteria = ruido * ovacion * modulacion * 0.42

        fanfarria = 0.0
        for ini, duracion, frecuencias in acordes:
            if ini <= t < ini + duracion:
                local = t - ini
                env = _envolvente(local, duracion, ataque=0.02, caida=0.16)
                for frecuencia in frecuencias:
                    vibrato = 1.0 + 0.004 * math.sin(2 * math.pi * 5.5 * local)
                    f = frecuencia * vibrato
                    fanfarria += (
                        0.28 * _cuadrada(f, t, 0.38)
                        + 0.10 * _cuadrada(f * 2.0, t, 0.50)
                        + 0.05 * _cuadrada(f * 3.0, t, 0.42)
                    ) * env

        for ini, duracion, frecuencia in melodia:
            if ini <= t < ini + duracion:
                local = t - ini
                env = _envolvente(local, duracion, ataque=0.01, caida=0.09)
                vibrato = 1.0 + 0.009 * math.sin(2 * math.pi * 6.2 * local)
                f = frecuencia * vibrato
                fanfarria += (
                    0.55 * _cuadrada(f, t, 0.45)
                    + 0.22 * _cuadrada(f * 2.0, t, 0.50)
                ) * env

        if 2.34 <= t < 2.96:
            local = t - 2.34
            env = _envolvente(local, 0.62, ataque=0.01, caida=0.22)
            destello = 2093.0 * (1.0 + 0.003 * math.sin(2 * math.pi * 11.0 * local))
            fanfarria += 0.10 * _cuadrada(destello, t, 0.25) * env

        mezcla = griteria + fanfarria * 0.56
        mezcla = math.tanh(mezcla * 1.35) * 0.95
        salida.append(_pcm(mezcla))

    return bytes(salida)


def _reproducir_wav(datos: bytes) -> None:
    global _ultimo_wav

    if _headless():
        return

    try:
        import winsound
    except Exception:
        return

    _ultimo_wav = datos
    try:
        winsound.PlaySound(_ultimo_wav, winsound.SND_MEMORY | winsound.SND_ASYNC)
        return
    except Exception:
        pass

    # Algunas versiones de winsound no aceptan SND_MEMORY junto a SND_ASYNC.
    # En ese caso se reproduce en un hilo daemon para no bloquear la UI.
    try:
        threading.Thread(
            target=lambda audio=_ultimo_wav: winsound.PlaySound(audio, winsound.SND_MEMORY),
            daemon=True,
        ).start()
    except Exception:
        pass


def _festejo_nivel_seguro() -> None:
    try:
        _reproducir_wav(_crear_wav(_muestras_festejo_nivel()))
    except Exception:
        return


def _festejo_balon_seguro() -> None:
    try:
        _reproducir_wav(_crear_wav(_muestras_festejo_balon()))
    except Exception:
        return


def reproducir_festejo_nivel() -> None:
    if _headless():
        return
    threading.Thread(target=_festejo_nivel_seguro, daemon=True).start()


def reproducir_festejo_balon_de_oro() -> None:
    if _headless():
        return
    threading.Thread(target=_festejo_balon_seguro, daemon=True).start()
