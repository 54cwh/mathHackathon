/**
 * Typography — the single definition site for font stacks.
 *
 * Status: `草案待确认` — `Inter` / `JetBrains Mono` are declared but not yet
 * self-hosted (`视觉规范审计.md` rule 9(d)); the browser currently falls back to
 * `system-ui`. A pixel font is not chosen yet; when it is, it must be scoped to
 * labels only, with numeric data staying on the mono stack
 * (`ui_reference_prompts.md` §工程约束 2).
 */

/** Body / UI text stack. */
export const FONT_TEXT_STACK = ["Inter", "system-ui", "sans-serif"];

/** Monospace stack for DNA strings and numeric data. */
export const FONT_MONO_STACK = ["JetBrains Mono", "ui-monospace", "monospace"];
