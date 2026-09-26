import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

import { BRAND } from "./src/design/palette";
import { toTailwindColors } from "./src/design/tokens";
import { FONT_MONO_STACK, FONT_TEXT_STACK } from "./src/design/typography";

/**
 * camelCase -> kebab-case，让 Tailwind 类名是 `bg-slate-shadow` 而不是 `bg-slateShadow`。
 * 品牌色的唯一来源仍是 `src/design/palette.ts`，不为了类名好看而复制一份。
 */
const kebab = (hexByName: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(hexByName).map(([name, hex]) => [
      name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`),
      hex,
    ]),
  );

export default {
  /* 全暗、不做主题切换（原 `darkMode: ["class"]` 是死配置，已移除）。 */
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  /**
   * 永久禁生成的类名。**这不是洁癖，是修一类真实缺陷。**
   *
   * 机制：Tailwind 扫的是**原始文本**（不剥注释），所以任何与工具类同名的
   * 小写单词都会被当成候选并生成「没人用」的 CSS：
   *   - TS 对象键：`tokens.ts` 的 shell token `ring:` -> 产出 `.ring` 及其整套
   *     `--tw-ring-*` 基座（实测 22 条声明）；
   *   - 属性访问：`DNA.shadow` -> 产出 `.shadow` + `--tw-shadow*`；
   *   - 英文注释：geometry.ts 的 "snapped…"（原 "rounded to…"）-> 产出 `.rounded`。
   * 静态检查抓不到「注释/键名」这两类（它剥注释、且不把属性访问当类名），
   * 所以真正的兜底只能放在这里：**让这些类名根本不可能被生成**。
   *
   * 与 §十一 一致：本项目不用阴影 / 模糊 / glass / 渐变 / 透明度淡出 / 动画，
   * 圆角刻度也已整段归零，故禁用它们不损失任何表达力。
   */
  blocklist: [
    /* 根因：6 个「基类」——只要被切出来就会带出整套 --tw-* 基座。 */
    "ring",
    "shadow",
    "rounded",
    "blur",
    "transition",
    "animate",
    /* 圆角整套刻度（值已全为 0，禁掉不损失表达力）。 */
    "rounded-none", "rounded-sm", "rounded-md", "rounded-lg",
    "rounded-xl", "rounded-2xl", "rounded-3xl", "rounded-full",
    /* 阴影 / 投影刻度。 */
    "shadow-sm", "shadow-md", "shadow-lg", "shadow-xl", "shadow-2xl",
    "shadow-inner", "shadow-none",
    "drop-shadow", "drop-shadow-sm", "drop-shadow-md",
    "drop-shadow-lg", "drop-shadow-xl", "drop-shadow-2xl",
    /* 模糊 / glass。 */
    "blur-sm", "blur-md", "blur-lg", "blur-xl", "blur-2xl", "blur-3xl",
    "backdrop-blur", "backdrop-blur-sm", "backdrop-blur-md",
    "backdrop-blur-lg", "backdrop-blur-xl",
    /* 过渡 / 动画。 */
    "transition-colors", "transition-all", "transition-opacity",
    "transition-shadow", "transition-transform", "transition-none",
    "animate-spin", "animate-ping", "animate-pulse", "animate-bounce",
    "animate-in", "animate-out",
  ],
  theme: {
    /* R2-4 无圆角：整段替换默认圆角刻度（连 `rounded` 与 `rounded-full` 一并归零）。 */
    borderRadius: {
      none: "0",
      sm: "0",
      DEFAULT: "0",
      md: "0",
      lg: "0",
      xl: "0",
      "2xl": "0",
      "3xl": "0",
      full: "0",
    },
    extend: {
      colors: {
        /* 外壳 token（值 owner：`src/index.css`；本层由 `src/design/tokens.ts` 生成）。 */
        ...toTailwindColors(),
        /* 品牌 24 色（owner：`src/design/palette.ts`）——
           用法：`bg-brand-ink` / `text-brand-foam` / `border-brand-stone-shadow` … */
        brand: kebab(BRAND),
      },
      fontFamily: {
        sans: FONT_TEXT_STACK,
        mono: FONT_MONO_STACK,
      },
    },
  },
  plugins: [animate],
} satisfies Config;
