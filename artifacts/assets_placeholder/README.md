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
