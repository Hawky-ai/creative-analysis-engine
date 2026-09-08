// Fetch a media URL and return it as an inline_data part.
//
// Why inline instead of a fileData URI: Gemini 3.7/3.8 reject an external CDN fileUri
// (surfaces as a misleading `403 The caller does not have permission`); only 2.5 accepts it.
// Inline bytes work on every model, so this is the model-agnostic path.
//
// Videos are transcoded down first (ffmpeg, 480p / 2fps). The model samples frames at a low
// rate regardless, so the smaller file yields the SAME prompt-token count and the same reading
// — verified on a 19MB creative: 1.1MB transcoded vs 19MB raw, ~7k prompt tokens either way,
// identical transcript incl. verbatim on-screen text. Falls back to the original bytes when
// ffmpeg is unavailable or the transcode fails.

import { execFile } from "child_process";
import { promisify } from "util";
import fs from "fs";
import os from "os";
import path from "path";
import crypto from "crypto";

const exec = promisify(execFile);

const SCALE = process.env.MEDIA_INLINE_SCALE || "-2:480";
const FPS = process.env.MEDIA_INLINE_FPS || "2";
const CRF = process.env.MEDIA_INLINE_CRF || "32";

async function transcode(src) {
  const out = src + ".small.mp4";
  await exec("ffmpeg", [
    "-y", "-loglevel", "error", "-i", src,
    "-vf", `scale=${SCALE},fps=${FPS}`,
    "-c:v", "libx264", "-crf", CRF, "-preset", "veryfast",
    "-c:a", "aac", "-b:a", "32k",
    out,
  ], { timeout: 180000 });
  return out;
}

const FETCH_TIMEOUT_MS = Number(process.env.MEDIA_INLINE_FETCH_TIMEOUT_MS || 180000);
const FETCH_RETRIES = Number(process.env.MEDIA_INLINE_FETCH_RETRIES || 3);

// A slow CDN read must not kill the run: retry with backoff, and let the caller's own
// retry loop see a normal Error rather than an uncaught AbortError.
async function fetchBytes(url) {
  let last;
  for (let attempt = 1; attempt <= FETCH_RETRIES; attempt++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
      if (!res.ok) throw new Error(`fetch ${res.status}`);
      return Buffer.from(await res.arrayBuffer());
    } catch (err) {
      last = err;
      if (attempt < FETCH_RETRIES) await new Promise(r => setTimeout(r, 2000 * attempt));
    }
  }
  throw new Error(`media fetch failed after ${FETCH_RETRIES} attempts (${last?.message}) for ${url}`);
}

export async function inlinePart(url, mimeType = "video/mp4", { transcodeVideo = true } = {}) {
  const raw = await fetchBytes(url);

  if (!transcodeVideo || !mimeType.startsWith("video/")) {
    return { inline_data: { mime_type: mimeType, data: raw.toString("base64") } };
  }

  const tmp = path.join(os.tmpdir(), "cae-" + crypto.randomBytes(8).toString("hex") + ".mp4");
  let small = null;
  try {
    fs.writeFileSync(tmp, raw);
    small = await transcode(tmp);
    const bytes = fs.readFileSync(small);
    return { inline_data: { mime_type: "video/mp4", data: bytes.toString("base64") } };
  } catch {
    return { inline_data: { mime_type: mimeType, data: raw.toString("base64") } };
  } finally {
    for (const f of [tmp, small]) { if (f) { try { fs.unlinkSync(f); } catch {} } }
  }
}

// OpenAI-schema variant: returns a `data:` URI for the image_url field.
// Same reason as inlinePart — newer Gemini models refuse a remote CDN URL and the failure
// surfaces as a misleading 403 PERMISSION_DENIED.
const MIME_BY_EXT = {
  webp: "image/webp", jpg: "image/jpeg", jpeg: "image/jpeg",
  png: "image/png", gif: "image/gif", bmp: "image/bmp",
};

export async function inlineDataUri(url) {
  const raw = await fetchBytes(url);
  const ext = (url.split("?")[0].split(".").pop() || "").toLowerCase();
  const mime = MIME_BY_EXT[ext] || "image/jpeg";
  return `data:${mime};base64,${raw.toString("base64")}`;
}
