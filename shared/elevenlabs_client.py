"""
Hedge Edge - ElevenLabs TTS Client
===================================
Text-to-speech generation via ElevenLabs API for video voiceovers,
product demos, and content production.

Capabilities:
    - Text-to-speech generation (multiple voices)
    - Voice listing and selection
    - Audio file output (MP3/WAV)
    - Voice settings control (stability, similarity, style)

Auth: ELEVENLABS_API_KEY in .env
Docs: https://elevenlabs.io/docs/api-reference

Usage:
    from shared.elevenlabs_client import generate_speech, list_voices, get_voice
"""

import os
import re
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://api.elevenlabs.io/v1"


def _api_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY must be set in .env")
    return key


def _headers(accept_json: bool = True) -> dict:
    h = {"xi-api-key": _api_key()}
    if accept_json:
        h["Content-Type"] = "application/json"
    return h


def list_voices() -> list[dict]:
    """List all available voices."""
    r = requests.get(f"{BASE_URL}/voices", headers=_headers(), timeout=15)
    r.raise_for_status()
    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category", "unknown"),
            "labels": v.get("labels", {}),
        }
        for v in r.json().get("voices", [])
    ]


def get_voice(voice_id: str) -> dict:
    """Get details for a specific voice."""
    r = requests.get(f"{BASE_URL}/voices/{voice_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def generate_speech(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    model_id: str = "eleven_multilingual_v2",
    output_path: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    use_speaker_boost: bool = True,
    output_format: str = "mp3_44100_128",
) -> str:
    """Generate speech from text and save to file."""
    if not output_path:
        ext = "mp3" if "mp3" in output_format else "wav"
        output_path = os.path.join(
            _ws_root, "Content Engine Agent",
            ".agents", "skills", "video-production",
            "resources", f"voiceover_output.{ext}"
        )

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        },
    }

    url = f"{BASE_URL}/text-to-speech/{voice_id}"
    params = {"output_format": output_format}

    r = requests.post(
        url, headers=_headers(), json=payload,
        params=params, timeout=120, stream=True,
    )
    r.raise_for_status()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return output_path


def generate_long_speech(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    model_id: str = "eleven_multilingual_v2",
    output_path: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    output_format: str = "mp3_44100_128",
    chunk_size: int = 4500,
) -> str:
    """Generate speech for long text by chunking at sentence boundaries."""
    if len(text) <= chunk_size:
        return generate_speech(
            text, voice_id, model_id, output_path,
            stability, similarity_boost, style, True, output_format
        )

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    if not output_path:
        output_path = os.path.join(
            _ws_root, "Content Engine Agent",
            ".agents", "skills", "video-production",
            "resources", "voiceover_output.mp3"
        )

    chunk_paths = []
    for i, ct in enumerate(chunks):
        cp = output_path.replace(".mp3", f"_chunk_{i:03d}.mp3")
        print(f"  Generating chunk {i+1}/{len(chunks)} ({len(ct)} chars)...")
        generate_speech(ct, voice_id, model_id, cp, stability, similarity_boost, style, True, output_format)
        chunk_paths.append(cp)

    print(f"  Merging {len(chunk_paths)} chunks...")
    with open(output_path, "wb") as outfile:
        for cp in chunk_paths:
            with open(cp, "rb") as infile:
                outfile.write(infile.read())
    for cp in chunk_paths:
        try:
            os.remove(cp)
        except OSError:
            pass
    return output_path


def get_subscription_info() -> dict:
    """Get subscription usage info."""
    r = requests.get(f"{BASE_URL}/user/subscription", headers=_headers(), timeout=10)
    r.raise_for_status()
    d = r.json()
    return {
        "tier": d.get("tier", "unknown"),
        "character_count": d.get("character_count", 0),
        "character_limit": d.get("character_limit", 0),
        "characters_remaining": d.get("character_limit", 0) - d.get("character_count", 0),
    }
