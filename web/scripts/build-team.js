// Parse the Ayunika Compliance Team expert package into website-ready data.
//
// Reads:
//   expert/ayunika-compliance-team/.codebuddy-plugin/plugin.json  (team + members)
//   expert/ayunika-compliance-team/agents/<id>.md                 (bio + tools)
//   expert/ayunika-compliance-team/avatars/*.png                  (portraits + team icon)
//
// Writes:
//   web/public/team.json        (clean, frontend-consumable)
//   web/public/avatars/*.png    (copied portraits + team icon)
//
// The web/ Dockerfile builds from the web/ context only, so the generated
// team.json + avatars are committed and served statically. Re-run this script
// whenever the expert package changes: `npm run build:team`.

import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", ".."); // repo root
const PKG = resolve(ROOT, "expert", "ayunika-compliance-team");
const PLUGIN = resolve(PKG, ".codebuddy-plugin", "plugin.json");
const AGENTS_DIR = resolve(PKG, "agents");
const AVATARS_DIR = resolve(PKG, "avatars");
const OUT_DIR = resolve(__dirname, "..", "public");
const OUT_AVATARS = resolve(OUT_DIR, "avatars");
const OUT_JSON = resolve(OUT_DIR, "team.json");

const readJson = (p) => JSON.parse(readFileSync(p, "utf8"));

// Pull frontmatter `description` + the first body paragraph of an agent md.
function parseAgent(id) {
  const md = readFileSync(resolve(AGENTS_DIR, `${id}.md`), "utf8");
  const fm = md.match(/^---\s*\n([\s\S]*?)\n---/);
  const body = fm ? md.slice(fm[0].length) : md;
  const summary =
    (fm && fm[1].match(/^description:\s*(.+)$/m)?.[1].trim().replace(/^["']|["']$/g, "")) || "";

  // First non-empty paragraph after the H1 line (join hard-wrapped lines).
  let bioLines = [];
  let seenH1 = false;
  let collecting = false;
  for (const ln of body.split("\n")) {
    const t = ln.trim();
    if (!seenH1) {
      if (t.startsWith("# ")) seenH1 = true;
      continue;
    }
    if (!t) {
      if (collecting) break;
      continue;
    }
    collecting = true;
    bioLines.push(t.replace(/\*\*/g, "").replace(/`/g, ""));
  }
  return { summary, bio: bioLines.join(" ").slice(0, 280) };
}

// Tools owned per member, parsed from the team-lead "The team" table.
function parseTools() {
  const md = readFileSync(resolve(AGENTS_DIR, "ayunika-team-lead.md"), "utf8");
  const map = {};
  let inTable = false;
  for (const ln of md.split("\n")) {
    if (ln.includes("|") && ln.toLowerCase().includes("owns")) {
      inTable = true;
      continue;
    }
    if (!inTable) continue;
    if (!ln.trim().startsWith("|")) break;
    const cells = ln
      .split("|")
      .map((c) => c.trim().replace(/`/g, ""))
      .filter(Boolean);
    if (cells.length >= 4 && cells[0].startsWith("ayunika-")) {
      const tools = cells[cells.length - 1]
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      map[cells[0]] = tools;
    }
  }
  return map;
}

const plugin = readJson(PLUGIN);
const tools = parseTools();

const members = plugin.members.map((m) => {
  const a = parseAgent(m.id);
  return {
    id: m.id,
    name: m.displayName.en,
    role: m.role,
    profession: m.profession.en,
    summary: a.summary,
    bio: a.bio,
    tools: tools[m.id] || [],
    avatar: "/avatars/" + m.avatar.split("/").pop(),
  };
});

const out = {
  team: {
    name: plugin.displayName.en,
    nameZh: plugin.displayName.zh,
    summary: plugin.displayDescription.en,
    category: plugin.categoryId,
    avatar: "/avatars/team.png",
  },
  members,
};

mkdirSync(OUT_AVATARS, { recursive: true });
for (const m of plugin.members) {
  const file = m.avatar.split("/").pop();
  const src = resolve(AVATARS_DIR, file);
  if (existsSync(src)) copyFileSync(src, resolve(OUT_AVATARS, file));
}
copyFileSync(resolve(AVATARS_DIR, "team.png"), resolve(OUT_AVATARS, "team.png"));

writeFileSync(OUT_JSON, JSON.stringify(out, null, 2) + "\n", "utf8");
console.log(`Wrote ${OUT_JSON} (${members.length} members) + ${members.length + 1} avatars.`);
