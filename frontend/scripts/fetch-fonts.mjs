/**
 * 下载自托管字体到 `public/fonts/`，并生成 `src/design/fonts.css`（@font-face）。
 *
 * 为什么要脚本而不是手放文件（`frontend/README.md:50`「不引 CDN，现场离线」）：
 *  - 现场断网，字体**必须**在仓库里 —— 但直接提交二进制无法复核来源；
 *  - 脚本把「从哪来、取哪几个 unicode-range、落地文件名」写成可复读的代码，
 *    改字体只需改下面 FAMILIES，重跑即可。
 *
 * 用法（在 `frontend/` 下）：`node scripts/fetch-fonts.mjs`
 * 幂等：已存在的文件默认跳过；`--force` 覆盖。
 *
 * ⚠️ **采用任何字体都要登记** `docs/declaration/THIRD_PARTY.md`（该文件要求
 * 「加入任何第三方……字体……时在此登记」）。本脚本只下载，**不登记** —— 那张表在
 * 池伟豪的 lane（`docs/`），须请他登记。条子见
 * `frontend/交接-给池伟豪-前端分工与开工包.md`。
 */
import { mkdir, writeFile, access } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(HERE, "..");
const OUT_DIR = join(FRONTEND, "public", "fonts");
const CSS_OUT = join(FRONTEND, "src", "design", "fonts.css");

/* 只取 latin 子集：界面标签是英文，中文走系统字体（见交接包的字体口径）。 */
const FAMILIES = [
  { family: "Inter", spec: "Inter:wght@400;500;600;700", file: "inter-latin", weight: "400 500 600 700" },
  { family: "JetBrains Mono", spec: "JetBrains+Mono:wght@400;500", file: "jetbrains-mono-latin", weight: "400 500" },
  { family: "Press Start 2P", spec: "Press+Start+2P", file: "press-start-2p-latin", weight: "400" },
];

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

const force = process.argv.includes("--force");

async function exists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

/** 从 Google Fonts CSS2 响应里取出 `/* latin *​/` 那一块的 woff2 URL。 */
function pickLatin(css) {
  const blocks = css.split(/\/\*\s*([a-z0-9-]+)\s*\*\//i);
  for (let i = 1; i < blocks.length; i += 2) {
    const label = blocks[i].trim().toLowerCase();
    if (label !== "latin") continue;
    const m = blocks[i + 1].match(/src:\s*url\(([^)]+\.woff2)\)/);
    if (m) return m[1];
  }
  return null;
}

async function fetchText(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.text();
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  await mkdir(dirname(CSS_OUT), { recursive: true });

  const faces = [];
  for (const f of FAMILIES) {
    const cssUrl = `https://fonts.googleapis.com/css2?family=${f.spec}&display=swap`;
    const css = await fetchText(cssUrl);
    const woff2 = pickLatin(css);
    if (!woff2) throw new Error(`未在 CSS 中找到 latin 子集：${f.family}`);
    const target = join(OUT_DIR, `${f.file}.woff2`);
    if (!force && (await exists(target))) {
      console.log(`skip  ${f.family}（已存在）`);
    } else {
      const res = await fetch(woff2, { headers: { "User-Agent": UA } });
      if (!res.ok) throw new Error(`HTTP ${res.status} 下载 ${f.family}`);
      await writeFile(target, Buffer.from(await res.arrayBuffer()));
      console.log(`ok    ${f.family} -> public/fonts/${f.file}.woff2`);
    }
    faces.push(
      `@font-face {\n` +
        `  font-family: "${f.family}";\n` +
        `  font-style: normal;\n` +
        `  font-weight: ${f.weight};\n` +
        `  font-display: swap;\n` +
        `  src: url("/fonts/${f.file}.woff2") format("woff2");\n` +
        `}`,
    );
  }

  const header =
    `/* 由 scripts/fetch-fonts.mjs 生成，**不要手改**。\n` +
    ` * 重新生成：cd frontend && node scripts/fetch-fonts.mjs --force\n` +
    ` * 许可与登记：见 frontend/交接-给池伟豪-前端分工与开工包.md（须登记 THIRD_PARTY.md）。\n` +
    ` * Latin 子集 only；中文一律走系统字体（像素字体不覆盖 CJK）。 */\n\n`;
  await writeFile(CSS_OUT, header + faces.join("\n\n") + "\n");
  console.log(`\n写入 src/design/fonts.css（${faces.length} 个 @font-face）`);
}

main().catch((err) => {
  console.error(`\n失败：${err.message}`);
  console.error("若是网络问题：需联网执行一次（现场 Demo 是离线的，字体必须预先落地）。");
  process.exit(1);
});
