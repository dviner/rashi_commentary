"""
ElevenLabs TTS client — converts a podcast script to an MP3 file.

Handles the eleven_v3 model's 5000-character limit by splitting on <break>
SSML tags, synthesizing each chunk, stitching with pydub, and combining
the character-level alignment data with corrected timestamps.
"""

import base64
import os
import re
import tempfile

import requests
from pydub import AudioSegment

from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_PRONUNCIATION_DICT_ID,
    ELEVENLABS_PRONUNCIATION_VERSION_ID,
)

MAX_CHARS = 5000
_BREAK_RE = re.compile(r'<break\s+time=["\'](\d+(?:\.\d+)?)s["\']\s*/?>')


def _chunk_text(text: str) -> list[tuple[str, float]]:
    """
    Split text on <break> tags into (chunk_text, silence_after_seconds) pairs.
    The last chunk gets silence_after = 0.0.
    Warns if any chunk exceeds MAX_CHARS.
    """
    parts = re.split(_BREAK_RE, text)
    chunks = []
    for i in range(0, len(parts), 2):
        chunk = parts[i].strip()
        silence = float(parts[i + 1]) if i + 1 < len(parts) else 0.0
        if not chunk:
            continue
        if len(chunk) > MAX_CHARS:
            print(f"  WARNING: chunk {len(chunks)+1} is {len(chunk)} chars "
                  f"(limit {MAX_CHARS}). Consider splitting further.")
        chunks.append((chunk, silence))
    return chunks


def _synthesize_chunk(text: str) -> tuple[bytes, dict]:
    """
    Synthesize one text chunk via /with-timestamps.
    Returns (mp3_bytes, alignment_dict).
    """
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/"
           f"{ELEVENLABS_VOICE_ID}/with-timestamps")
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
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
    return base64.b64decode(data["audio_base64"]), data["alignment"]


def _combine_alignments(
    alignments: list[dict],
    chunk_durations: list[float],
    silence_durations: list[float],
) -> dict:
    """
    Merge per-chunk alignment dicts into one, offsetting timestamps so they
    reflect position in the final stitched audio.
    """
    combined = {"characters": [], "character_start_times_seconds": [],
                "character_end_times_seconds": []}
    offset = 0.0
    for i, alignment in enumerate(alignments):
        combined["characters"].extend(alignment["characters"])
        combined["character_start_times_seconds"].extend(
            t + offset for t in alignment["character_start_times_seconds"]
        )
        combined["character_end_times_seconds"].extend(
            t + offset for t in alignment["character_end_times_seconds"]
        )
        offset += chunk_durations[i] + silence_durations[i]
    return combined


def text_to_mp3(script_text: str, output_path: str) -> dict:
    """
    Convert script_text to speech using ElevenLabs and write the result
    to output_path as an MP3 file.

    Splits on <break> SSML tags to stay within the eleven_v3 5000-char limit,
    synthesizes each chunk, stitches them together with pydub (inserting the
    specified silence between chunks), and combines the alignment data.

    Returns the combined alignment dict with character-level timing data, which
    can be passed to srt_generator.generate_srt() to produce a transcript.

    Raises RuntimeError on API errors.
    """
    if not ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY environment variable is not set."
        )

    chunks = _chunk_text(script_text)
    print(f"Script split into {len(chunks)} chunk(s) for synthesis.")

    tmp_dir = tempfile.mkdtemp(prefix="tts_chunks_")
    chunk_paths: list[str] = []
    alignments: list[dict] = []
    chunk_durations: list[float] = []
    silence_durations: list[float] = []

    try:
        for i, (chunk_text, silence) in enumerate(chunks):
            print(f"  Synthesizing chunk {i+1}/{len(chunks)}: "
                  f"{len(chunk_text)} chars, {silence}s silence after")
            audio_bytes, alignment = _synthesize_chunk(chunk_text)

            chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
            with open(chunk_path, "wb") as f:
                f.write(audio_bytes)
            chunk_paths.append(chunk_path)
            alignments.append(alignment)
            silence_durations.append(silence)

            # Duration = last end time in the alignment data
            end_times = alignment.get("character_end_times_seconds", [])
            chunk_durations.append(end_times[-1] if end_times else 0.0)

        # Stitch chunks with pydub
        combined_audio = AudioSegment.empty()
        for i, path in enumerate(chunk_paths):
            combined_audio += AudioSegment.from_mp3(path)
            if silence_durations[i] > 0:
                combined_audio += AudioSegment.silent(
                    duration=int(silence_durations[i] * 1000)
                )
        combined_audio.export(output_path, format="mp3")

        total_bytes = os.path.getsize(output_path)
        print(f"Audio saved to: {output_path} ({total_bytes:,} bytes)")

    finally:
        for path in chunk_paths:
            if os.path.exists(path):
                os.remove(path)
        if os.path.isdir(tmp_dir):
            os.rmdir(tmp_dir)

    return _combine_alignments(alignments, chunk_durations, silence_durations)
