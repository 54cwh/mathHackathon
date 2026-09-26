/**
 * 视觉规范静态检查（`npm run lint:design`）。**只读**，不改任何文件。
 *
 * 存在的理由：规范写在文档里会漂，写成检查才不会漂。审计查出的事实是
 * `panels/DanioArenaPanel.tsx` 里散落 11 个硬编码 hex（其中 3 个是手打的 Tailwind 灰），
 * 而「改一处颜色要满仓库找」正是两人并行时最容易互相踩的地方。
 *
 * 检查项（任一失败即 exit 1）：
 *  R1  `#RRGGBB` 只允许出现在 `src/design/palette.ts`（品牌色唯一 owner）。
 *  R2  禁止 `rounded` / `rounded-*`（除 `rounded-none`）——`R2-4 无圆角`。
 *  R3  `index.css` 的 `--radius` 必须是 `0rem`（R2-4 的代码落点）。
 *  R4  `palette.ts` 的 `BRAND` 必须恰好 24 项（防误删/误加）。
 *  R5  `palette.ts` 不得含 `#FF00FF`（洋红是抠图键控色，进了色板会挖掉素材本身）。
 *
 * 已知局限（诚实声明）：注释剥离是**逐行状态机**，只处理 `/* … *​/` 块注释与
 * `//` 行注释（且 `//` 前是 `:` 时不视为注释，避开 `https://`）。
 * 若将来出现模板字符串里拼 hex 之类的写法，本检查抓不到 —— 那种情况请直接不要写。
 */
import { readFile, readdir } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const SRC = join(ROOT, "src");

const PALETTE_REL = "src/design/palette.ts"; // 正斜杠：与 relative(...) 归一化后的形式比对
const ALLOW_HEX = new Set([PALETTE_REL]);

const violations = [];
const bad = (rule, file, line, msg) =>
  violations.push({ rule, file: relative(ROOT, file).split(sep).join("/"), line, msg });

/** 递归收集 src 下的 .ts/.tsx/.css */
async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else if (/\.(ts|tsx|css)$/.test(entry.name)) out.push(full);
  }
  return out;
}

/** 逐行剥注释，返回 {text, line} 数组。 */
function stripComments(source) {
  const lines = source.split(/\r?\n/);
  const out = [];
  let inBlock = false;
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];
    let res = "";
    let idx = 0;
    while (idx < line.length) {
      if (inBlock) {
        const end = line.indexOf("*/", idx);
        if (end === -1) { idx = line.length; break; }
        inBlock = false;
        idx = end + 2;
        continue;
      }
      const open = line.indexOf("/*", idx);
      const slash = line.indexOf("//", idx);
      const isUrl = slash > 0 && line[slash - 1] === ":";
      const lineComment = slash !== -1 && !isUrl;
      if (open !== -1 && (lineComment ? open < slash : true)) {
        res += line.slice(idx, open);
        const end = line.indexOf("*/", open + 2);
        if (end === -1) { inBlock = true; idx = line.length; break; }
        idx = end + 2;
        continue;
      }
      if (lineComment) { res += line.slice(idx, slash); idx = line.length; break; }
      res += line.slice(idx);
      break;
    }
    out.push({ text: res, line: i + 1 });
  }
  return out;
}

const HEX = /#[0-9A-Fa-f]{6}\b/;
const ROUNDED = /(^|[\s"'`])rounded(?!-none)(-[a-z0-9]+)?\b/;

const files = await walk(SRC);
for (const file of files) {
  const rel = relative(ROOT, file).split(sep).join("/");
  const stripped = stripComments(await readFile(file, "utf8"));

  if (!ALLOW_HEX.has(rel)) {
    for (const { text, line } of stripped) {
      const m = text.match(HEX);
      if (m) bad("R1", file, line, `出现 hex 字面量 ${m[0]}；品牌色只在 ${PALETTE_REL} 定义`);
    }
  }
  for (const { text, line } of stripped) {
    if (ROUNDED.test(text)) bad("R2", file, line, "出现 rounded 类（R2-4 无圆角）");
  }
}

/* R3：--radius 必须为 0rem */
const cssLines = stripComments(await readFile(join(SRC, "index.css"), "utf8"));
const radiusLine = cssLines.find(({ text }) => /--radius\s*:/.test(text));
if (!radiusLine) bad("R3", join(SRC, "index.css"), 0, "未找到 --radius 声明");
else if (!/--radius\s*:\s*0(rem|px|)\s*;/.test(radiusLine.text))
  bad("R3", join(SRC, "index.css"), radiusLine.line, "--radius 必须为 0（R2-4 无圆角）");

/* R4 / R5：色板本身 */
const paletteSrc = await readFile(join(ROOT, PALETTE_REL), "utf8");
const brandBlock = paletteSrc.match(/export const BRAND = \{([\s\S]*?)\n\} as const;/);
if (!brandBlock) bad("R4", join(ROOT, PALETTE_REL), 0, "未找到 BRAND 定义");
else {
  const count = (brandBlock[1].match(/^\s*[a-zA-Z][a-zA-Z0-9]*\s*:\s*"#/gm) || []).length;
  if (count !== 24) bad("R4", join(ROOT, PALETTE_REL), 0, `BRAND 有 ${count} 项，应为 24`);
}
if (/#FF00FF/i.test(paletteSrc))
  bad("R5", join(ROOT, PALETTE_REL), 0, "色板含 #FF00FF（抠图键控色）");

/* 输出 */
if (violations.length === 0) {
  console.log(`lint:design OK（扫描 ${files.length} 个文件，R1–R5 全过）`);
  process.exit(0);
}
console.error(`lint:design 失败：${violations.length} 处\n`);
for (const v of violations) {
  console.error(`  [${v.rule}] ${v.file}:${v.line}  ${v.msg}`);
}
console.error("\n规则说明见 scripts/lint-design.mjs 顶部；R2-4 / Q4 等决策见 frontend/交互与可视化.md §13。");
process.exit(1);
