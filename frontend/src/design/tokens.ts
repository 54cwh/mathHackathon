/**
 * Shell design tokens — the single definition site for every CSS variable and
 * the radius scale. `index.css` and `tailwind.config.ts` are generated from /
 * import this module; do not hand-edit them.
 *
 * Status: `草案待确认` — values are the pre-freeze theme lifted out of
 * `index.css`. The visual freeze (`frontend/交互与可视化.md` §13) replaces them
 * from the prompt-3 palette; only this file then changes.
 */

/** Colour tokens as bare HSL triplets (`hsl()` is added by the consumer). */
export const tokens = {
  background: "213 29% 6%",
  foreground: "208 35% 93%",
  card: "217 9% 10%",
  "card-foreground": "208 35% 93%",
  popover: "217 9% 10%",
  "popover-foreground": "208 35% 93%",
  primary: "188 86% 53%",
  "primary-foreground": "213 29% 6%",
  secondary: "217 9% 16%",
  "secondary-foreground": "208 35% 93%",
  muted: "217 9% 16%",
  "muted-foreground": "214 15% 60%",
  accent: "217 9% 18%",
  "accent-foreground": "208 35% 93%",
  destructive: "0 91% 71%",
  "destructive-foreground": "213 29% 6%",
  border: "213 28% 17%",
  input: "213 28% 17%",
  ring: "188 86% 53%",
  success: "158 64% 52%",
  warning: "43 96% 56%",
  violet: "255 92% 76%",
} as const;

export type TokenName = keyof typeof tokens;

/** Corner radius — zero everywhere (rule 4: no rounded corners). */
export const RADIUS = "0";

/** Tailwind `borderRadius` scale, explicitly all-zero (avoids negative calc). */
export const BORDER_RADIUS_SCALE = {
  none: "0",
  sm: "0",
  DEFAULT: "0",
  md: "0",
  lg: "0",
  xl: "0",
  full: "0",
} as const;

/** Markers delimiting the generated token block in `index.css`. */
export const CSS_TOKENS_BEGIN = "/* @generated:design */";
export const CSS_TOKENS_END = "/* @end:design */";

/** Render the `:root { … }` token block written into `index.css`. */
export function toCssRootBlock(): string {
  const lines = Object.entries(tokens).map(([name, value]) => `    --${name}: ${value};`);
  lines.push(`    --radius: ${RADIUS};`);
  return [CSS_TOKENS_BEGIN, ...lines, CSS_TOKENS_END].join("\n");
}

type ColorValue = string | { DEFAULT: string; foreground: string };

/**
 * Tokens kept for CSS completeness but **not** remapped into Tailwind. `violet`
 * would override Tailwind's own violet scale (dead-token issue); the brand violet
 * is `brand.mutation-violet` from `design/palette.ts` instead.
 */
const TAILWIND_OMIT = new Set<TokenName>(["violet"]);

/** Render the Tailwind `theme.extend.colors` map from the tokens. */
export function toTailwindColors(): Record<string, ColorValue> {
  const colors: Record<string, ColorValue> = {};
  for (const name of Object.keys(tokens) as TokenName[]) {
    if (name.endsWith("-foreground") || TAILWIND_OMIT.has(name)) continue;
    const value = `hsl(var(--${name}))`;
    const foreground = tokens[`${name}-foreground` as TokenName];
    colors[name] = foreground ? { DEFAULT: value, foreground: `hsl(var(--${name}-foreground))` } : value;
  }
  return colors;
}
