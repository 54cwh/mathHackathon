---
name: nn-design-playbook
description: 数学建模黑客松"设计一个神经网络"赛道的作战手册。涵盖调研→形式化→实验→写作全流程、三条候选方向（预测编码/事件驱动、有限元分区、存算一体）的数学内核与实验设计、可用的开源与 MCP 工具、以及评分导向的自检清单。当需要"定方向""设计网络结构""规划建模流程""确定评价指标""准备答辩"时使用。
---

# 神经网络设计赛道作战手册

## 赛道判据
评委看四点：**原创性、数学严谨性、可跑通、故事闭环**。产出应是"一个受脑/物理启发的网络结构 + 数学刻画 + 仿真验证"，而非刷 SOTA。

## 三条候选方向（可组合）
### C. 预测编码 + 事件驱动（最贴题）
- 内核：只传预测误差。自由能 $F=\lVert x-\hat x\rVert^2+\beta\Omega(z)$；阈值 $\tau$ 控制"精度-计算量"。
- 实验：视频下一帧预测，对比 dense（每帧全算）与 event-driven（只算残差）的 FLOPs-延迟-精度。
- 锚点：Rao & Ballard (1999)；代码 `coxlab/prednet`、`BerenMillidge/PredictiveCodingBackprop`。

### B. 有限元式分区神经元网络（最原创）
- 内核：网络=图，前向=扩散离散化 $u_{t+1}=u_t-\alpha L u_t+\sigma(Wu_t)$，$L=D-A$。
- 分区=谱聚类 min-Ncut；用谱隙 $\lambda_2$ 与边界带宽 $b$ 给出精度-通信量权衡。
- 工具：scikit-learn 谱聚类、METIS；框架可选 `brainpy/BrainPy`。

### A. 存算一体 Pareto 优化（数学最稳）
- 内核：crossbar 上 $I=GV$，输出 $y=f(Q(GV+\epsilon_{\text{drift}}+\epsilon_{\text{IR}}+\epsilon_{\text{ADC}}))$；能耗 $E(p,k)$。
- 优化：$\min E$ s.t. $\mathrm{Acc}\ge A^*$，画 Pareto 前沿。
- 工具：`coreylammie/MemTorch`、`thu-nics/MNSIM-2.0`、`knowm/memristor-models-4-all`。

## 工作流
1. `/scout` 调研（GitHub 实现 + 论文锚点）→ 2. `modeler` 形式化并给验证方案 →
3. `experimenter` 最小实验 + 指标 → 4. `writer` 成稿 → 5. `critic` 压力测试 → 迭代。

## 必备产出（答辩清单）
- 一张网络结构示意图（Netron 导出）
- 一条核心数学式 + 其推导/性质
- 一张对比图（Pareto / FLOPs-延迟-精度 三角）
- 一个最小复跑命令 + 随机种子
- 与已有工作的差异说明

## 工具速查
- 调研：`gh search repos`、`openalex_*`、`arxiv` MCP、`tavily`、`mcp-for-zotero`
- 框架：PyTorch、snnTorch/SpikingJelly、PredNet、MemTorch
- 写作：`academic-writing-distillation` skill、`latex2word` skill、`ai-tone-boundaries.md`
- 解析：`mineru`（PDF→Markdown）
