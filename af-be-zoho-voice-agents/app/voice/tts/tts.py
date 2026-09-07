"""
Text-to-Speech using Windows SAPI5 (subprocess) or pyttsx3 (Mac/Linux).
Converts agent reply text to WAV bytes sent back to the browser.
"""
import re
import sys
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

from app.config import SETTINGS, logger
from app.config.settings import VOICE_PROFILES, LINUX_VOICE_MAP

# Clean text before sending to TTS engine (removes markdown, links, symbols)
CLEANING_RULES = [
    (re.compile(r'\*{1,3}([^*]+)\*{1,3}'), r'\1'),
    (re.compile(r'_{1,2}([^_]+)_{1,2}'),   r'\1'),
    (re.compile(r'`{1,3}([^`]*)`{1,3}'),   r'\1'),
    (re.compile(r'#{1,6}\s*'),              ''),
    (re.compile(r'^\s*[-*]\s+', re.M),     ''),
    (re.compile(r'https?://\S+'),           ''),
    (re.compile(r'[{}<>\\|^~`\[\]]'),      ''),
    (re.compile(r'\s{2,}'),                ' '),
]
# LLM hallucinations to discard entirely — not worth reading aloud
HALLUCINATIONS = {"thank you for watching", "thank you", "please subscribe"}

# Clean LLM text (remove markdown, links, noise) → return safe speech string or empty if useless
def clean_for_speech(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    for pattern, replacement in CLEANING_RULES:
        text = pattern.sub(replacement, text)
    text = text.strip()
    if text.lower().rstrip(".!?").strip() in HALLUCINATIONS:
        return ""
    return text

# Run platform-specific TTS in subprocess → generate WAV file safely without blocking main thread
def synth_subprocess(text: str, out_path: str, voice: str) -> bool:
    profile = VOICE_PROFILES.get(voice, VOICE_PROFILES[SETTINGS.DEFAULT_VOICE])

    if sys.platform == "win32":
        sapi_rate = profile.get("sapi_rate", 0)  # defined per voice in VOICE_PROFILES (settings.py)
        script = (
            "import win32com.client\n"
            "try:\n"
            "    speaker = win32com.client.Dispatch('SAPI.SpVoice')\n"
            f"    speaker.Rate = {sapi_rate}\n"
            "    voices = speaker.GetVoices()\n"
            f"    kws = {profile['keywords']!r}\n"
            "    for i in range(voices.Count):\n"
            "        desc = voices.Item(i).GetDescription().lower()\n"
            "        if any(k in desc for k in kws):\n"
            "            speaker.Voice = voices.Item(i)\n"
            "            break\n"
            "    stream = win32com.client.Dispatch('SAPI.SpFileStream')\n"
            f"    stream.Open({out_path!r}, 3, False)\n"
            "    speaker.AudioOutputStream = stream\n"
            f"    speaker.Speak({text!r})\n"
            "    stream.Close()\n"
            "except Exception as e:\n"
            "    print(e); exit(1)\n"
        )
    else:
        linux_voice = LINUX_VOICE_MAP.get(voice, LINUX_VOICE_MAP[SETTINGS.DEFAULT_VOICE])
        script = (
            "import pyttsx3\n"
            "e = pyttsx3.init()\n"
            f"e.setProperty('rate', {profile['rate']})\n"
            f"e.setProperty('voice', {linux_voice!r})\n"
            f"e.save_to_file({text!r}, {out_path!r})\n"
            "e.runAndWait()\n"
            "e.stop()\n"
        )

    try:
        result = subprocess.run([sys.executable, "-c", script], timeout=20, capture_output=True)
        return result.returncode == 0
    except Exception as e:
        logger.error("TTS subprocess failed", error=str(e))
        return False

# ── TTS singleton ─────────────────────────────────────────────────────────────
class PyttsxTTS:
    instance = None
    def __new__(cls):  # Ensure single instance of TTS engine
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance.default_voice = SETTINGS.DEFAULT_VOICE
            cls.instance.interrupt     = threading.Event()
        return cls.instance

    def load(self) -> None: # Validate TTS engine availability at startup
        try:
            import pyttsx3
            e = pyttsx3.init()
            e.stop()
            logger.info("TTS engine ready", voice=self.default_voice)
        except Exception as e:
            logger.warning("TTS engine unavailable — audio will be disabled", error=str(e))

    def synthesize(self, text: str, voice: str = None) -> Optional[bytes]: # Convert text to WAV audio bytes
        clean = clean_for_speech(text)
        if not clean:
            return None
        v = voice or self.default_voice
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = Path(tmp.name)
        ok = synth_subprocess(clean, str(path), v)
        if ok and path.exists() and path.stat().st_size > 100:
            data = path.read_bytes()
            path.unlink(missing_ok=True)
            return data
        return None

tts = PyttsxTTS()
