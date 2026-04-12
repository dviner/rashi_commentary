import os

# --- Podcast Metadata ---
PODCAST_TITLE = "Rashi in Brief"
PODCAST_DESCRIPTION = (
    "A weekly podcast exploring Rashi's commentary on the Jewish Torah portion (Parashah) "
    "in about 10 minutes. New episode every week following the Ashkenazi diaspora reading schedule."
)
PODCAST_AUTHOR = "Dave Viner"
PODCAST_EMAIL = "parashahpodcaster@gmail.com"  # Used for Spotify ownership verification
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Religion &amp; Spirituality"
PODCAST_EXPLICIT = "clean"

# GitHub Pages base URL — update after creating your GitHub Pages site
# e.g. "https://USERNAME.github.io/REPO_NAME"
PODCAST_BASE_URL = "https://dviner.github.io/rashi_commentary"

# Path to cover art relative to docs/ — 3000x3000px JPEG or PNG, under 30MB
COVER_IMAGE_FILENAME = "rashi_in_brief_3000.png"

# --- ElevenLabs ---
# Get your API key from https://elevenlabs.io
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# Arabella - Z3R5wn05IrDiVCyEkUrK - https://elevenlabs.io/app/voice-library?voiceId=Z3R5wn05IrDiVCyEkUrK
#. ==> Arabella is a little to monotone.
# Charles  - zNsotODqUhvbJ5wMG7Ei - https://elevenlabs.io/app/voice-library?voiceId=zNsotODqUhvbJ5wMG7Ei
# Ranbir   - nZ5WsS2E2UAALki8m2V6 - https://elevenlabs.io/app/voice-library?voiceId=nZ5WsS2E2UAALki8m2V6
# Ingrid   - SS2U4vq6kgD4fTNVtd4k - https://elevenlabs.io/app/voice-library?voiceId=SS2U4vq6kgD4fTNVtd4k
# Shelley - 4CrZuIW9am7gYAxgo2Af - 

ELEVENLABS_VOICE_ID = os.environ.get(
    "ELEVENLABS_VOICE_ID", "4CrZuIW9am7gYAxgo2Af")  # Shelley
ELEVENLABS_MODEL_ID = "eleven_monolingual_v1"
ELEVENLABS_PRONUNCIATION_DICT_ID = "YTCijUQ2ewUrqpjuPh2X"
ELEVENLABS_PRONUNCIATION_VERSION_ID = "YQc3AxybKEN3eEXWoAT3"

# --- Anthropic ---
# Get your API key from https://console.anthropic.com
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-opus-4-6"

# --- Sefaria ---
SEFARIA_CALENDARS_URL = "https://www.sefaria.org/api/calendars"
SEFARIA_TEXTS_URL = "https://www.sefaria.org/api/v3/texts"
RASHI_COMMENT_LIMIT = 100  # Max Rashi comments to send to Claude

# --- Local Paths ---
DOCS_DIR = "docs"
EPISODES_DIR = f"{DOCS_DIR}/episodes"
FEED_PATH = f"{DOCS_DIR}/feed.xml"
SCRIPTS_DIR = "scripts"
