"""
Sefaria API client for fetching the weekly Parashah name and Rashi's commentary.
No API key required — Sefaria is a free, open resource.
"""

import requests
from config import SEFARIA_CALENDARS_URL, SEFARIA_TEXTS_URL, RASHI_COMMENT_LIMIT


def get_current_parashah() -> dict:
    """
    Fetch the current week's Parashah from the Sefaria calendars API.

    Returns a dict with:
        - name: str  — display name (e.g. "Vayikra")
        - ref:  str  — Sefaria reference (e.g. "Leviticus 1:1-5:26")

    Raises RuntimeError if the Parashah cannot be found.
    """
    response = requests.get(SEFARIA_CALENDARS_URL, timeout=15)
    response.raise_for_status()
    data = response.json()

    for item in data.get("calendar_items", []):
        if item.get("title", {}).get("en") == "Parashat Hashavua":
            return {
                "name": item["displayValue"]["en"],
                "ref": item["ref"],
            }

    raise RuntimeError(
        "Could not find 'Parashat Hashavua' in Sefaria calendars response. "
        f"Available items: {[i.get('title', {}).get('en') for i in data.get('calendar_items', [])]}"
    )


def _flatten_verses(text_data) -> list[str]:
    """
    Recursively flatten nested verse/comment lists (Sefaria returns chapters as nested arrays)
    into a flat list of strings.
    """
    if isinstance(text_data, str):
        return [text_data] if text_data.strip() else []
    if isinstance(text_data, list):
        verses = []
        for item in text_data:
            verses.extend(_flatten_verses(item))
        return verses
    return []


def get_rashi_commentary(ref: str) -> str:
    """
    Fetch the English translation of Rashi's commentary on a Torah portion from Sefaria.

    Constructs the Rashi reference by prepending "Rashi on " to the parashah ref,
    e.g. "Rashi on Exodus 30:11-34:35".

    Limits the result to the first RASHI_COMMENT_LIMIT comments.
    Returns the comments joined as a single string, each on its own line.

    Raises RuntimeError if the commentary cannot be retrieved.
    """
    rashi_ref = f"Rashi on {ref}"
    url = f"{SEFARIA_TEXTS_URL}/{requests.utils.quote(rashi_ref)}"
    response = requests.get(url, params={"version": "english"}, timeout=15)
    response.raise_for_status()
    data = response.json()

    # Sefaria v3 returns text under data["versions"][0]["text"]
    versions = data.get("versions", [])
    if not versions:
        raise RuntimeError(
            f"No text versions returned for Rashi ref '{rashi_ref}'. Response: {data}"
        )

    raw_text = versions[0].get("text", [])
    comments = _flatten_verses(raw_text)

    if not comments:
        raise RuntimeError(
            f"No comments found in Sefaria response for Rashi ref '{rashi_ref}'."
        )

    limited = comments[:RASHI_COMMENT_LIMIT]
    return "\n".join(limited)
