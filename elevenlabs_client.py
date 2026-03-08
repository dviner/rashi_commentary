"""
ElevenLabs TTS client — converts a podcast script to an MP3 file.
"""

import requests
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID


def text_to_mp3(script_text: str, output_path: str) -> None:
    """
    Convert script_text to speech using ElevenLabs and write the result
    to output_path as an MP3 file.

    Raises RuntimeError on API errors.
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY environment variable is not set."
        )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": script_text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {response.status_code}: {response.text}"
        )

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Audio saved to: {output_path} ({len(response.content):,} bytes)")
