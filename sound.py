"""Sunet ambiental de ploaie. Zgomotul este generat de program (fără fișiere externe).
Windows: folosește winsound (inclus în Python). Alte sisteme: pip install pygame"""

import os
import random
import struct
import sys
import tempfile
import wave

_PATH = os.path.join(tempfile.gettempdir(), "ploaie_meteo.wav")


def _genereaza(secunde=4, rata=22050):
    rnd = random.Random(1)
    prev, cadre = 0.0, bytearray()
    for _ in range(secunde * rata):
        prev = prev * 0.6 + rnd.uniform(-1, 1) * 0.4      # filtru trece-jos -> zgomot "de ploaie"
        cadre += struct.pack("<h", int(prev * 9000))
    with wave.open(_PATH, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rata)
        w.writeframes(bytes(cadre))


def porneste():
    """Returnează True dacă sunetul a pornit."""
    if not os.path.exists(_PATH):
        _genereaza()
    if sys.platform.startswith("win"):
        import winsound
        winsound.PlaySound(_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        return True
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.Sound(_PATH).play(loops=-1)
        return True
    except Exception:
        return False


def opreste():
    if sys.platform.startswith("win"):
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    else:
        try:
            import pygame
            pygame.mixer.stop()
        except Exception:
            pass
