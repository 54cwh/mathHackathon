/**
 * 激活向量的语义读数（`交互与可视化.md` §7，2026-09-27 定稿）。
 *
 * **纯复算模型公式，不伪造**：把激活向量 `h` 按*该鱼自己的发育产物*（`cell_type` + `positions`，
 * 与 `h` 同序、同个体）分组求均值；左右 motor 的二分与 ω 驱动严格照 `DanioNet §5`
 * （`motor_sides`：motor 池按发育坐标 `x` 中位数二分；`ω = tanh(L − R)`）。
 *
 * 缺域（该鱼没有该类神经元）一律记 `null` —— **不补 0**（缺失 ≠ 0）。
 */

/** 六类发育域的顺序 = `configs/default_model.yaml::development.domains`，也是 `cell_type` 的下标。 */
export const DOMAIN_NAMES = [
  "sensory",
  "prey",
  "threat",
  "integrator_memory",
  "inhibitory",
  "motor",
] as const;

export type DomainName = (typeof DOMAIN_NAMES)[number];

/** 读数中展示的语义分组（§7 的五项）。 */
export const READOUT_DOMAINS: readonly DomainName[] = [
  "sensory",
  "prey",
  "threat",
  "integrator_memory",
];

export interface ActivationReadouts {
  /** 参与读数的神经元数（`h` 与 `cell_type` 的较小长度）。 */
  n: number;
  /** 各语义域的均值；该鱼无此域 → `null`。 */
  perDomain: Record<DomainName, number | null>;
  /** 左右 motor 池均值；无 motor 神经元 → `null`。 */
  motorLeft: number | null;
  motorRight: number | null;
  /** ω 驱动 `L − R`（`DanioNet §5`：`ω = tanh(L − R)`）；无 motor → `null`。 */
  omegaDriver: number | null;
}

function meanOf(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/**
 * `DanioNet §5` 的 `motor_sides` 复算：motor 下标按 `positions[i][0]` **稳定升序**排序后，
 * 前 `n//2` 为 left、其余为 right（与后端同口径；`n=0` 时两边皆空）。
 */
function motorSides(
  motorIndices: number[],
  positions: [number, number][],
): { left: number[]; right: number[] } {
  const ordered = [...motorIndices].sort((a, b) => {
    const xa = positions[a]?.[0] ?? 0;
    const xb = positions[b]?.[0] ?? 0;
    return xa - xb;
  });
  const leftCount = Math.floor(ordered.length / 2);
  return { left: ordered.slice(0, leftCount), right: ordered.slice(leftCount) };
}

/**
 * 计算五项语义读数。
 *
 * `h` 与 `cellType` 长度不一致时以较小者为准（诚实退化，不补值）；`positions` 缺项按 0 处理。
 */
export function activationReadouts(
  h: number[],
  cellType: number[] | null,
  positions: [number, number][] | null,
): ActivationReadouts | null {
  if (!cellType || cellType.length === 0) return null;
  const n = Math.min(h.length, cellType.length);
  if (n === 0) return null;

  const buckets = new Map<number, number[]>();
  for (let i = 0; i < n; i++) {
    const fate = cellType[i] ?? -1;
    const list = buckets.get(fate);
    if (list) list.push(h[i] ?? 0);
    else buckets.set(fate, [h[i] ?? 0]);
  }

  const perDomain = {} as Record<DomainName, number | null>;
  DOMAIN_NAMES.forEach((name, index) => {
    perDomain[name] = meanOf(buckets.get(index) ?? []);
  });

  const motorIndex = DOMAIN_NAMES.indexOf("motor");
  const motorIndices: number[] = [];
  for (let i = 0; i < n; i++) if ((cellType[i] ?? -1) === motorIndex) motorIndices.push(i);
  const { left, right } = motorSides(motorIndices, positions ?? []);
  const motorLeft = meanOf(left.map((i) => h[i] ?? 0));
  const motorRight = meanOf(right.map((i) => h[i] ?? 0));
  const omegaDriver =
    motorLeft !== null && motorRight !== null ? motorLeft - motorRight : null;

  return { n, perDomain, motorLeft, motorRight, omegaDriver };
}
