"""
Test ElevenLabs pronunciation by uploading a dictionary and synthesizing sample text.
Uses eleven_v3 model with chunking (5000 char limit per request) and pydub stitching.

Usage:
    python test_pronunciation.py --pls <pls_file> <text_file> [output.mp3] [--name <name>]
    python test_pronunciation.py --rules <text_file> [output.mp3] [--name <name>]

  --pls    Upload a PLS file via the add-from-file API endpoint.
  --rules  Upload from pronunciation_rules.py via the add-from-rules API endpoint.
  --name   Optional name for the uploaded dictionary (default: "test-pls" or "test-rules").

Output defaults to test_output.mp3 in the current directory.
Chunk MP3s are written to a temp directory and deleted after stitching.
"""

import sys
import os
import re
import base64
import argparse
import tempfile
import requests
from pydub import AudioSegment

from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
)
from pronunciation_rules import PRONUNCIATION_RULES

BASE_URL = "https://api.elevenlabs.io/v1"
MODEL_ID = "eleven_v3"
MAX_CHARS = 5000


# ---------------------------------------------------------------------------
# Dictionary upload
# ---------------------------------------------------------------------------

def upload_pls(pls_path: str, name: str) -> tuple[str, str]:
    """Upload a PLS file to ElevenLabs and return (dict_id, version_id)."""
    with open(pls_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/pronunciation-dictionaries/add-from-file",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            files={"file": (os.path.basename(pls_path), f, "application/pls+xml")},
            data={"name": name},
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to upload PLS: {response.status_code} {response.text}"
        )
    data = response.json()
    dict_id = data["id"]
    version_id = data["version_id"]
    print(f"  Uploaded PLS dictionary '{name}': {dict_id} (version {version_id})")
    return dict_id, version_id


def upload_rules(name: str) -> tuple[str, str]:
    """Upload PRONUNCIATION_RULES to ElevenLabs and return (dict_id, version_id)."""
    response = requests.post(
        f"{BASE_URL}/pronunciation-dictionaries/add-from-rules",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "name": name,
            "rules": PRONUNCIATION_RULES,
        },
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to upload rules: {response.status_code} {response.text}"
        )
    data = response.json()
    dict_id = data["id"]
    version_id = data["version_id"]
    print(f"  Uploaded rules dictionary '{name}': {dict_id} (version {version_id})")
    print(f"  ({len(PRONUNCIATION_RULES)} rules)")
    return dict_id, version_id


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str) -> list[tuple[str, float]]:
    """
    Split text on <break> tags into (chunk_text, silence_after_seconds) pairs.
    The last chunk gets silence_after = 0.0.

    Warns if any chunk exceeds MAX_CHARS.
    """
    pattern = r'<break\s+time=["\'](\d+(?:\.\d+)?)s["\']\s*/?>'
    parts = re.split(pattern, text)
    # re.split with a capturing group alternates: text, capture, text, capture, ..., text
    chunks = []
    for i in range(0, len(parts), 2):
        chunk = parts[i].strip()
        silence = float(parts[i + 1]) if i + 1 < len(parts) else 0.0
        if not chunk:
            continue
        if len(chunk) > MAX_CHARS:
            print(f"  WARNING: chunk {len(chunks)+1} is {len(chunk)} chars (limit {MAX_CHARS}). "
                  f"Consider splitting further.")
        chunks.append((chunk, silence))
    return chunks


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

def synthesize_chunk(text: str, dict_id: str, version_id: str) -> bytes:
    """
    Synthesize one chunk via /with-timestamps and return raw MP3 bytes.
    """
    response = requests.post(
        f"{BASE_URL}/text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": MODEL_ID,
            "voice_settings": {
                "stability": 0.3,
                "speed": 0.8,
                "similarity_boost": 0.75,
            },
            "pronunciation_dictionary_locators": [
                {
                    "pronunciation_dictionary_id": dict_id,
                    "version_id": version_id,
                }
            ],
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"TTS error {response.status_code}: {response.text}"
        )
    data = response.json()
    return base64.b64decode(data["audio_base64"])


# ---------------------------------------------------------------------------
# Stitching
# ---------------------------------------------------------------------------

def stitch_chunks(chunk_paths: list[str], silence_durations: list[float],
                  output_path: str) -> None:
    """
    Concatenate chunk MP3 files, inserting silence between them, and export.
    """
    combined = AudioSegment.empty()
    for i, path in enumerate(chunk_paths):
        combined += AudioSegment.from_mp3(path)
        if i < len(silence_durations) and silence_durations[i] > 0:
            combined += AudioSegment.silent(duration=int(silence_durations[i] * 1000))
    combined.export(output_path, format="mp3")
    print(f"  Stitched {len(chunk_paths)} chunk(s) → {output_path} "
          f"({os.path.getsize(output_path):,} bytes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Test ElevenLabs pronunciation dictionaries (eleven_v3)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pls", metavar="PLS_FILE", help="Path to a PLS file to upload")
    mode.add_argument("--rules", action="store_true",
                      help="Upload from pronunciation_rules.py")
    parser.add_argument("text_file", help="Text file to synthesize")
    parser.add_argument("output", nargs="?", default="test_output.mp3",
                        help="Output MP3 path (default: test_output.mp3)")
    parser.add_argument("--name", help="Name for the uploaded dictionary")
    args = parser.parse_args()

    if not ELEVENLABS_API_KEY:
        print("ERROR: ELEVENLABS_API_KEY environment variable is not set.")
        sys.exit(1)

    if not os.path.exists(args.text_file):
        print(f"ERROR: Text file not found: {args.text_file}")
        sys.exit(1)

    with open(args.text_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    chunks = chunk_text(text)

    print(f"Text file: {args.text_file} ({len(text.split())} words, "
          f"{len(text)} chars, {len(chunks)} chunk(s))")
    print(f"Voice:     {ELEVENLABS_VOICE_ID}  Model: {MODEL_ID}")
    print()

    # Upload dictionary
    print("Uploading pronunciation dictionary...")
    if args.pls:
        if not os.path.exists(args.pls):
            print(f"ERROR: PLS file not found: {args.pls}")
            sys.exit(1)
        name = args.name or "test-pls"
        dict_id, version_id = upload_pls(args.pls, name)
    else:
        name = args.name or "test-rules"
        dict_id, version_id = upload_rules(name)

    # Synthesize each chunk to a temp file
    print(f"\nSynthesizing {len(chunks)} chunk(s)...")
    tmp_dir = tempfile.mkdtemp(prefix="tts_chunks_")
    chunk_paths = []
    silence_durations = []
    try:
        for i, (chunk_text_str, silence) in enumerate(chunks):
            print(f"  Chunk {i+1}/{len(chunks)}: {len(chunk_text_str)} chars, "
                  f"silence after: {silence}s")
            audio_bytes = synthesize_chunk(chunk_text_str, dict_id, version_id)
            chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
            with open(chunk_path, "wb") as f:
                f.write(audio_bytes)
            chunk_paths.append(chunk_path)
            silence_durations.append(silence)

        # Stitch
        print("\nStitching chunks...")
        stitch_chunks(chunk_paths, silence_durations, args.output)

    finally:
        # Clean up temp files
        for path in chunk_paths:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(tmp_dir)

    print()
    print("Done. To reuse this dictionary without re-uploading, set in config.py:")
    print(f"  ELEVENLABS_PRONUNCIATION_DICT_ID    = \"{dict_id}\"")
    print(f"  ELEVENLABS_PRONUNCIATION_VERSION_ID = \"{version_id}\"")


if __name__ == "__main__":
    main()
