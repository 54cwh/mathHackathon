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
