# 视觉素材占位

最终视觉参考待提供后统一冻结。

需要：
- EvoGenesis logo
- zebrafish swim sprites 4–6 帧
- prey / predator
- obstacles / plants / rocks
- water background
- DNA texture
- cell-type icons
- neural glow
- danger/hunger/mutation UI effect
- PPT cover visual

Arena 素材优先透明背景。实验图、统计图、network graph 不使用生图。

## 决策记录

- **2026-09-26（第二次，辰钊）**：**提示词一律按 `gpt-image-prompt` skill 重写**
  （本机 `~/.claude/skills/gpt-image-prompt/SKILL.md`）。该 skill 的硬规则已成为本目录两条文件的书写依据：
  **提示词用英文**、**固定标签化结构**、**比例只用网页版认的三种**、**颜色写 hex 不写色名**、
  首行 **AS-IS** 阻止 ChatGPT 加戏、**一条提示词 = 一次新对话**。
  逐条改动清单见 `ui_reference_prompts.md` §「本次按 skill 改了什么」。
  这一轮同时改掉了三个会白做的错：**`16:9` 网页版不认**、**色名不如 hex 可靠**、
  **一图塞太多主体/太多文字**。
- **2026-09-26（辰钊）**：**素材尽量全部由 ChatGPT 生成** —— 含 UI 参考图、sprite、logo、
  cell-type icons、neural glow、UI 特效、water background、molecular texture、PPT 封面视觉。
  理由：美工效果显著优于程序化绘制。

  两条边界**不因此放宽**：

  1. **数据驱动图不得生成**（本文件与 `frontend/交互与可视化.md` §12 已写死）：
     实验曲线、network graph、指标图、sensitivity map、统计结果**必须**由真实数据渲染。
     这类东西 ChatGPT 能帮的是**配色 / 主题配置 / 图例样式**（产出代码），不是产出位图。
  2. **生成的 UI 参考图只作视觉方向参考**，不得当作"界面截图"放进答辩稿或论文
     （`ui_reference_prompts.md` 已写明：它看起来像真实界面，会被读作伪数据）。

  配套：生成前须先冻结主题色板（≤32 色）并重写 `frontend/src/index.css`，
  否则素材与既有 token 对不上（详见 `ui_reference_prompts.md` 第 3 条工程约束）。

## 文件索引

| 文件 | 内容 |
|---|---|
| 本文件 | 素材清单（10 项）+ 决策记录 + 两条边界 |
| `ui_reference_prompts.md` | §快速开始 + §选型对照表 + **3 张 UI 参考图**完整提示词 + **§步骤 2 取色板提示词（交给 ChatGPT）** + §步骤 3 追问表（英文/标签化结构/hex/AS-IS）+ **候选色板唯一定义处**（24 色起步候选）+ 自检清单 + 两条操作纪律 + 3 条工程约束 + 选定后落地四步 + DNA 观感口径 |
| `asset_prompts.md` | **一图一素材的逐张提示词（15 条 / 约 20 张图）**：§0 三条铁律、§1 占位、§2 通用规格（含**四条现实约束**）、A1–A8 Arena 内素材、B1a/B1b/B2–B4 面板视觉、C1–C2 品牌与演示、§6 后处理与尺寸表、§7 自检、**§8 症状→修正表**、§9 清单自查 |
| `image_prompt_template.md` | 三类早期模板（Fish sprite / Predator / DNA）—— 已被 `asset_prompts.md` 覆盖，保留作沿革 |

**素材来源是 `asset_prompts.md` 的 A/B/C**。`ui_reference_prompts.md` 的提示词 2（sprite sheet）
已被 skill 判为「一图塞 7 类素材、违反多主体限制」，只保留作**风格对照图**，不是切图来源。

**使用顺序**：

1. 跑 `ui_reference_prompts.md` 的 3 条提示词（**每条新开一次对话**）→ 选定 1 张；
2. **把选定图交给 ChatGPT 取色板**（它是视觉模型，看图判断归它）：用 `ui_reference_prompts.md`
   §步骤 2 的提示词，拿回 ≤32 色的「色名 + hex」→ 回写该文件的 §候选色板 → 填进
   `asset_prompts.md` 的 `{色板}` 占位（并确认**不含** `{键控色}` 洋红）；
3. **先只生成 A1 一张**，验证「洋红底 → 抠图 → 最近邻缩小 → 贴到 `#0B1220` 上」这条链路；
4. A1 合格后它就是**风格锚**：之后每条提示词**新开对话 + 附上 A1 + 加那句
   `Image 1 is a style reference only: copy its exact pixel size, outline weight, palette and shading technique exactly. Do NOT copy its subject.`**
   ，再按 A→B→C 逐张生成。

色板未冻结前批量生成 = 全部作废。**一条提示词 = 一次新对话**，否则前面生成过的元素会渗进新图。
