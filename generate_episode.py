"""
Main script — generates one weekly Rashi commentary podcast episode end-to-end.

Usage:
    python generate_episode.py

Reads from environment:
    ANTHROPIC_API_KEY   — Anthropic API key
    ELEVENLABS_API_KEY  — ElevenLabs API key
    ELEVENLABS_VOICE_ID — (optional) override the voice ID from config.py
"""

import os
import sys
from datetime import datetime, timezone

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, EPISODES_DIR, SCRIPTS_DIR, PODCAST_BASE_URL
from sefaria_client import get_current_parashah, get_rashi_commentary
from elevenlabs_client import text_to_mp3
from rss_manager import add_episode


EPISODE_SCRIPT_PROMPT = """\
You are the host of a weekly podcast called "Rashi in Brief" that explores Rashi's \
commentary on the Jewish weekly Torah portion in about 10 minutes.

Rashi (Rabbi Shlomo Yitzchaki, 1040–1105) is the most widely studied Jewish Bible \
commentator. His commentary is famous for identifying difficulties in the biblical text — \
unusual word choices, apparent contradictions, logical gaps — and resolving them with \
concise, precise answers drawn from rabbinic tradition, grammar, and close reading.

Below is the English translation of Rashi's commentary on this week's Torah portion, \
called {parashah_name} ({parashah_ref}).

Write a podcast episode script that is approximately 1,400 words — suitable for a \
9 to 11 minute recording. The script must have exactly five parts, clearly separated \
by a blank line between each part:

Part 1 — Introduction (2-3 sentences): Welcome listeners warmly. Introduce the name \
of this week's Torah portion and set up the idea that we'll be looking at it through \
the eyes of Rashi.

Part 2 — Setting the Stage (4-6 sentences): Give a brief orientation to the content \
of this week's Torah portion — the key events, characters, or themes — so that \
listeners have context for Rashi's comments. Then explain what kinds of questions or \
difficulties Rashi tends to focus on in this particular portion.

Part 3 — Rashi's Key Commentaries (15-20 sentences): This is the heart of the \
episode. Walk through 4 to 6 of Rashi's most interesting, important, or illuminating \
comments on this portion. For each one: first, briefly state what the Torah verse says; \
then, identify the difficulty or question Rashi is addressing; then, explain Rashi's \
answer. Help the listener understand not just what Rashi says, but why it matters — \
what it reveals about the text, the characters, or the deeper meaning. Between each \
commentary (i.e. after each group of sentences about one Rashi comment, before the next), \
output exactly this on its own line: <break time="0.75s" />

Part 4 — Themes and Takeaways (4-6 sentences): Step back and draw out the bigger \
picture. What recurring themes or ideas does Rashi emphasize across his commentary on \
this portion? What does his approach reveal about his understanding of the text or \
of Torah study more broadly?

Part 5 — Closing (1-2 sentences): A brief, warm sign-off.

Between each part, output exactly this on its own line:
<break time="1.5s" />

Write in a warm, clear, conversational tone — as if speaking to a curious, \
thoughtful listener who may not have a background in Jewish learning. \
Do not include section labels, headers, stage directions, or any other formatting. \
When you use Hebrew terms, always explain them briefly in English.

Rashi's commentary text:
{rashi_text}
"""


def _get_audio_duration(mp3_path: str) -> int:
    """
    Return MP3 duration in seconds.
    Uses mutagen for accuracy; falls back to file-size estimate at 128 kbps.
    """
    try:
        from mutagen.mp3 import MP3
        audio = MP3(mp3_path)
        return int(audio.info.length)
    except ImportError:
        size_bytes = os.path.getsize(mp3_path)
        return int(size_bytes / 16_000)  # 128 kbps ≈ 16,000 bytes/sec


def generate_episode() -> None:
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Determine today's episode filename
    today = datetime.now(tz=timezone.utc)
    date_str = today.strftime("%Y-%m-%d")
    os.makedirs(EPISODES_DIR, exist_ok=True)
    mp3_filename = f"{date_str}.mp3"
    mp3_path = os.path.join(EPISODES_DIR, mp3_filename)

    if os.path.exists(mp3_path):
        print(f"Episode for {date_str} already exists at {mp3_path}. Skipping.")
        return

    # Step 1: Get this week's Parashah
    print("Fetching current Parashah from Sefaria...")
    parashah = get_current_parashah()
    print(f"  Parashah: {parashah['name']} ({parashah['ref']})")

    # Step 2: Fetch Rashi's commentary
    print("Fetching Rashi's commentary from Sefaria...")
    rashi_text = get_rashi_commentary(parashah["ref"])
    print(f"  Retrieved commentary ({rashi_text.count(chr(10)) + 1} comments)")

    # Step 3: Generate the podcast script with Claude
    print(f"Generating episode script with {ANTHROPIC_MODEL}...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = EPISODE_SCRIPT_PROMPT.format(
        parashah_name=parashah["name"],
        parashah_ref=parashah["ref"],
        rashi_text=rashi_text,
    )
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    script = message.content[0].text.strip()
    print(f"  Script generated ({len(script)} characters, ~{len(script.split())} words)")

    # Save script to scripts/YYYY-MM-DD.txt
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, f"{date_str}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"Parashah (Rashi): {parashah['name']} ({parashah['ref']})\n")
        f.write(f"Date: {date_str}\n\n")
        f.write(script)
    print(f"  Script saved to: {script_path}")
    print(f"\n--- SCRIPT ---\n{script}\n--- END SCRIPT ---\n")

    # Step 4: Convert script to MP3
    print("Converting script to audio with ElevenLabs...")
    text_to_mp3(script, mp3_path)

    # Step 5: Update the RSS feed
    mp3_size = os.path.getsize(mp3_path)
    duration = _get_audio_duration(mp3_path)
    episode_title = f"{parashah['name']} — {date_str}"
    episode_description = (
        f"This week's Torah portion is {parashah['name']} ({parashah['ref']}). "
        f"A 10-minute exploration of Rashi's commentary on the key passages."
    )

    print("Updating RSS feed...")
    add_episode(
        title=episode_title,
        description=episode_description,
        pub_date=today,
        mp3_filename=mp3_filename,
        mp3_size_bytes=mp3_size,
        duration_seconds=duration,
    )

    print(f"\nEpisode complete!")
    print(f"  Audio: {mp3_path}")
    print(f"  Duration: {duration // 60}m {duration % 60}s")
    print(f"  RSS feed updated: docs/feed.xml")
    print(f"  RSS URL (after push): {PODCAST_BASE_URL}/feed.xml")


if __name__ == "__main__":
    generate_episode()
