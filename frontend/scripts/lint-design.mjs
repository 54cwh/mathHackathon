// Design-spec enforcement (`frontend/视觉规范审计.md` §3.5 / §7 #15).
// Scans src/** and exits non-zero on any hardcoded colour, radius, shadow,
// blur, gradient or colour transition. Also verifies the generated index.css
// token block matches src/design/tokens.ts (drift guard).
// Palette / token / CSS files are exempt (they are the definition sites).

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { CSS_TOKENS_BEGIN, CSS_TOKENS_END, toCssRootBlock } from "../src/design/tokens.ts";

const SRC = fileURLToPath(new URL("../src", import.meta.url));
const EXEMPT = new Set(["design/palette.ts", "design/tokens.ts", "index.css"]);
const EXTENSIONS = [".ts", ".tsx", ".css"];

const RULES = [
  { name: "literal hex colour", re: /#[0-9A-Fa-f]{3,8}\b/g },
  { name: "rgb()/hsl() colour", re: /\b(?:rgb|rgba|hsl|hsla)\(/g },
  {
    name: "tailwind named colour scale",
    re: /\b(?:bg|text|border|from|to|via|ring|fill|stroke|divide|outline|accent|caret|decoration|shadow)-(?:gray|slate|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/g,
  },
  { name: "rounded*", re: /\brounded(?:-[a-z0-9]+)?\b/g },
  { name: "shadow*", re: /\bshadow(?:-[a-z0-9]+)?\b/g },
  { name: "blur*", re: /\bblur(?:-[a-z0-9]+)?\b/g },
  { name: "gradient", re: /\b(?:bg-gradient|linear-gradient|radial-gradient|conic-gradient)\b/g },
  { name: "transition-colors", re: /\btransition-colors\b/g },
];

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) yield* walk(full);
    else if (EXTENSIONS.some((ext) => entry.endsWith(ext))) yield full;
  }
}

const findings = [];
for (const file of walk(SRC)) {
  const rel = relative(SRC, file).split(sep).join("/");
  if (EXEMPT.has(rel)) continue;
  const content = readFileSync(file, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const lines = content.split("\n");
  lines.forEach((line, index) => {
    const code = line.replace(/(^|\s)\/\/.*$/, "$1");
    for (const rule of RULES) {
      rule.re.lastIndex = 0;
      if (rule.re.test(code)) {
        findings.push(`${rel}:${index + 1}  ${rule.name}  →  ${line.trim()}`);
      }
    }
  });
}

// Drift guard: index.css token block must equal what tokens.ts generates.
const css = readFileSync(join(SRC, "index.css"), "utf8");
const start = css.indexOf(CSS_TOKENS_BEGIN);
const stop = css.indexOf(CSS_TOKENS_END);
if (start === -1 || stop === -1) {
  findings.push("index.css  缺少 token 生成标记（/* @generated:design */ … /* @end:design */）");
} else if (css.slice(start, stop + CSS_TOKENS_END.length) !== toCssRootBlock()) {
  findings.push("index.css  token 块与 src/design/tokens.ts 不一致 → 运行 `npm run gen:design`");
}

if (findings.length > 0) {
  console.error(`lint:design 失败（${findings.length} 项）：`);
  for (const finding of findings) console.error(`  ${finding}`);
  process.exit(1);
}
console.log("lint:design 通过：无硬编码样式；index.css token 块与 design/tokens.ts 同步。");
