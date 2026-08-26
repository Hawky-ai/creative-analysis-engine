import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Minimal YAML subset parser — flat keys + one nesting level, strings/numbers/bools.
// Avoids a node dependency; config.yaml deliberately stays this simple.
function parseYaml(text) {
  const root = {};
  let section = null;
  for (const raw of text.split("\n")) {
    const line = raw.replace(/#.*$/, "").trimEnd();
    if (!line.trim()) continue;
    const indented = /^\s/.test(line);
    const m = line.trim().match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!m) continue;
    const [, key, valRaw] = m;
    if (!indented) {
      if (valRaw === "") { section = key; root[key] = {}; continue; }
      section = null;
      root[key] = coerce(valRaw);
    } else if (section) {
      root[section][key] = coerce(valRaw);
    }
  }
  return root;
}
function coerce(v) {
  v = v.replace(/^["']|["']$/g, "");
  if (v === "true") return true;
  if (v === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(v)) return Number(v);
  return v;
}

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const CONFIG = parseYaml(fs.readFileSync(path.join(repoRoot, "config.yaml"), "utf8"));

export function env(name, { required = true } = {}) {
  const v = process.env[name];
  if (!v && required) {
    console.error(`Missing env var ${name} — see .env.example. Inject secrets via your secret manager (e.g. \`doppler run -- ...\`); never hardcode them.`);
    process.exit(1);
  }
  return v;
}
