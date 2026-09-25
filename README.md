# EvoGenesis

**Evolutionary-Developmental Neural Networks from Regulatory Genomes**

中文暂定：**EvoGenesis：基于遗传调控与演化发育的神经网络生成系统**

> Edit DNA. Grow Brains. Evolve Behavior.

EvoGenesis 面向“神经网络设计 + 数学建模”赛道。项目不直接手工指定最终神经网络，而是定义一套可编辑、可遗传的人工二倍体 DNA，经由统一的调控与发育模型生成 DanioNet；DanioNet 再进入 Danio Arena 完成捕食、逃逸、能量管理和繁殖选择。

核心链路：

```text
Diploid DNA
   ↓
Regulatory Motif Matching
   ↓
Discrete GRN Dynamics
   ↓
Cell Proliferation & Differentiation
   ↓
RGCD: Genome-to-Connectome Decoding
   ↓
DanioNet Topology + Neuronal Dynamics
   ↓
Lifetime Learning
   ↓
Danio Arena Behavior
   ↓
Fitness
   ↓
Mendelian Inheritance + Recombination + Mutation
   ↓
Next Generation
```


## 命名体系

- **EvoGenesis**：总项目名与总体框架。
- **RGCD**：Regulatory Genome-to-Connectome Decoder，核心算法。
- **DanioNet**：由 RGCD 发育生成的斑马鱼启发神经网络。
- **DNA2Brain Lab**：DNA 编辑、调控与发育交互实验台。
- **Danio Arena**：捕食—逃逸—繁殖—演化生态环境。

“Danio”仅保留在神经网络实例与生态环境层，用于强调斑马鱼生物学参考；总项目统一使用 EvoGenesis。

## 核心方法
**RGCD — Regulatory Genome-to-Connectome Decoder**

## 当前冻结范围
- 二倍体人工 genome：2 对同源染色体，每条单倍染色体 128 bp。
- 8 个 regulatory motifs，8 维 GRN。
- GRN 采用统一离散时间动力学，报告、代码、Demo 使用同一个更新方程。
- 24 个 precursor cells，6 个 developmental domains，每个 precursor 最多分裂一次，最多 48 个神经元。
- 六类基础 neural fate：sensory / prey / threat / integrator-memory / inhibitory / motor。
- DNA/GRN 同时影响网络 topology 与 neuron-specific time constant。
- DanioNet 输出连续动作：turning angular velocity + propulsion。
- Arena 使用 12 维结构化感知输入，不使用原始像素作为本次 MVP 输入。
- 生命周期学习：ExpertPolicy → Behavior Cloning；RL 仅作为可选扩展。
- 后天训练权重不遗传；后代只继承 DNA，并重新发育。
- 种群演化采用有限种群、二倍体、随机配子、重组、SNP mutation 和 fitness-based parent selection。
- Mendel Mode 用 AaBb × AaBb 展示 9:3:3:1。
- Virtual CRISPR 为 P1：核心系统完成后有时间则加入。
- 表观遗传、真实斑马鱼 genome、原始像素视觉、复杂结构变异、SNN、3D embryogenesis 等进入 Future Work。

## 交付目标
1. 论文/技术报告
2. 建模方法与 AI 工作流
3. 可离线运行现场 Demo
4. 创新性与价值论证
5. 完整路演材料
6. 可选 60–90 秒本地 Demo 视频

## 两人分工
### 池伟豪
模型与后端主负责人：DNA engine、GRN、Development / RGCD、DanioNet、Behavior Cloning、Evolution Engine、Baseline / Ablation、实验跑数。

### 李辰钊
系统与建模主负责人：数学建模规范、Danio Arena、前端与交互、DNA/Brain/Evolution 可视化、实验设计与结果解释、系统集成、技术报告、PPT、现场路演。

## 待外部输入
- 最终视觉风格参考图
- 开发机器硬件配置

系统默认设计为 CPU 可运行、GPU 可加速；视觉层使用可替换主题资源。
