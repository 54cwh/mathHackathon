// Design-spec enforcement (`frontend/交互与可视化.md` §14 / 附录 A §A.2)。
// Scans src/** and exits non-zero on any hardcoded colour, radius, shadow,
// blur, gradient or colour transition. Also verifies the generated index.css
// token block matches src/design/tokens.ts (drift guard) and that the palette
// still holds exactly 24 brand colours. Palette / token / CSS files are exempt
// from the class scan (they are the definition sites) but are checked directly.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { CSS_TOKENS_BEGIN, CSS_TOKENS_END, toCssRootBlock } from "../src/design/tokens.ts";

const SRC = fileURLToPath(new URL("../src", import.meta.url));
const EXEMPT = new Set(["design/palette.ts", "design/tokens.ts", "index.css"]);
const EXTENSIONS = [".ts", ".tsx", ".css"];

// 边界断言用 (?<![\w.-]) / (?![\w-])，**不要**用 \b。
// 理由（真实踩过的陷阱）：品牌色名 `stone-shadow` 里 `-shadow` 前面是 `-`，
// 而 `-` 是非词字符 => \b 成立 => 第一个写 `bg-brand-stone-shadow` 的人会被
// 误报成「阴影」。带 lookbehind 后，`-` 与词字符都排除在外，误报消失。
// 还要排除 `.`：TS 里的**属性访问**（`DNA.shadow` / `obj.blur`）不是 class 字符串，
// 但补集里恰好含 `shadow` 这类词 —— 本规则第一次运行就抓到了自己的源码。
const RULES = [
  { name: "literal hex colour", re: /#[0-9A-Fa-f]{3,8}\b/g },
  { name: "rgb()/hsl() colour", re: /\b(?:rgb|rgba|hsl|hsla)\(/g },
  {
    name: "tailwind named colour scale",
    re: /\b(?:bg|text|border|from|to|via|ring|fill|stroke|divide|outline|accent|caret|decoration|shadow)-(?:gray|slate|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/g,
  },
  { name: "rounded*", re: /(?<![\w.-])rounded(?:-[a-z0-9]+)?(?![\w-])/g },
  { name: "shadow*", re: /(?<![\w.-])(?:drop-)?shadow(?:-[a-z0-9]+)?(?![\w-])/g },
  { name: "blur*", re: /(?<![\w.-])blur(?:-[a-z0-9]+)?(?![\w-])/g },
  { name: "backdrop-* (glass)", re: /(?<![\w.-])backdrop-[a-z0-9-]+/g },
  { name: "gradient", re: /\b(?:bg-gradient|linear-gradient|radial-gradient|conic-gradient)\b/g },
  { name: "gradient endpoint", re: /(?<![\w.-])(?:from|via|to)-[a-z-]+-[0-9]{2,3}(?![\w-])/g },
  { name: "transition* (colour interpolation)", re: /(?<![\w.-])transition(?:-[a-z0-9]+)?(?![\w-])/g },
  { name: "animate-*", re: /(?<![\w.-])animate-[a-z0-9-]+/g },
  { name: "opacity-*", re: /(?<![\w.-])opacity-[0-9]+/g },
  { name: "colour alpha suffix", re: /(?<![\w.-])(?:bg|text|border|ring|divide|outline|fill|stroke|accent|caret|decoration)-[a-z-]+\/[0-9]{1,3}(?![\w-])/g },
];

/** 仅对 .css 生效：裸 CSS 声明。类名形态的规则抓不到它们。 */
const CSS_RULES = [
  { name: "box-shadow:", re: /box-shadow\s*:/g },
  { name: "text-shadow:", re: /text-shadow\s*:/g },
  { name: "filter:", re: /(?<![-\w])filter\s*:/g },
  { name: "backdrop-filter:", re: /backdrop-filter\s*:/g },
  { name: "*-gradient()", re: /(?:linear|radial|conic)-gradient\(/g },
  { name: "transition:", re: /(?<![-\w])transition\s*:/g },
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
  // 块注释替换成等量换行（而不是空串），否则报出的行号会在第一个多行注释后整体错位。
  const stripped = readFileSync(file, "utf8").replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ""));
  const rules = rel.endsWith(".css") ? RULES.concat(CSS_RULES) : RULES;
  stripped.split("\n").forEach((line, index) => {
    const code = line.replace(/(^|\s)\/\/.*$/, "$1");
    for (const rule of rules) {
      rule.re.lastIndex = 0;
      if (rule.re.test(code)) {
        findings.push(`${rel}:${index + 1}  ${rule.name}  →  ${line.trim()}`);
      }
    }
  });
}

// ---- palette invariants（palette.ts 在扫描里 EXEMPT，故在此直接校验）--------
const paletteSrc = readFileSync(join(SRC, "design/palette.ts"), "utf8");
const brandStart = paletteSrc.indexOf("export const BRAND");
const brandEnd = paletteSrc.indexOf("export type BrandColor");
if (brandStart === -1 || brandEnd === -1 || brandEnd < brandStart) {
  findings.push("design/palette.ts  找不到 BRAND 块或 BrandColor 类型（结构被改，请同步本检查）");
} else {
  const brandBlock = paletteSrc.slice(brandStart, brandEnd);
  const brandCount = (brandBlock.match(/^ {2}[a-zA-Z]+:/gm) ?? []).length;
  if (brandCount !== 24) {
    findings.push(`design/palette.ts  BRAND 应恰好 24 色，实际 ${brandCount}（防误删 / 误加）`);
  }
}
if (/#FF00FF/i.test(paletteSrc)) {
  findings.push("design/palette.ts  含 #FF00FF（洋红是抠图键控色，进色板会挖掉素材本身）");
}

// ---- CSS 声明表：唯一 owner 是 index.css ----------------------------------
const css = readFileSync(join(SRC, "index.css"), "utf8");
const radius = /--radius:\s*([^;]+);/.exec(css);
if (!radius || !/^0(?:rem|px|em|%)?$/.test(radius[1].trim())) {
  findings.push(`index.css  --radius 必须为 0（R2-4 无圆角），实际 ${radius ? radius[1].trim() : "缺失"}`);
}

// ---- Drift guard: index.css token block must equal what tokens.ts generates ----
// 先去掉所有 CR（String.fromCharCode(13)）再取下标并比较：Windows + core.autocrlf=true
// 的检出是 CRLF，而 tokens.ts 生成 LF。**下标必须在归一化之后取** —— 用 CRLF 串算出的
// 下标去切归一化后的串会错位（两串长度不同），这是这个守卫第一版的真实 bug。
const cssLf = css.split(String.fromCharCode(13)).join("");
const start = cssLf.indexOf(CSS_TOKENS_BEGIN);
const stop = cssLf.indexOf(CSS_TOKENS_END);
if (start === -1 || stop === -1) {
  findings.push("index.css  缺少 token 生成标记（/* @generated:design */ … /* @end:design */）");
} else if (cssLf.slice(start, stop + CSS_TOKENS_END.length) !== toCssRootBlock()) {
  findings.push("index.css  token 块与 src/design/tokens.ts 不一致 → 运行 `npm run gen:design`");
}

if (findings.length > 0) {
  console.error(`lint:design 失败（${findings.length} 项）：`);
  for (const finding of findings) console.error(`  ${finding}`);
  process.exit(1);
}
console.log("lint:design 通过：无硬编码样式；palette 24 色 / --radius 0 / index.css token 块均达标。");
