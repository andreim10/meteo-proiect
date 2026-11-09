"""Sinteză vocală (Text-to-Speech) cu pyttsx3 – funcționează offline.
pip install pyttsx3   (pe Linux: sudo apt install espeak)
Dacă sistemul are voce în limba română, e aleasă automat."""

import threading


def disponibil():
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        return False


def _vorbeste(text):
    import pyttsx3
    motor = pyttsx3.init()
    try:
        for v in motor.getProperty("voices"):
            info = (v.name + " " + str(getattr(v, "languages", ""))).lower()
            if "ro-ro" in info or "romanian" in info or "română" in info or "ro_ro" in info or "ioana" in info:
                motor.setProperty("voice", v.id)
                break
        motor.setProperty("rate", 165)
    except Exception:
        pass
    motor.say(text)
    motor.runAndWait()


def spune(text):
    """Citește textul într-un thread separat. Returnează False dacă pyttsx3 lipsește."""
    if not disponibil():
        return False
    threading.Thread(target=lambda: _vorbeste(text), daemon=True).start()
    return True
