// Regenerates THIRD-PARTY-NOTICES.md from package-lock.json + node_modules (production deps only).
// usage (from the repo root, after npm install): node scripts/generate-third-party-notices.cjs <ProductName>
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const root = process.cwd();
const product = process.argv[2] ?? "This product";
const out = path.join(root, "THIRD-PARTY-NOTICES.md");

const lock = JSON.parse(fs.readFileSync(path.join(root, "package-lock.json"), "utf8"));
const entries = [];
const missing = [];

for (const [p, meta] of Object.entries(lock.packages)) {
  if (!p.includes("node_modules/") || meta.dev || meta.devOptional || meta.link) continue;
  const dir = path.join(root, p);
  if (!fs.existsSync(dir)) { missing.push(p); continue; }
  const pj = JSON.parse(fs.readFileSync(path.join(dir, "package.json"), "utf8"));
  let license = pj.license ?? (pj.licenses && pj.licenses.map((l) => l.type).join(" OR "));
  if (license && typeof license === "object") license = license.type;
  const file = fs.readdirSync(dir).find((f) => /^(licen[cs]e|copying|notice)(\.|$)/i.test(f) && fs.statSync(path.join(dir, f)).isFile());
  const text = file ? fs.readFileSync(path.join(dir, file), "utf8").replace(/\r\n/g, "\n").trim() : "";
  entries.push({ name: pj.name ?? p.split("node_modules/").pop(), version: pj.version, license: license ?? "UNKNOWN", text, repo: typeof pj.repository === "string" ? pj.repository : pj.repository?.url ?? "" });
}

entries.sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version));
const seen = new Set();
const uniq = entries.filter((e) => { const k = e.name + "@" + e.version; if (seen.has(k)) return false; seen.add(k); return true; });

const groups = new Map();
for (const e of uniq) {
  const key = e.text ? crypto.createHash("sha1").update(e.text).digest("hex") : "none:" + e.license;
  if (!groups.has(key)) groups.set(key, { text: e.text, license: e.license, pkgs: [] });
  groups.get(key).pkgs.push(e);
}

let o = `THIRD-PARTY NOTICES\n\n${product} includes the open-source software listed below, which ships in its production build.\nEach component remains under its own licence and copyright. This file is generated from package-lock.json and the installed packages; regenerate it when dependencies change.
Where a component is offered under a choice of licences that includes MIT, the MIT licence is elected.
Platform-specific binaries are listed only for the platform the file was generated on.\n\n`;
o += `## Components (${uniq.length})\n\n`;
for (const e of uniq) o += `- ${e.name}@${e.version} (${e.license})\n`;
o += `\n## Licence texts\n`;
for (const g of groups.values()) {
  o += `\n----------------------------------------\n${g.pkgs.map((p) => p.name + "@" + p.version).join(", ")}\n(${g.license})\n\n`;
  o += g.text || `No licence file shipped with the package; licence declared in package.json: ${g.license}.`;
  o += "\n";
}
fs.writeFileSync(out, o);
const unknown = uniq.filter((e) => e.license === "UNKNOWN").map((e) => e.name);
const nofile = uniq.filter((e) => !e.text).length;
const kinds = {};
for (const e of uniq) kinds[e.license] = (kinds[e.license] || 0) + 1;
console.log(JSON.stringify({ components: uniq.length, missingOnDisk: missing.length, withoutLicenceFile: nofile, unknown, kinds }, null, 1));
