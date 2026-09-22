"""
Sagar Mitra - Feature 1: Regional Language Voice In/Out
==============================================================================
Lets a fisherman speak a query in Marathi, Tamil, Telugu, Gujarati,
Malayalam, English, Hindi, Bengali, Kannada, Punjabi, or Odia and get the
advisory back as speech in that same language. Both directions go straight through Gemini's native multimodal
audio understanding and TTS -- no separate STT/TTS service -- using the
same key-rotation machinery (app.advisory.generate_content) as every other
Gemini call in ORCA, so a quota hit here rotates keys exactly like it does
for the text advisory path.

Consumed by app/main.py's /api/voice/orchestrate endpoint.
"""
import json
import os
import re
import uuid
import wave
from io import BytesIO

from google.genai import types

from app.advisory import generate_content, LITE_MODEL

# Same static directory app/main.py mounts at /static. Unlike historical.py's
# chart images (in-memory base64, no disk write), audio genuinely needs a
# real file for the frontend's <audio> element to stream/seek, and is only
# ever written on an explicit voice query (not on every typed chat
# message), so it isn't the live-reload trigger a chart-per-message would be.
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Full base URL so audio links are directly playable from the frontend.
# Set SAGAR_MITRA_BASE_URL in .env once deployed.
BASE_URL = os.environ.get("SAGAR_MITRA_BASE_URL", "http://127.0.0.1:8000")

# Transcription+translation is a structured extraction task, not open-ended
# synthesis -- run it on the lite model so it doesn't compete with the
# user-facing advisory synthesis call for the same quota (see
# advisory.LITE_MODEL and nlp_extract.py, which does the same for text).
TRANSCRIBE_MODEL = LITE_MODEL

# Google's current native-audio-output model. Swap this if Google
# renames/promotes the TTS-capable model.
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_VOICE = "Kore"

SUPPORTED_LANGUAGES = [
    "Marathi", "Tamil", "Telugu", "Gujarati", "Malayalam", "English",
    "Hindi", "Bengali", "Kannada", "Punjabi", "Odia",
]

TRANSCRIBE_SYSTEM_PROMPT = """
You are the speech-input layer for Sagar Mitra, an ocean intelligence system
for the Indian coast. You are given a short spoken audio clip from a
fisherman or coastal resident, in Marathi, Tamil, Telugu, Gujarati,
Malayalam, English, Hindi, Bengali, Kannada, Punjabi, or Odia.

Respond with ONLY valid JSON, no markdown, no explanation, matching this
exact schema:

{
  "transcript": "<exact transcription of the speech, in its own native script>",
  "language": "<one of: Marathi, Tamil, Telugu, Gujarati, Malayalam, English, Hindi, Bengali, Kannada, Punjabi, Odia>",
  "english_text": "<English translation of the transcript>"
}

If the clip is silent, unintelligible, or not recognizable speech, respond
with ONLY this exact JSON instead:
{"error": "unsupported_audio"}
"""


class UnsupportedAudioError(Exception):
    """Raised when the uploaded clip is silent, unintelligible, or not
    recognizable speech -- callers should tell the user plainly instead of
    guessing at a transcript (see app/main.py's /api/voice/orchestrate)."""


def transcribe_and_translate(audio_bytes: bytes, mime_type: str = "audio/wav") -> dict:
    """
    Sends the raw audio clip straight to Gemini and gets back the
    native-script transcript, detected language, and English translation
    in a single call.

    Returns: {"transcript": str, "language": str, "english_text": str}
    Raises: UnsupportedAudioError if the clip has no recognizable speech.
    """
    response = generate_content(
        model=TRANSCRIBE_MODEL,
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
        config=types.GenerateContentConfig(
            system_instruction=TRANSCRIBE_SYSTEM_PROMPT,
            temperature=0.0,
            max_output_tokens=1024,
        ),
    )

    text = (response.text or "").strip()
    text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise UnsupportedAudioError(
                "Could not understand the audio clip. Please try speaking again clearly."
            )
        parsed = json.loads(match.group(0))

    if parsed.get("error") == "unsupported_audio" or not parsed.get("transcript"):
        raise UnsupportedAudioError(
            "Could not understand the audio clip. Please try speaking again clearly."
        )

    return parsed


def synthesize_speech(text: str, language: str = "English") -> bytes:
    """
    Turns advisory text into spoken audio via Gemini's native TTS, reading
    it fluently in `language`. Returns WAV-encoded audio bytes.
    """
    response = generate_content(
        model=TTS_MODEL,
        contents=f"Say the following naturally in {language}, in a calm, clear voice:\n\n{text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
                )
            ),
        ),
    )

    candidates = response.candidates or []
    parts = candidates[0].content.parts if candidates and candidates[0].content else None
    pcm_data = parts[0].inline_data.data if parts and parts[0].inline_data else None
    if not pcm_data:
        raise RuntimeError("Gemini TTS returned no audio data.")

    # Gemini's TTS models return raw 24kHz/16-bit/mono PCM, not a WAV
    # container -- wrap it so browsers can play it directly via <audio>.
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def save_advisory_audio(audio_bytes: bytes) -> dict:
    """Saves synthesized advisory audio under static/audio (served by
    FastAPI's StaticFiles mount, see app/main.py) and returns a public URL
    the frontend can hand straight to an <audio> element."""
    filename = f"advisory_{uuid.uuid4().hex[:8]}.wav"
    path = os.path.join(AUDIO_DIR, filename)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return {"file_path": path, "url": f"{BASE_URL}/static/audio/{filename}"}
