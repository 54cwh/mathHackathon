import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

import { BRAND } from "./src/design/palette";

/**
 * camelCase -> kebab-case，让 Tailwind 类名是 `bg-slate-shadow` 而不是 `bg-slateShadow`。
 * 这样品牌色的**唯一来源仍是 `src/design/palette.ts`**，不为了类名好看而复制一份。
 */
const kebab = (hexByName: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(hexByName).map(([name, hex]) => [
      name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`),
      hex,
    ]),
  );

export default {
  /* 已移除 `darkMode: ["class"]`（Q2(c) 全暗、不做主题切换）。
     它此前就是死配置：`src/index.css` 只有 `:root` 一个主题块、无 `.dark`，
     且全库 `src/**` 无任何 `dark:` 变体（grep 实测 0 处）。 */
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    /* R2-4 无圆角：**整段替换**默认圆角刻度（不是 extend），
       连默认的 `rounded` 与 `rounded-full` 一并归零。
       数值基准：`src/design/palette.ts` 的 `RADIUS`。 */
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
        /* ---- 外壳 token（owner：`src/index.css` 的 `:root`）---- */
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        /* 注：此处原有的 `violet: "hsl(var(--violet))"` 覆盖了 Tailwind 自带的
           violet 色阶 —— 属审计 §3 记的「死 token」，品牌紫已由 `brand.mutation-violet` 承担，
           故不再在本层重定义 `violet`。 */
        /* ---- 品牌 24 色（owner：`src/design/palette.ts`）----
           用法：`bg-brand-ink` / `text-brand-foam` / `border-brand-stone-shadow` … */
        brand: kebab(BRAND),
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [animate],
} satisfies Config;
