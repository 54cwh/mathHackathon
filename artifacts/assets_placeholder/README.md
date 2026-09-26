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
| `ui_reference_prompts.md` | **3 张 UI 参考图**完整提示词（像素风）+ 自检清单 + 3 条工程约束 + 选定后落地四步 |
| `image_prompt_template.md` | 三类早期模板（Fish sprite / Predator / DNA）—— 已被 `asset_prompts.md` 覆盖，保留作沿革 |
| `asset_prompts.md` | **一图一素材的逐张提示词（14 条）**：A1–A8 Arena 内素材（成鱼摆尾 4 帧、幼鱼、猎物、捕食者、水草、岩石/沉木、地表瓦片、海洋背景）、B1–B4 面板视觉（DNA 纹理+碱基条、细胞图标、神经辉光、UI 特效）、C1–C2（logo、PPT 封面）；另含 §0 占位、§1 通用规格、**§2 三条现实约束**（透明背景/伪像素/鱼大小）、§6 后处理与尺寸表、§7 自检 |

**使用顺序**：先跑 `ui_reference_prompts.md` 的 3 条 → 选定 1 张 → 取色板（不超过 32 色）→ 把它填进 `asset_prompts.md` 的 `{色板}` 占位（并确认 `{色板}` **不含** `{键控色}` 洋红）→ **先只生成 1 张验证抠图链路** → 再按 A→B→C 逐张生成。
色板未冻结前批量生成 = 全部作废。
