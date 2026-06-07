#!/usr/bin/env python3
"""Download, extract, and exact-dedupe free music sample libraries."""

from __future__ import annotations

import hashlib
import html.parser
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/Volumes/2TBPNY/music-sample-libraries")
ARCHIVES = ROOT / "_archives"
EXTRACTED = ROOT / "extracted"
REPORTS = ROOT / "reports"
MANIFEST = ROOT / "DOWNLOAD_LINKS.md"

AUDIO_EXTS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".ogg"}


@dataclass(frozen=True)
class Library:
    name: str
    slug: str
    url: str
    source: str
    license_note: str
    rationale: str


DIRECT_LIBRARIES = [
    Library(
        "MusicRadar SampleRadar - Organic Drone Samples",
        "musicradar-organic-drone-samples",
        "https://cdn.mos.musicradar.com/musicradar-organic-drone-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-303-free-organic-drone-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Large atmospheric/drone WAV pack for ambient, scoring, transitions, and texture beds.",
    ),
    Library(
        "MusicRadar SampleRadar - Wooden Percussion Samples",
        "musicradar-wooden-percussion-samples",
        "https://cdn.mos.musicradar.com/musicradar-wooden-percussion-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-213-free-wooden-percussion-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Organic percussion one-shots and loops with real transient character.",
    ),
    Library(
        "MusicRadar SampleRadar - Bass Synth Samples",
        "musicradar-bass-synth-samples",
        "https://cdn.mos.musicradar.com/musicradar-bass-synth-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-250-free-bass-synth-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Useful low-end multisamples and loops across analogue-style and digital synth basses.",
    ),
    Library(
        "MusicRadar SampleRadar - Glitch Drums",
        "musicradar-glitch-drums-samples",
        "https://cdn.mos.musicradar.com/audio/musicradar-glitch-drums-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-345-free-glitch-drums-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Processed electronic drum loops for IDM, breaks, and experimental rhythm beds.",
    ),
    Library(
        "MusicRadar SampleRadar - Modular Percussion",
        "musicradar-modular-percussion-samples",
        "https://cdn.mos.musicradar.com/musicradar-modular-percussion-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-497-free-modular-percussion-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Eurorack-style percussive loops, hits, and FX.",
    ),
    Library(
        "MusicRadar SampleRadar - Processed 808 and 909",
        "musicradar-processed-808-909-samples",
        "https://cdn.mos.musicradar.com/musicradar-sampleradar-processed-808-909-samples.zip",
        "https://www.musicradar.com/music-tech/samples/sampleradar-167-free-processed-808-and-909-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Warped classic drum-machine material for beats and loops.",
    ),
    Library(
        "MusicRadar SampleRadar - Analogue Drum Samples",
        "musicradar-analogue-drums-samples",
        "https://cdn.mos.musicradar.com/audio/samples/sampleradar-analogue-drums-samples.zip",
        "https://www.musicradar.com/news/sampleradar-298-free-analogue-drum-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Classic analogue drum one-shots and loops.",
    ),
    Library(
        "MusicRadar SampleRadar - Drum and Bass Essentials",
        "musicradar-drum-and-bass-essentials-samples",
        "https://cdn.mos.musicradar.com/audio/musicradar-drum-and-bass-essentials-samples.zip",
        "https://www.musicradar.com/news/sampleradar-drum-and-bass-essentials-samples",
        "Royalty-free; use in music allowed; redistribution of sample pack not allowed.",
        "Breaks, basses, FX, and one-shots for faster electronic production.",
    ),
    Library(
        "VCSL - Versilian Community Sample Library SFZ Build",
        "vcsl-1.2.2-rc",
        "https://www.dropbox.com/s/t9i75ur4i0x0n1j/VCSL-1.2.2-RC.zip?dl=1",
        "https://github.com/sgossner/VCSL/releases/tag/v1.2.2-RC",
        "CC0 / public-domain dedication per VCSL README.",
        "Large general-purpose open instrument sample library with SFZ mappings.",
    ),
    Library(
        "MusicRadar SampleRadar - Hip-Hop Samples",
        "musicradar-hiphop-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-hiphop-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Direct hip-hop-oriented drum, bass, and loop material.",
    ),
    Library(
        "MusicRadar SampleRadar - Crate Digger Samples",
        "musicradar-crate-digger-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-crate-digger-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Dusty, sample-flip-style source material for boom-bap and collage production.",
    ),
    Library(
        "MusicRadar SampleRadar - Sampled Funk and Soul",
        "musicradar-sampled-funk-soul-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-sampled-funk-soul-samples.zip",
        "https://soundcloud.com/musicradar-com/sets/sampleradar-264-free-sampled",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Funk/soul bass, guitar, and processed instrumental phrases closer to classic sample-based hip-hop.",
    ),
    Library(
        "MusicRadar SampleRadar - Dusty Funk Samples",
        "musicradar-dusty-funk-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-dusty-funk-samples.zip",
        "https://www.noizefield.com/news/sampleradar-releases-268-free-dusty-funk-samples",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Dusty funk loops and hits for soul/boom-bap texture.",
    ),
    Library(
        "MusicRadar SampleRadar - Soul Funk Samples",
        "musicradar-soul-funk-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-soul-funk-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Soul/funk groove material that fits chopped-R&B and sample-based production.",
    ),
    Library(
        "MusicRadar SampleRadar - Funk Guitar Samples",
        "musicradar-funk-guitar-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-funk-guitar-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Guitar chops and riffs suitable for warm neo-soul or Kanye-style flips.",
    ),
    Library(
        "MusicRadar SampleRadar - Funk Samples",
        "musicradar-funk-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-funk-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Straight funk loops and one-shots for sample chopping.",
    ),
    Library(
        "MusicRadar SampleRadar - Jazz Keys Samples",
        "musicradar-jazz-keys-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-jazz-keys-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Keys material for soulful chord beds and Frank Ocean-style harmony sketches.",
    ),
    Library(
        "MusicRadar SampleRadar - Jazz Groove Samples",
        "musicradar-jazz-groove-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-jazz-groove-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Jazz grooves and phrases useful for chopped soul/jazz-rap production.",
    ),
    Library(
        "MusicRadar SampleRadar - Noise, Hiss and Crackle",
        "musicradar-noise-hiss-crackle-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-noise-hiss-crackle-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Vinyl/tape/texture layer material for lo-fi, soul, and sample-collage beats.",
    ),
    Library(
        "MusicRadar SampleRadar - Cosmic Soul Samples",
        "musicradar-cosmic-soul-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-cosmic-soul-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Soulful, spacious melodic material for R&B-adjacent production.",
    ),
    Library(
        "MusicRadar SampleRadar - Female Vocal Samples",
        "musicradar-female-vocal-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-female-vocal-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Vocal one-shots and phrases for R&B/soul hooks and texture.",
    ),
    Library(
        "MusicRadar SampleRadar - Downtempo Dreams",
        "musicradar-downtempo-dreams-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-downtempo-dreams-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Slower atmospheric and melodic material better aligned with hip-hop/R&B than club genres.",
    ),
    Library(
        "MusicRadar SampleRadar - Drum Break Samples",
        "musicradar-drum-break-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-drum-break-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Breaks for chopping into boom-bap and soul-sample drums.",
    ),
    Library(
        "MusicRadar SampleRadar - Essential Drumkit Samples",
        "musicradar-essential-drumkit-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-essential-drumkit-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "General drum-kit one-shots to build custom hip-hop kits.",
    ),
    Library(
        "MusicRadar SampleRadar - Cartoon Caper Samples",
        "musicradar-cartoon-caper-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-cartoon-caper-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Short comic stings and exaggerated sounds for funny drops and meme-ish edits.",
    ),
    Library(
        "MusicRadar SampleRadar - Gangster Sting Samples",
        "musicradar-gangster-sting-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-gangster-sting-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Short dramatic stabs/stings for beat tags, transitions, and comedic punctuation.",
    ),
    Library(
        "MusicRadar SampleRadar - Radiosonics Samples",
        "musicradar-radiosonics-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-radiosonics-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Radio-style blips, sweeps, tuning, and odd short FX for sample-collage moments.",
    ),
    Library(
        "MusicRadar SampleRadar - Robot Samples",
        "musicradar-robot-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-robot-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Short robotic vocal-ish FX and bleeps for funny ad-libs and fills.",
    ),
    Library(
        "MusicRadar SampleRadar - Found Sound Samples",
        "musicradar-found-sound-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-found-sound-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Odd short everyday sounds for ear-candy, skits, and transition details.",
    ),
    Library(
        "MusicRadar SampleRadar - Real World FX Samples",
        "musicradar-real-world-fx-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-real-world-fx-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "Short non-musical FX useful for meme timing and texture layers.",
    ),
    Library(
        "MusicRadar SampleRadar - Effect Samples",
        "musicradar-effect-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-effect-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "General short effects for drops, edits, beat switches, and jokes.",
    ),
    Library(
        "MusicRadar SampleRadar - FX Samples",
        "musicradar-fx-samples",
        "https://cdn.mos.musicradar.com/audio/samples/musicradar-fx-samples.zip",
        "https://www.reddit.com/r/WeAreTheMusicMakers/comments/cpk0je/musicradar_royalty_free_samples_consolidated/",
        "Royalty-free MusicRadar/SampleRadar pack; use in music allowed; redistribution of sample pack not allowed.",
        "More short effects and transition sounds.",
    ),
]

