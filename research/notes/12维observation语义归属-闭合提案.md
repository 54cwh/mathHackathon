# 12 维 observation 语义归属 — 闭合提案

> **状态：草案待确认**
> 起草：李辰钊（Arena / 系统）
> 待 **池伟豪** 确认（`connectome/DanioNet设计规范.md` 为其 lane，本提案只提改动，不代改）
> 对应：`src/evogenesis/core/核心机制与数据流.md` §10 开放项 **#13**（「12 维 observation 语义 owner（DanioNet §2 ↔ Arena §4 互指「待闭合」）」）
> 已落地的同侧改动：`src/evogenesis/arena/Danio_Arena设计规范.md` **§15「12 维 observation 的语义归属」**（纯追加，见本文 §4）

---

## 0. 一句话结论

按 `AGENTS.md` 的裁决条款，**12 维 observation 的语义 owner 是 `arena/`（产出方）**，`connectome/DanioNet设计规范.md` 是**消费方、只引用**。互指死结的解在 Arena 侧已由 `Danio_Arena设计规范.md` §15 落地；本文给出消费侧与总管侧可**直接照抄**的精确替换句。

裁决依据（原文引用，不新立规则）：

| 依据 | 原文 |
|---|---|
| `AGENTS.md:142` | `arena/Danio_Arena设计规范.md`（+ `Danio_Arena实现说明.md`）——「**产出** observation（12 维）、事件日志、每鱼记录」 |
| `AGENTS.md:149` | 「每个箭头的边界对象由**产出方**文档定义，消费方只引用（见上 producer owns）」 |
| `AGENTS.md:126` | 「模块内算法与常量语义 → 该模块文档」 |
| `AGENTS.md:128` | 「**禁止循环引用**：边界对象必须指定唯一 owner；owner 未定时登记进 `core/核心机制与数据流.md` §10，**不得在两处各写一版**」 |
| `AGENTS.md:127` | 「`core/核心机制与数据流.md` 是数据流总管，拥有管线图与边界清单，**不定义模块内算法**」 |

**顺序冻结的硬性来源**：`docs/验收清单.md:15`「12 维输入顺序固定」。
**顺序的机器可读权威**：`src/evogenesis/arena/sensing.py:25-38` 的 `DIM_NAMES`（与 `observe()` 返回顺序 `sensing.py:147-163` 逐项对齐；docstring `sensing.py:4-11` 声明 `FROZEN`）。

---

## 1. 精确替换句 A — `connectome/DanioNet设计规范.md:29`（`（待闭合）`）

**替换前（现状，整行）**

