"""The pipeline's creative hash, reimplemented so this repo produces the SAME value.

The warehouse joins entities to ads on a media hash that is derived from the CONTENT of the
creative, not from its URL. It is computed by the analysis service and cached in Mongo
`hash_cache.hash_id` keyed by (cache_id=brand, url); the CH export reads it from there.

That matters whenever we push rows to ClickHouse ourselves without going through the analysis
service. A hash invented here (md5 of the URL, say) looks fine in isolation and joins fine
against rows we wrote ourselves — and then silently orphans every entity the day the real
pipeline computes the genuine hash for the same creative.

Ported from meta/analysis-service/app/media_utils.py and app/engine/pipeline.py:

  image     imagehash.phash(PIL image)                                      -> 16 hex
  video     ~5 sampled frames -> imagehash.average_hash each,
            then sha256 of the concatenated frame hashes                    -> 64 hex
  carousel  sha256(json.dumps(sorted(urls)))                                -> 64 hex
  fallback  video only: sha256 of the first 2MB of bytes                    -> 64 hex

Those shapes are load-bearing: the export validates a video hash with /^[a-f0-9]{64}$/ and an
image hash with /^[a-f0-9]{16}$/ (meta/src/utils/media-identity.js), so a 16-hex value on a
video is rejected outright.

Frame sampling walks `range(0, total_frames, total_frames // 5)` and needs at least 3 frames;
if that yields too few it retries over the first 50 frames. Keep both passes — dropping the
retry changes the hash for short videos.
"""
import hashlib
import json
import math
import os
import tempfile

MIN_FRAMES = 3
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def image_hash(path_or_image):
    """phash of an image. Matches analysis-service perceptual_image_hash()."""
    import imagehash
    from PIL import Image
    img = path_or_image if hasattr(path_or_image, "mode") else Image.open(path_or_image)
    return str(imagehash.phash(img))


def video_hash(path):
    """sha256 over per-frame average_hash values. Matches download_video_hash_and_duration()."""
    import cv2
    import imagehash
    from PIL import Image

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("cannot open video")
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 10
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        duration = round(total / fps, 2) if fps > 0 and total > 0 else None
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        aspect = f"{w // math.gcd(w, h)}:{h // math.gcd(w, h)}" if w > 0 and h > 0 else "unknown"

        interval = max(1, total // 5)
        frames = []
        for strat in (range(0, total, interval),
                      range(0, min(total, 50), max(1, min(total, 50) // 5))):
            frames = []
            for idx in strat:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok or frame is None or frame.size == 0:
                    continue
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(str(imagehash.average_hash(Image.fromarray(rgb))))
                except Exception:
                    continue
            if len(frames) >= MIN_FRAMES:
                break
        if not frames:
            raise ValueError("could not extract frames")
        return hashlib.sha256("".join(frames).encode()).hexdigest(), duration, aspect
    finally:
        cap.release()


def carousel_hash(urls):
    """sha256 of the sorted url list. Matches the carousel branch of compute_hashes()."""
    return hashlib.sha256(json.dumps(sorted(urls)).encode()).hexdigest()


def hash_url(url, media_type, session=None, max_bytes=MAX_VIDEO_BYTES):
    """Download the media and return (hash, duration, aspect_ratio).

    duration/aspect are only produced for video; both are None for images.
    Raises on failure rather than inventing a value - an invented hash is worse than no row.
    """
    import requests
    get = (session or requests).get

    if media_type == "carousel" and isinstance(url, (list, tuple)):
        return carousel_hash(list(url)), None, None

    suffix = ".mp4" if media_type in ("video", "dco_video", "carousel") else ".jpg"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        downloaded = 0
        with get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise ValueError(f"media larger than {max_bytes} bytes")
                    f.write(chunk)

        if media_type in ("video", "dco_video", "carousel"):
            try:
                return video_hash(tmp)
            except Exception:
                # the service falls back to hashing the leading bytes; keep parity
                with open(tmp, "rb") as f:
                    return hashlib.sha256(f.read(2 * 1024 * 1024)).hexdigest(), None, None
        return image_hash(tmp), None, None
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def looks_like_video_hash(v):
    return bool(v) and len(str(v)) == 64 and all(c in "0123456789abcdef" for c in str(v).lower())


def looks_like_image_hash(v):
    return bool(v) and len(str(v)) == 16 and all(c in "0123456789abcdef" for c in str(v).lower())


def _selfcheck():
    """Hash a known creative twice and against a resize; phash must be stable."""
    from PIL import Image, ImageDraw
    # a smooth image with a few large shapes: what phash is designed for. A fine checkerboard
    # is pathological - downscaling destroys the high frequencies and the hash legitimately moves.
    a = Image.new("RGB", (256, 256))
    d = ImageDraw.Draw(a)
    for y in range(256):
        d.line([(0, y), (256, y)], fill=(30 + y // 3, 60 + y // 4, 160 - y // 4))
    d.ellipse([40, 40, 170, 170], fill=(240, 220, 90))
    d.rectangle([150, 160, 240, 240], fill=(200, 40, 60))
    h1 = image_hash(a)
    h2 = image_hash(a.resize((128, 128)).resize((256, 256)))
    assert looks_like_image_hash(h1), f"image hash wrong shape: {h1}"
    assert h1 == h2, f"phash not stable across a resize: {h1} != {h2}"
    assert len(carousel_hash(["b", "a"])) == 64
    assert carousel_hash(["b", "a"]) == carousel_hash(["a", "b"]), "carousel hash must be order-independent"
    print(f"ok  image={h1}  carousel={carousel_hash(['a','b'])[:16]}…")


if __name__ == "__main__":
    _selfcheck()
