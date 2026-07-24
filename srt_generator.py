"""
Generates SRT subtitle files from ElevenLabs character-level alignment data.
"""


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    total_ms = int(seconds * 1000)
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(alignment: dict, output_path: str) -> None:
    """
    Convert ElevenLabs character-level alignment to a phrase-chunked SRT file.

    alignment: dict with keys "characters", "character_start_times_seconds",
               "character_end_times_seconds" (as returned by /with-timestamps).
    output_path: where to write the .srt file.
    """
    characters = alignment["characters"]
    start_times = alignment["character_start_times_seconds"]
    end_times = alignment["character_end_times_seconds"]

    # Build word-level timing from character-level, skipping SSML/XML tags
    words = []
    current_word = ""
    word_start = None
    word_end = None
    inside_tag = False

    for char, start, end in zip(characters, start_times, end_times):
        if char == "<":
            inside_tag = True
            if current_word:
                words.append((current_word, word_start, word_end))
                current_word = ""
                word_start = None
            continue
        if inside_tag:
            if char == ">":
                inside_tag = False
            continue

        if char in (" ", "\n", "\r"):
            if current_word:
                words.append((current_word, word_start, word_end))
                current_word = ""
                word_start = None
        else:
            if word_start is None:
                word_start = start
            current_word += char
            word_end = end

    if current_word:
        words.append((current_word, word_start, word_end))

    # Group words into natural phrases (~8 words or at sentence boundary)
    MAX_WORDS = 8
    phrases = []
    current_words = []
    phrase_start = None
    phrase_end = None

    for word, start, end in words:
        current_words.append(word)
        if phrase_start is None:
            phrase_start = start
        phrase_end = end

        if word[-1] in ".!?" or len(current_words) >= MAX_WORDS:
            phrases.append((" ".join(current_words), phrase_start, phrase_end))
            current_words = []
            phrase_start = None

    if current_words:
        phrases.append((" ".join(current_words), phrase_start, phrase_end))

    with open(output_path, "w", encoding="utf-8") as f:
        for i, (text, start, end) in enumerate(phrases, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_timestamp(start)} --> {_format_timestamp(end)}\n")
            f.write(f"{text}\n\n")

    print(f"SRT transcript saved to: {output_path} ({len(phrases)} subtitle blocks)")