```
依据：prey/threat 通道对应斑马鱼视觉捕食与威胁回避 `[bib#8]`；hunger/energy 对应内部状态调制决策 `[bib#9][bib#10]`；looming 为逃避触发量。维度顺序冻结，Arena↔DanioNet 的编码规则见 `arena/Danio_Arena设计规范.md`（待闭合）。
```

**替换后（整行）**

```
依据：prey/threat 通道对应斑马鱼视觉捕食与威胁回避 `[bib#8]`；hunger/energy 对应内部状态调制决策 `[bib#9][bib#10]`；looming 为逃避触发量。维度顺序冻结，语义 owner 为 `arena/Danio_Arena设计规范.md`（按其 §15「12 维 observation 的语义归属」，依 AGENTS.md「producer owns」）；本节 12 项为该文 §15.2 的**引用**，顺序以 `arena/sensing.py:25-38` 的 `DIM_NAMES` 为准，此处不另立定义。
```

**最小改法（若希望整行不动、只改从句）**：把 `（待闭合）` 替换为
`（语义 owner 见该文 §15；本清单为引用，顺序以 arena/sensing.py DIM_NAMES 为准）`。

理由：`AGENTS.md:142 / 149` 指定 Arena 为产出方，`AGENTS.md:128` 要求「不得在两处各写一版」。改后 §2 由「并列定义」降为「引用」，互指死结消失；两处顺序经核对本就一致（见本文 §3），改动不改变任何数值或顺序。

---

## 2. 精确替换句 B — `connectome/DanioNet设计规范.md:130`（阅读问题 #1）

**替换前（现状，整行）**

```
1. **12 维输入与 Arena 视野的对应未定义**：§2 列出 12 项，但各项如何由 arena/Danio_Arena设计规范.md 的 left/right channel、radius、FOV 计算未写（arena/Danio_Arena设计规范.md 阅读问题 #1 的另一侧）。
```

**替换后（整行）**

```
1. ~~12 维输入与 Arena 视野的对应未定义~~ **已由产出方定义**：§2 列出 12 项，各项由 `arena/Danio_Arena设计规范.md` 的 left/right channel、radius、FOV 算出，编码规则见该文 §15「12 维 observation 的语义归属」；归一化公式见 `arena/Danio_Arena实现说明.md` §3.1「规范 §4 视野」行、§3.2 S20 与 `research/notes/arena-api-决策认领表.md` A1，**公式的认领状态为 `草案待确认`**（归属已闭合，数值未冻结）。本节只引用。
```

**若不愿用删除线**：直接整行替换为

```
1. **12 维输入与 Arena 视野的对应（已闭合）**：§2 列出 12 项，各项由 `arena/Danio_Arena设计规范.md` 的 left/right channel、radius、FOV 算出；语义 owner 与编码规则见该文 §15，本节只引用。
```

理由：原文「未定义」与「另一侧」的措辞描述的是历史状态；按 `AGENTS.md` `# 根因修复原则` 第 3 条（正向、面向当前状态），改为陈述当前归属。归属（谁拥有）与数值（公式是否冻结）是两件事，本文分开记录，不把未认领的公式说成已冻结。

---

## 3. 精确替换句 C — `core/核心机制与数据流.md:109`（§4.2 `observation` 行）

**替换前（现状，整行）**

```
| `observation` | float[**12**]（`sensory_dim = 12`） | 感知向量，**维度顺序冻结**（维度定义见 `connectome/DanioNet设计规范.md` §2；验收清单硬性要求） |
```

**替换后（整行）**

```
| `observation` | float[**12**]（`sensory_dim = 12`） | 感知向量，**维度顺序冻结**（维度定义见 `arena/Danio_Arena设计规范.md` §15（语义 owner；`connectome/DanioNet设计规范.md` §2 为其引用）；顺序权威 `arena/sensing.py` 的 `DIM_NAMES`；验收清单硬性要求） |
```

理由：`core/核心机制与数据流.md` 是**数据流总管**，按 `AGENTS.md:127` 拥有管线图与边界清单、**不定义模块内算法**；`AGENTS.md:138` 亦记其「不定义模块内算法」。它现在把这个边界对象的语义指向**消费方** `DanioNet §2`，方向与 `AGENTS.md:149` 相反。改指产出方即可，无需在 core 内复制 12 项清单（`AGENTS.md:128`）。

---

## 4. 已落地的同侧改动（Arena lane，仅供对照）

`src/evogenesis/arena/Danio_Arena设计规范.md` 末尾、`## 阅读问题（待确认）` 之前，已追加 **§15「12 维 observation 的语义归属」**（含 15.1 归属声明 / 15.2 顺序权威与 12 维索引 / 15.3 公式状态未认领 / 15.4 两项内容缺口 N1、N2 / 15.5 与阅读问题 #1 的关系），并在该文「阅读问题」A 节 #1 下追加一行指向 §15。**纯追加：`git diff --numstat` 删除列为 0。**

---

## 5. 七处并列陈述 → 「1 个 owner + 6 处引用」

清单出处：`src/evogenesis/arena/Danio_Arena实现说明.md:343`（§10 变更纪律表「12 维感知顺序」行）①–⑦。收敛要求出处：`AGENTS.md:128`。

| 序号 | 位置（`实现说明:343` 编号） | 现状角色 | 目标角色 | 改 / 不改 | 由谁改 | 依据 |
|---|---|---|---|---|---|---|
| ① | `src/evogenesis/arena/sensing.py`（docstring 与 `DIM_NAMES`） | 定义 + 实现 | **owner**（顺序与索引的机器可读权威） | 不改内容 | — | `AGENTS.md:142/149` |
| ② | `schemas/examples/README.md:34` 的 12 维语义表 | 并列陈述（表头指 `DanioNet §2`） | 降为引用 | **改 1 行（表头）** | schemas 侧（建议李辰钊起草、池伟豪确认） | `AGENTS.md:128` |
| ③ | `schemas/examples/trajectory_example.jsonl`（观测向量列序） | 数据载体 | 降为引用（列序须与 owner 一致） | 不改数据 | — | 同上 |
| ④ | `core/核心机制与数据流.md` §4.2 `observation` 行 | 指向消费方 `DanioNet §2` | 降为引用（改指 Arena §15） | **改 1 行**（见本文 §3） | core（数据流总管） | `AGENTS.md:127/138/149` |
| ⑤ | `connectome/DanioNet设计规范.md` §2（+ 阅读问题 #1） | 并列陈述（消费方） | 降为引用 | **改 2 行**（见本文 §1、§2） | 池伟豪（本文只提案） | `AGENTS.md:149` |
| ⑥ | `docs/参数总表.json` `sensory_dim` 条目 | Tier 3：拥有基数 `12` 与依据状态 | 保留；`source` 指向**待确认** | 待定 | 参数总表侧 | `AGENTS.md:121`（Tier 3） |
| ⑦ | `docs/验收清单.md:15`「12 维输入顺序固定」 | 验收判据 | 保留（不陈述具体顺序） | 不改 | — | `AGENTS.md:126`（验收判据属地） |

**② 的替换句（`schemas/examples/README.md:34`）**

替换前：

```
## trajectory 观测向量的 12 维语义（connectome/DanioNet设计规范.md §2）
```

替换后：

```
## trajectory 观测向量的 12 维语义（语义 owner：arena/Danio_Arena设计规范.md §15；顺序权威：arena/sensing.py 的 DIM_NAMES）
```

**⑥ 的待确认项（不代改，交参数总表侧决定）**：`docs/参数总表.json:298` 现记 `"source": "src/evogenesis/connectome/DanioNet设计规范.md:13-25"`。该字段语义是「依据」，按 Tier 3 属地由参数总表自行决定；两种处理供选：**(a) 保留**（依据可指消费方清单，因该清单顺序与 owner 一致）、**(b) 改指** `src/evogenesis/arena/sensing.py:25-38`。本文不预判。

---

## 6. 两处内容缺口（一并登记，避免闭合归属时被误当已解决）

| # | 缺口 | 证据 | 状态 |
|---|---|---|---|
| **N1** | **第 9 维（idx 8）`looming_rate` 在现状调用序下恒为 0**（除 `reset()` 后首帧）：`observe()` 总在步界调用，而 `_prev_predator_rel` 在上一步末尾用**同一函数**刷新，故两者由构造必然相等 ⇒ 该维**目前不携带信息** | `Danio_Arena实现说明.md:143`（S20 实测：seed 250927 首帧 12 条鱼中 2 条为 1.0，其后 40 步全 0）、`:281`（F1）、`:302`（M13） | **草案待确认**；修法与认领表 A1 一并认领（M13 记：修法会改变观测分布） |
| **N2** | 同一顺序在**七处并列陈述**，按 `AGENTS.md:128` 应收敛为 1 owner + 6 引用 | `实现说明:343`；`AGENTS.md:128` | 本文 §5 给出收敛落点 |

**归一化公式的认领状态**（与 N1 相关但独立）：**未认领**，出处 `research/notes/arena-api-决策认领表.md:15-19`（**A1**，「12 维感官编码的归一化公式」）；同表 A1 现状栏（`:16`）与 `Danio_Arena实现说明.md:266`（§7 A1 行）记其「已实现、已固化」。**未认领的数值不得进论文与正式实验**（`Danio_Arena实现说明.md:8`）。

---

## 7. 自检

| 项 | 结果 |
|---|---|
| 12 维顺序四源逐项核对 | ✅ 一致 —— `arena/sensing.py:25-38`（`DIM_NAMES`）、`sensing.py:4-11`（docstring）、`connectome/DanioNet设计规范.md:16-27`、`schemas/examples/README.md:38-43`（表头 `:34`）、`schemas/trajectory.schema.json:61` |
| 本文档「待确认 / 未定义」计数 | **4 处**：公式认领状态（A1）未认领；N1（第 9 维恒 0）待认领；⑥ 参数总表 `source` 指向待确认；§2 提炼替换句待池伟豪确认 |
| 提议的精确替换句 | **4 个目标、6 句**：主改 4 句 —— §1（`DanioNet:29`）、§2（`DanioNet:130`）、§3（`core:109`）、§5②（`README:34`）；另附备选措辞 2 句（§1 的从句级最小改法、§2 的去删除线版） |
| 已落地编辑 | 仅 1 文件：`arena/Danio_Arena设计规范.md`（纯追加，`git diff --numstat` 删除列 = 0） |
| 未触碰 | `connectome/DanioNet设计规范.md`、`core/核心机制与数据流.md`、`AGENTS.md`、`docs/参数总表.json`、`research/reference/`、任何 `.py`、`configs/`、`frontend/` |

---

## 8. 不敢写、留给业主的地方

1. **DanioNet §2 的 12 项是否保留为显式清单** —— `AGENTS.md:128` 允许「1 owner + N 引用」，但**是否**要在消费方保留完整的 12 项枚举（便于阅读）属池伟豪的写作选择。本文只把措辞改为「引用」，不删清单。
2. **`docs/参数总表.json` `sensory_dim.source` 的指向**（本文 §5⑥）—— Tier 3 自决，本文给出 (a)/(b) 两个选项而不预判。
3. **N1 的第 9 维修法** —— `实现说明:302`（M13）给出方向（在 `step()` 内移动前后各取一次，或把 `prev` 改在步首读取）但明示「会改变观测分布，需与 A1 一并认领」。**具体修法属设计决定，本文不选。**
4. **归一化公式本身的数值** —— 认领表 A1 尚未回答，本文只登记状态，不复制、不改写公式（`AGENTS.md:128`）。
5. **`实现说明:343` ⑥ 与 `docs/参数总表.json` 收录范围的措辞落差** —— `实现说明:93` 记 `sensory_dim` 属「DanioNet 侧契约，不是 Arena 世界参数」，与本文「Arena 拥有 12 维语义」并存不矛盾（前者讲**参数表的收录范围**，后者讲**边界对象的语义归属**），但是否要在参数总表侧加一句说明由参数总表侧决定。
