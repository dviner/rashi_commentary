"""
RSS feed manager for the Rashi in Brief podcast.
Creates and updates a Spotify/Apple-Podcasts-compatible feed.xml.
"""

import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

from config import (
    PODCAST_TITLE,
    PODCAST_DESCRIPTION,
    PODCAST_AUTHOR,
    PODCAST_EMAIL,
    PODCAST_LANGUAGE,
    PODCAST_CATEGORY,
    PODCAST_EXPLICIT,
    PODCAST_BASE_URL,
    COVER_IMAGE_FILENAME,
    FEED_PATH,
    DOCS_DIR,
)


def _rfc2822(dt: datetime) -> str:
    """Format a datetime as RFC 2822, as required by the RSS spec."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def _seconds_to_hhmmss(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _prettify(element: ET.Element) -> str:
    """Return a pretty-printed XML string with proper indentation."""
    raw = ET.tostring(element, encoding="unicode")
    reparsed = minidom.parseString(raw)
    return reparsed.toprettyxml(indent="  ", encoding=None)


def initialize_feed() -> None:
    """
    Create docs/feed.xml with channel metadata but no episodes.
    Only call this once — subsequent runs use add_episode().
    """
    os.makedirs(DOCS_DIR, exist_ok=True)

    cover_url = f"{PODCAST_BASE_URL}/{COVER_IMAGE_FILENAME}"
    feed_url = f"{PODCAST_BASE_URL}/feed.xml"

    # Build the RSS tree manually so we can use the itunes: namespace
    rss_attribs = {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:atom": "http://www.w3.org/2005/Atom",
    }
    rss = ET.Element("rss", attrib=rss_attribs)
    channel = ET.SubElement(rss, "channel")

    # Standard RSS channel tags
    ET.SubElement(channel, "title").text = PODCAST_TITLE
    ET.SubElement(channel, "link").text = PODCAST_BASE_URL
    ET.SubElement(channel, "language").text = PODCAST_LANGUAGE
    ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, "copyright").text = f"© {datetime.now().year} {PODCAST_AUTHOR}"

    # Atom self-link (required by many validators)
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.set("href", feed_url)
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # iTunes channel tags
    ET.SubElement(channel, "itunes:author").text = PODCAST_AUTHOR
    owner = ET.SubElement(channel, "itunes:owner")
    ET.SubElement(owner, "itunes:name").text = PODCAST_AUTHOR
    ET.SubElement(owner, "itunes:email").text = PODCAST_EMAIL
    ET.SubElement(channel, "itunes:image").set("href", cover_url)
    ET.SubElement(channel, "itunes:category").set("text", PODCAST_CATEGORY)
    ET.SubElement(channel, "itunes:explicit").text = PODCAST_EXPLICIT

    xml_str = _prettify(rss)
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"Initialized RSS feed at {FEED_PATH}")


def add_episode(
    title: str,
    description: str,
    pub_date: datetime,
    mp3_filename: str,
    mp3_size_bytes: int,
    duration_seconds: int,
) -> None:
    """
    Prepend a new <item> to the existing feed.xml.
    Initializes the feed first if feed.xml does not exist.
    """
    if not os.path.exists(FEED_PATH):
        initialize_feed()

    # Parse the existing feed
    # ElementTree strips namespace prefixes, so we register them first
    ET.register_namespace("", "")
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")

    tree = ET.parse(FEED_PATH)
    root = tree.getroot()
    channel = root.find("channel")

    mp3_url = f"{PODCAST_BASE_URL}/episodes/{mp3_filename}"

    # Remove any existing items with the same GUID to prevent duplicates
    existing_items = channel.findall("item")
    for existing in existing_items:
        guid = existing.findtext("guid")
        if guid == mp3_url:
            channel.remove(existing)
            print(f"  Replaced existing episode entry for {mp3_filename}")

    # Build the new <item>
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "pubDate").text = _rfc2822(pub_date)
    ET.SubElement(item, "guid").text = mp3_url

    enclosure = ET.SubElement(item, "enclosure")
    enclosure.set("url", mp3_url)
    enclosure.set("length", str(mp3_size_bytes))
    enclosure.set("type", "audio/mpeg")

    ET.SubElement(item, "itunes:duration").text = _seconds_to_hhmmss(duration_seconds)
    ET.SubElement(item, "itunes:explicit").text = PODCAST_EXPLICIT

    # Insert the new item as the first episode (after channel-level tags)
    # Find the position just after the last non-item child
    insert_pos = 0
    for i, child in enumerate(channel):
        if child.tag == "item":
            insert_pos = i
            break
        insert_pos = i + 1

    channel.insert(insert_pos, item)

    xml_str = _prettify(root)
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"Added episode '{title}' to {FEED_PATH}")
