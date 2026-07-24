"""
ElevenLabs TTS client — converts a podcast script to an MP3 file.
"""

import base64
import requests
from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_PRONUNCIATION_DICT_ID,
    ELEVENLABS_PRONUNCIATION_VERSION_ID,
)


def text_to_mp3(script_text: str, output_path: str) -> dict:
    """
    Convert script_text to speech using ElevenLabs and write the result
    to output_path as an MP3 file.

    Returns the alignment dict with character-level timing data, which can
    be passed to srt_generator.generate_srt() to produce a transcript.

    Raises RuntimeError on API errors.
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY environment variable is not set."
        )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": script_text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
        "pronunciation_dictionary_locators": [
            {
                "pronunciation_dictionary_id": ELEVENLABS_PRONUNCIATION_DICT_ID,
                "version_id": ELEVENLABS_PRONUNCIATION_VERSION_ID,
            }
        ],
    }

    response = requests.post(url, json=payload, headers=headers, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {response.status_code}: {response.text}"
        )

    data = response.json()
    audio_bytes = base64.b64decode(data["audio_base64"])

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    print(f"Audio saved to: {output_path} ({len(audio_bytes):,} bytes)")
    return data["alignment"]
