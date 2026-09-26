/**
 * Explicit "no value shown here" placeholder (`视觉规范审计.md` §7 #13).
 *
 * Purpose is semantic, not image-avoidance: a slot that deliberately withholds
 * a value should read as intentional rather than as "data not wired yet".
 * Enablement depends on the §4 reading (A: top bar keeps real values; B: use
 * this for the five numeric slots).
 */
export function StatusPlaceholder({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span aria-hidden className="inline-block h-3 w-8 bg-muted" />
    </span>
  );
}
