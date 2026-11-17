# Ellie's voice. American female, natural everyday speech.
# Best: Piper offline voice "en_US-lessac-medium".
#   Uses piper\piper.exe (standalone, works from any Python)
#   and voices\en_US-lessac-medium.onnx (+ .onnx.json).
# Fallback: a Windows US female voice (Zira).

import os
import re
import subprocess
import sys
import tempfile
import winsound

HERE = os.path.dirname(os.path.abspath(__file__))
PIPER_MODEL = os.path.join(HERE, "voices", "en_US-lessac-medium.onnx")


def _clean(text):
    """Skips code blocks and markdown symbols so she doesn't read them aloud."""
    text = re.sub(r"```.*?```", " I have put the code on screen. ", text, flags=re.S)
    text = re.sub(r"[*_#`>]", "", text)
    text = re.sub(r"\s*\n+\s*", " ", text)      # line breaks -> one flowing paragraph
    text = re.sub(r"\.{2,}|…", ",", text)        # "..." -> short comma pause
    return re.sub(r"\s{2,}", " ", text).strip()


PIPER_EXE = os.path.join(HERE, "piper", "piper.exe")

# ---------- Voice tuning (change these to taste) ----------
LENGTH_SCALE = 0.95      # speed: lower = faster. 1.0 is the voice's normal pace.
NOISE_SCALE = 0.667      # expressiveness / tone variation. 0.5 is flatter.
NOISE_W = 0.8            # rhythm variation. Higher = more natural flow, lower = robotic.
SENTENCE_SILENCE = 0.15  # pause in seconds after each sentence.


def _piper_ready():
    return os.path.exists(PIPER_MODEL) and os.path.exists(PIPER_EXE)


def speak(text):
    """Says the text out loud. Blocks until she finishes speaking."""
    text = _clean(text)
    if not text:
        return
    flags = subprocess.CREATE_NO_WINDOW
    if _piper_ready():
        wav = os.path.join(tempfile.gettempdir(), "ellie_voice.wav")
        if os.path.exists(wav):
            os.remove(wav)
        subprocess.run([PIPER_EXE, "-m", PIPER_MODEL, "-f", wav,
                        "--length_scale", str(LENGTH_SCALE),
                        "--noise_scale", str(NOISE_SCALE),
                        "--noise_w", str(NOISE_W),
                        "--sentence_silence", str(SENTENCE_SILENCE)],
                       input=text.encode("utf-8"), creationflags=flags, check=False)
        if os.path.exists(wav):
            winsound.PlaySound(wav, winsound.SND_FILENAME)
            return
    # Windows fallback: prefer a US female voice, then any female voice.
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v=$s.GetInstalledVoices()|%{$_.VoiceInfo}|?{$_.Gender -eq 'Female'};"
        "$us=$v|?{$_.Culture.Name -eq 'en-US'}|select -First 1;"
        "if($us){$s.SelectVoice($us.Name)}elseif($v){$s.SelectVoice(($v|select -First 1).Name)};"
        "$s.Speak([Console]::In.ReadToEnd())"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   input=text.encode("utf-8"), creationflags=flags, check=False)
