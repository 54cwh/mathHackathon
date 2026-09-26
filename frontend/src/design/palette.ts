/**
 * 品牌色板 + Arena 角色映射的**唯一数据源**（owner：李辰钊）。
 *
 * 本文件由三条规则约束，由 `npm run lint:design`（`scripts/lint-design.mjs`）强制：
 *
 *  1. **`#RRGGBB` 只允许出现在本文件**。`src/**` 其余任何文件出现 hex 字面量即 lint 失败。
 *     理由：审计查出 `panels/DanioArenaPanel.tsx` 里散落 11 个硬编码 hex，改色要逐行找。
 *  2. 组件只用两种写法：Tailwind 类名（`bg-brand-ink` / `text-brand-foam`，来自 `tailwind.config.ts`
 *     的 `colors.brand`），或 `import { BRAND, ARENA } from "@/design/palette"` 取常量。
 *  3. **本文件只放品牌 24 色**。「外壳 token」（`--background` 等 22 个 shadcn 变量）的 owner 是
 *     `src/index.css` 的 `:root`，**不在本文件** —— 一处一 owner，避免审计 §3 指出的「双 owner」。
 *
 * 冻结：2026-09-26 v0.1（`artifacts/assets_placeholder/ui_reference_prompts.md` §候选色板）。
 * 上游 = 该节取色结果；下游 = Tailwind 类名 / Canvas 绘制 / 素材提示词的 `{色板}` 占位。
 * **改这里 = 改色板**，改完须同步素材提示词与 `{色板}`。
 */
export const BRAND = {
  /* ---- 深色骨架 / 水体 ---- */
  ink: "#1A1C2C",
  slateShadow: "#333C57",
  blueGrey: "#566C86",
  deepWater: "#1E6F9F",
  midWater: "#2E9BC7",
  shallowWater: "#6FD3E8",
  foam: "#B6F0F5",
  /* ---- 植被 ---- */
  deepGrass: "#2F6B3A",
  grassGreen: "#4C9A3F",
  lightGrass: "#8ED14B",
  /* ---- 木石沙 ---- */
  barkDark: "#5A3A22",
  woodBrown: "#8A5A33",
  sandWarm: "#C6854A",
  sandLight: "#E8C179",
  /* ---- 强调 / 语义 ---- */
  amber: "#F2A93B",
  coralOrange: "#F08A5D",
  dangerRed: "#E4595C",
  mutationViolet: "#9B5DE5",
  /* ---- 中性 ---- */
  white: "#FFFFFF",
  bone: "#D9E0E8",
  stoneGrey: "#7A8A99",
  stoneShadow: "#4A4A5A",
  /* ---- 鱼（生 Object 侧自用两档） ---- */
  fishNavy: "#2B3A67",
  fishBlue: "#5C7CB8",
} as const;

export type BrandColor = keyof typeof BRAND;

/**
 * Arena 画布的角色映射 —— **审计的收敛结果**。
 *
 * 改造前：`panels/DanioArenaPanel.tsx` 里硬编码 **11 个 hex**，其中 3 个是手打的 Tailwind 灰
 * （`#374151` gray-700 / `#6B7280` gray-500 / `#9CA3AF` gray-400），**都不在 24 色里**。
 * 改造后：**11 → 0**，全部指回品牌色。
 *
 * ⚠️ **这是可见的配色变化，不是纯重命名**（记入交付说明，不要当成无感重构）：
 *  - 画布底 `#0B1220` → `ink #1A1C2C`（略提亮，仍是全场最暗一级）；
 *  - 鱼由「琥珀/蓝双色描边」改为「ink 统一描边 + 选中=amber、未选中=fishBlue 填充」
 *    （像素画惯例：轮廓统一，靠填充区分）；
 *  - 猎物 `#34D399` → `lightGrass`；捕食者 → `dangerRed`；能量环 → `grassGreen`/`dangerRed`。
 */
export const ARENA = {
  /** 画布底（水体最深一级） */
  canvas: BRAND.ink,
  /** 障碍物两档 */
  obstacleDark: BRAND.stoneShadow,
  obstacleLight: BRAND.stoneGrey,
  /** 猎物（食物）—— 亮绿读作"吃的" */
  prey: BRAND.lightGrass,
  /** 捕食者 */
  predator: BRAND.dangerRed,
  /** 鱼：选中 / 未选中 */
  fishSelected: BRAND.amber,
  fishUnselected: BRAND.fishBlue,
  /** 所有生物统一轮廓色（像素画惯例：轮廓一致，靠填充区分） */
  outline: BRAND.ink,
  /** 能量环：充足 / 告急 */
  energyOk: BRAND.grassGreen,
  energyLow: BRAND.dangerRed,
  /** 画布内 HUD 文字（step 计数等） */
  hudText: BRAND.stoneGrey,
} as const;

/**
 * 圆角基准 —— **`R2-4 无圆角` 的代码落点**。
 *
 * 这条同时覆盖两份此前互相自洽、但都与 R2-4 相反的定义：
 *  - `frontend/README.md:157`（原写 `圆角 | 10px`）
 *  - `frontend/src/index.css:39`（原写 `--radius: 0.625rem`）
 *
 * `0` 是**唯一合法值**；`tailwind.config.ts` 的 `borderRadius` 整段被硬零化，
 * 因此即便有人写 `rounded-lg` / `rounded-full` 也拿不到圆角（lint 另有类名检查）。
 */
export const RADIUS = "0" as const;
