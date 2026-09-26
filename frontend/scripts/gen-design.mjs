// Generator: rewrite the token block in src/index.css from src/design/tokens.ts
// (`frontend/通用层设计.md` §3 rule 4 — generated artefacts are never hand-edited).

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { CSS_TOKENS_BEGIN, CSS_TOKENS_END, toCssRootBlock } from "../src/design/tokens.ts";

const CSS_PATH = fileURLToPath(new URL("../src/index.css", import.meta.url));
const source = readFileSync(CSS_PATH, "utf8");

const begin = source.indexOf(CSS_TOKENS_BEGIN);
const end = source.indexOf(CSS_TOKENS_END);
if (begin === -1 || end === -1) {
  console.error(`gen:design 失败：src/index.css 缺少 ${CSS_TOKENS_BEGIN} / ${CSS_TOKENS_END} 标记。`);
  process.exit(1);
}

const next = source.slice(0, begin) + toCssRootBlock() + source.slice(end + CSS_TOKENS_END.length);
if (next === source) {
  console.log("gen:design 无变化：src/index.css token 块已最新。");
} else {
  writeFileSync(CSS_PATH, next);
  console.log("gen:design 已更新 src/index.css 的 token 块。");
}
