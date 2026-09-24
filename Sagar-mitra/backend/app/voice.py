"""
Voice input/output for Sagar Mitra, backed by Groq audio APIs.
"""
import json
import os
import re
import uuid

from app.advisory import OPENAI_MODEL, get_openai_client, generate_content

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
BASE_URL = os.environ.get("SAGAR_MITRA_BASE_URL", "http://127.0.0.1:8000")
TRANSCRIBE_MODEL = "whisper-large-v3"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "troy"


class UnsupportedAudioError(Exception):
    """Raised when speech transcription returns no recognizable words."""


def transcribe_and_translate(audio_bytes: bytes, mime_type: str = "audio/wav") -> dict:
    """Transcribe speech, then detect its language and translate it for routing."""
    extension = {
        "audio/wav": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3",
        "audio/mp4": "mp4", "audio/webm": "webm", "audio/ogg": "ogg",
        "audio/x-m4a": "m4a",
    }.get(mime_type.split(";", 1)[0].lower(), "wav")
    transcription = get_openai_client().audio.transcriptions.create(
        model=TRANSCRIBE_MODEL,
        file=(f"query.{extension}", audio_bytes, mime_type),
    )
    transcript = (transcription.text or "").strip()
    if not transcript:
        raise UnsupportedAudioError("Could not understand the audio clip. Please try speaking again clearly.")

    result = generate_content(
        model=OPENAI_MODEL,
        contents=transcript,
        system_instruction=(
            "Detect the language of the user's transcript and translate it into English. "
            "Return only JSON with exactly these keys: transcript (preserve the original words "
            "and script), language (language name), english_text (English translation)."
        ),
        temperature=0,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(result.text)
    if not parsed.get("transcript"):
        raise UnsupportedAudioError("Could not understand the audio clip. Please try speaking again clearly.")
    return parsed


def synthesize_speech(text: str, language: str = "English") -> bytes:
    """Generate English WAV speech for an advisory using Groq text-to-speech."""
    if language.lower() not in {"english", "en"}:
        raise ValueError("Groq Orpheus speech output currently supports English only.")
    response = get_openai_client().audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav",
    )
    return response.content


def save_advisory_audio(audio_bytes: bytes) -> dict:
    """Save generated audio under the static mount and return its public URL."""
    filename = f"advisory_{uuid.uuid4().hex[:8]}.wav"
    path = os.path.join(AUDIO_DIR, filename)
    with open(path, "wb") as audio_file:
        audio_file.write(audio_bytes)
    return {"file_path": path, "url": f"{BASE_URL}/static/audio/{filename}"}