IOWA_PAGES = [
]

MANUAL_LINKS = [
    (
        "SignatureSounds.org free CC0 packs, surfaced via Reddit",
        "https://signaturesounds.org/",
        "Reddit post: https://www.reddit.com/r/musicproduction/comments/1i0kk6m/50_free_music_and_sound_sample_packs_all_high/",
        "Many free CC0 packs, but downloads are individual Squarespace commerce flows rather than direct stable ZIP URLs.",
    ),
    (
        "Producer Space - 18 CC0 sample packs",
        "https://producerspace.com/spanish-dance-vocals/",
        "MEGA download page from source site.",
        "2.3GB one-download CC0 pack; MEGA is better handled manually unless megatools is installed/configured.",
    ),
    (
        "99Sounds - Music Loops",
        "https://99sounds.org/music-loops/",
        "Free Gumroad checkout.",
        "Royalty-free 700MB WAV/Serum/MIDI pack, but distributed through Gumroad.",
    ),
    (
        "SampleSwap",
        "https://sampleswap.org/",
        "Browse free individual samples or paid one-shot full-library download.",
        "Large 44.1kHz WAV collection; full 9.4GB ZIP is not a free direct endpoint.",
    ),
    (
        "Philharmonia Orchestra sound samples",
        "https://philharmonia.co.uk/resources/sound-samples/",
        "Manual browsing.",
        "Useful orchestral source, but not exposed as a simple bulk ZIP from the public pages.",
    ),
    (
        "University of Iowa Musical Instrument Samples",
        "https://theremin.music.uiowa.edu/MIS.html",
        "Manual browsing.",
        "High-quality freely usable instrument samples; auto-download skipped because the public archive uses literal-space URLs.",
    ),
    (
        "Freesound",
        "https://freesound.org/",
        "Manual/API account flow.",
        "Great Reddit-recommended source, but licenses vary and downloads usually require account/API handling.",
    ),
    (
        "Freesound short vocal/outtake searches",
        "https://freesound.org/search/?q=funny+voice&f=duration%3A%5B0+TO+10%5D",
        "Manual filtering recommended.",
        "Good for <10s funny voice/outtake material; check each clip license before using commercially.",
    ),
    (
        "Freesound short cartoon/sting searches",
        "https://freesound.org/search/?q=cartoon+sting&f=duration%3A%5B0+TO+10%5D",
        "Manual filtering recommended.",
        "Good source for meme-like stings without using copyrighted movie/social-media rips.",
    ),
]


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def ensure_dirs() -> None:
    for path in (ROOT, ARCHIVES, EXTRACTED, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def archive_path(lib: Library) -> Path:
    return ARCHIVES / f"{lib.slug}.zip"


def fetch_iowa_libraries() -> list[Library]:
    libs: list[Library] = []
    for title, slug, page_url in IOWA_PAGES:
        with urllib.request.urlopen(page_url, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        parser = LinkParser()
        parser.feed(html)
        seen: set[str] = set()
        zip_links = []
        for href in parser.links:
            if not href.lower().endswith(".zip"):
                continue
            url = urllib.parse.urljoin(page_url, href)
            if url in seen:
                continue
            seen.add(url)
            zip_links.append(url)
        for url in zip_links:
            file_slug = re.sub(r"[^a-z0-9]+", "-", Path(urllib.parse.urlparse(url).path).stem.lower()).strip("-")
            libs.append(
                Library(
                    f"{title} - {Path(urllib.parse.urlparse(url).path).name}",
                    f"{slug}-{file_slug}",
                    url,
                    page_url,
                    "Freely downloadable and usable without restrictions per University of Iowa MIS page.",
                    "Clean 24-bit instrument multisamples from the University of Iowa MIS collection.",
                )
            )
    return libs


def download(lib: Library) -> Path:
    dest = archive_path(lib)
    if dest.exists() and dest.stat().st_size > 0:
        if test_zip(dest):
            print(f"skip existing complete archive: {dest}")
            return dest
        print(f"resume partial or invalid archive: {dest}")
    run([
        "curl",
        "-L",
        "--fail",
        "--retry",
        "4",
        "--retry-delay",
        "3",
        "-C",
        "-",
        "-o",
        str(dest),
        lib.url,
    ])
    return dest


def test_zip(path: Path) -> bool:
    result = subprocess.run(["unzip", "-tq", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (REPORTS / "zip-test.log").open("a").write(f"\n## {path}\n{result.stdout}\n")
    return result.returncode == 0


def extract(lib: Library, archive: Path) -> None:
    marker = EXTRACTED / lib.slug / ".extracted"
    if marker.exists():
        print(f"skip existing extraction: {marker.parent}")
        return
    out = EXTRACTED / lib.slug
    out.mkdir(parents=True, exist_ok=True)
    run(["unzip", "-q", "-n", str(archive), "-d", str(out)])
    marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z\n"), encoding="utf-8")


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def dedupe_audio() -> tuple[int, int]:
    groups: dict[tuple[int, str], list[Path]] = {}
    for path in EXTRACTED.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
            continue
        groups.setdefault((path.stat().st_size, sha256(path)), []).append(path)

    duplicate_sets = [sorted(paths) for paths in groups.values() if len(paths) > 1]
    report_lines = []
    removed = 0
    reclaimed = 0
    for paths in duplicate_sets:
        keep = paths[0]
        report_lines.append(f"KEEP {keep}")
        for duplicate in paths[1:]:
            size = duplicate.stat().st_size
            duplicate.unlink()
            removed += 1
            reclaimed += size
            report_lines.append(f"DELETE {duplicate}")
        report_lines.append("")

    report = REPORTS / "audio-dedupe-report.txt"
    report.write_text("\n".join(report_lines) if report_lines else "No exact duplicate audio files found.\n", encoding="utf-8")
    return removed, reclaimed


def write_manifest(libs: list[Library], failed: list[tuple[Library, str]], removed: int, reclaimed: int) -> None:
    archive_count = len([p for p in ARCHIVES.glob("*.zip") if p.is_file()])
    audio_count = sum(1 for p in EXTRACTED.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    archive_size = sum(p.stat().st_size for p in ARCHIVES.glob("*.zip") if p.is_file())
    extracted_size = sum(p.stat().st_size for p in EXTRACTED.rglob("*") if p.is_file())

    downloaded_rows = "\n".join(
        f"- **{lib.name}**\n  - Source: {lib.source}\n  - Archive: `{archive_path(lib)}`\n  - License/use: {lib.license_note}\n  - Why: {lib.rationale}"
        for lib in libs
        if archive_path(lib).exists()
    )
    failed_rows = "\n".join(f"- **{lib.name}**: {reason}\n  - URL: {lib.url}" for lib, reason in failed) or "- None"
    manual_rows = "\n".join(
        f"- **{name}**\n  - Link: {url}\n  - Context: {context}\n  - Note: {note}"
        for name, url, context, note in MANUAL_LINKS
    )

    MANIFEST.write_text(
        textwrap.dedent(
            f"""\
            # Music Sample Libraries

            Target folder: `{ROOT}`

            ## Local Inventory

            - Archives downloaded: {archive_count}
            - Archive bytes: {archive_size:,}
            - Extracted bytes after dedupe: {extracted_size:,}
            - Audio files after dedupe: {audio_count:,}
            - Exact duplicate audio files removed: {removed:,}
            - Approx bytes reclaimed: {reclaimed:,}
            - Dedupe report: `{REPORTS / "audio-dedupe-report.txt"}`

            ## Downloaded And Extracted

            {downloaded_rows}

            ## Failed Or Skipped Direct Downloads

            {failed_rows}

            ## Manual / Reddit-Derived Download Leads

            {manual_rows}

            ## Notes

            I only downloaded sources with direct archive URLs and a clear free/royalty-free/CC0/unrestricted-use statement from the source page.
            Reddit posts were used as discovery leads, not as final license authority.
            MusicRadar/SampleRadar packs allow use in music but ask that the packs themselves not be redistributed.
            """
        ),
        encoding="utf-8",
    )


def main() -> int:
    ensure_dirs()
    libs = DIRECT_LIBRARIES + fetch_iowa_libraries()
    failed: list[tuple[Library, str]] = []
    downloaded: list[Library] = []

    for lib in libs:
        print(f"\n== {lib.name} ==")
        try:
            archive = download(lib)
            if not test_zip(archive):
                failed.append((lib, "Downloaded file failed unzip integrity test."))
                continue
            extract(lib, archive)
            downloaded.append(lib)
        except Exception as exc:
            failed.append((lib, repr(exc)))

    removed, reclaimed = dedupe_audio()
    write_manifest(downloaded, failed, removed, reclaimed)
    print(f"\nDone: {MANIFEST}")
    if failed:
        print(f"Failures: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
