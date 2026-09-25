# DNA2Brain 项目交接稿 v0.1

> 当前版本为初步方案，用于团队内部对齐方向、拆分任务和快速启动开发。  
> 后续可根据时间、实现难度、比赛规则和测试结果继续修改。

---

## 1. 项目一句话

**DNA2Brain：让人工斑马鱼的神经网络不是被直接“搭出来”，而是由一段人工 DNA 经过基因调控与发育规则“长出来”，再进入二维生态环境中完成捕食、逃逸、生存、繁殖和演化。**

核心链路：

\[
\text{DNA}
\rightarrow
\text{Gene Regulation}
\rightarrow
\text{Development}
\rightarrow
\text{Neural Circuit}
\rightarrow
\text{Behavior}
\rightarrow
\text{Fitness}
\rightarrow
\text{Evolution}
\]

---

## 2. 项目定位

参赛方向：**神经网络设计 / 数学建模 / 生物启发计算**

项目重点不是做一个普通遗传算法，也不是直接复刻真实斑马鱼大脑，而是尝试设计一种新的神经网络生成范式：

\[
\boxed{
\text{Genome}
\xrightarrow{\text{Development}}
\text{Neural Architecture}
}
\]

传统神经网络通常直接指定层数、连接方式和模块结构；DNA2Brain 希望把“神经网络结构”看作一种表型，由更紧凑的遗传编码和发育规则生成。

核心思想：

- **DNA 不直接等于神经网络权重**
- **DNA 决定的是神经网络如何发育**
- **不同 DNA 可以生成不同网络结构**
- **网络结构再决定不同的行为倾向**
- **环境进一步选择不同的神经网络表型**

---

## 3. 生物模型

主要参考生物：**斑马鱼（Danio rerio）**

选择原因：

1. 斑马鱼具有清晰的视觉—决策—运动行为链条。
2. 捕食、逃逸、趋近、回避等行为适合转换为计算任务。
3. 斑马鱼天然适合“大鱼吃小鱼”式二维生态演示。
4. 可以自然结合遗传、发育、神经回路和行为。
5. 相比直接模仿人脑，更适合在黑客松时间内做出可运行模型。

---

## 4. 项目组成

项目暂分为三个主要模块。

### 4.1 DNA Lab

负责遗传编码与人工交互。

主要功能：

- 查看人工 DNA 序列
- 人工编辑 A / C / G / T
- 单碱基突变
- 选择关键调控位点
- 选择两条鱼作为亲本
- 进行繁殖
- 查看后代基因型
- 控制繁殖轮次
- 后续可增加虚拟 CRISPR 模式

目标：

> 让用户能够直接参与“改 DNA”和“选亲本”。

---

### 4.2 Brain Forge

负责：

\[
\text{DNA}
\rightarrow
\text{Gene Expression}
\rightarrow
\text{Neural Network}
\]

主要展示：

1. DNA motif 被识别
2. 调控信号发生变化
3. gene expression 改变
4. 不同类型神经元生成
5. 神经连接形成
6. 最终生成 DanioNet

目标：

> 让“DNA 长成大脑”成为项目最核心的视觉过程。

---

### 4.3 Danio Arena

二维生态游戏环境。

整体体验参考“大鱼吃小鱼”类游戏，但使用自主设计的视觉和规则。

环境中包含：

- 小型猎物
- 大型捕食者
- 障碍物
- 其他人工斑马鱼
- 食物与能量系统
- 饥饿状态
- 生存时间
- 捕食 / 逃逸行为
- 后续可加入成长机制

目标：

> 让不同 DNA 生成的神经网络在同一个环境中直接产生可观察的行为差异。

---

# 5. DNA 如何影响神经网络

## 5.1 人工 DNA

第一版不使用真实完整斑马鱼基因组，而是设计一个简化人工 genome：

\[
S \in \{A,C,G,T\}^{L}
\]

建议第一版：

\[
L \approx 100\sim300
\]

后续需要时再扩展。

示例：

```text
ACGTTACCGTATAAGGCTACGGATCC...
```

---

## 5.2 Regulatory Motif

DNA 中定义若干人工 regulatory motifs。

例如：

```text
Motif M1: ACGTAC
Motif M2: GGATCC
Motif M3: TATAAG
```

程序扫描 DNA，并计算 motif 匹配程度：

\[
q_k(S)=Match(M_k,S)
\]

随后进入 gene-expression 模型。

---

## 5.3 Gene Expression

第一版计划设置 4 类核心“发育基因”。

### P：Prey

控制：

- 猎物检测
- 猎物追踪
- 视觉趋近

### T：Threat

控制：

- 威胁检测
- 逃逸反应

### M：Memory

控制：

- 循环连接
- 神经元时间常数
- 对过去状态的保留

### I：Inhibition

控制：

- 抑制性神经元比例
- 左右运动回路竞争
- 稀疏激活

简化表达模型：

\[
e_i=
\sigma
\left(
b_i+\sum_k w_{ik}q_k
\right)
\]

得到：

\[
e_P,e_T,e_M,e_I
\]

---

# 6. Developmental Decoder

核心模块：

\[
A=D(S)
\]

其中：

- \(S\)：DNA sequence
- \(D\)：developmental decoder
- \(A\)：最终神经网络 adjacency / connectivity

第一版不模拟完整真实胚胎发育。

只需要做到：

> 不同 DNA → 不同表达 → 不同神经元组成与连接 → 不同 DanioNet。

可以根据表达量控制：

- 各类神经元数量
- recurrent connection probability
- inhibitory connection probability
- sensory-to-motor connection
- memory circuit strength
- left/right motor competition

例如：

\[
N_{memory}=f(e_M)
\]

\[
P_{inhibitory}=f(e_I)
\]

\[
\tau_{memory}=\tau_0+\alpha e_M
\]

\[
P(A_{ij}=1)
=
\sigma
(
\beta_0+
\beta_1e_P+
\beta_2e_M-
\beta_3d_{ij}
)
\]

---

# 7. DanioNet

DanioNet 暂定为：

**由 DNA 发育产生的异质、模块化、循环神经网络。**

初版结构：

```text
        Left Visual Input       Right Visual Input
                \                 /
                 \               /
                  Visual Encoder
                        |
          -----------------------------
          |                           |
     Prey Circuit               Threat Circuit
          |                           |
          -----------+-----------------
                     |
               State / Memory
                     |
                 Hunger Gate
                     |
             Action Selection
              /             \
           Left             Right
                Motor Circuit
```

核心神经元类型：

- Fast sensory neurons
- Prey-related neurons
- Threat-related neurons
- Memory / slow neurons
- Inhibitory neurons
- Motor neurons

简化动力学：

\[
h_i^{t+1}
=
(1-\lambda_i)h_i^t
+
\lambda_i
\sigma
\left(
\sum_j A_{ij}w_{ij}h_j^t
+
U_ix_t
\right)
\]

其中不同神经元具有不同：

\[
\lambda_i
\]

用于形成不同时间尺度。

---

# 8. 生理状态：Hunger

饥饿不作为基因，而作为实时生理状态。

定义：

\[
H_t=
1-\frac{E_t}{E_{max}}
\]

其中：

- \(E_t\)：当前能量
- \(H_t\)：饥饿程度

神经网络可以写成：

\[
h_{t+1}
=
\sigma
\left[
(A(S)\odot W)h_t
+
Ux_t
+
MH_t
\right]
\]

其中：

- \(S\)：DNA
- \(A(S)\)：DNA 发育产生的网络结构
- \(W\)：后天学习得到的连接强度
- \(x_t\)：环境输入
- \(H_t\)：当前生理状态

这样可以区分：

- Genetics：有什么回路
- Learning：连接如何调整
- Physiology：当前如何使用回路
- Environment：当前看到了什么

---

# 9. 9:3:3:1 的使用方式

项目中保留经典孟德尔双因子遗传作为一个重要展示入口。

设置两个关键调控位点：

\[
A/a
\]

与：

\[
B/b
\]

初步可分别对应：

- A：Memory / Prey developmental program
- B：Threat / Inhibitory developmental program

进行：

\[
AaBb\times AaBb
\]

在经典完全显性、独立分配的基线情况下：

\[
9:3:3:1
\]

对应四种人工 neural phenotype。

| 遗传表型 | 神经网络表型 |
|---|---|
| \(A\_B\_\) | Memory/Prey + Threat/Inhibition |
| \(A\_bb\) | 偏捕食 / 记忆 |
| \(aaB\_\) | 偏逃逸 / 抑制 |
| \(aabb\) | 基础反射网络 |

注意：

9:3:3:1 主要用于：

- 路演入口
- 遗传机制演示
- Architecture ablation
- 不同 neural phenotype 对比

不表示某一种 genotype 一定“最好”。

---

# 10. Epistasis

后续版本可加入：

\[
\theta
=
\theta_0
+
\alpha G_A
+
\beta G_B
+
\gamma G_AG_B
\]

其中：

\[
\gamma
\]

代表 gene interaction / epistasis。

目标：

> 两个基因共同存在时，产生的神经结构不只是两个模块简单相加，而可以出现新的 circuit motif。

例如：

Memory circuit 与 inhibitory circuit 共同存在时，额外形成 memory-modulated action competition。

这一部分可作为后续升级功能，不是第一版 MVP 的强制项。

---

# 11. Danio Arena 游戏规则

## 11.1 输入

人工鱼感知：

- 猎物方向
- 猎物距离
- 猎物大小
- 捕食者方向
- 捕食者距离
- looming / 接近速度
- 障碍物
- 当前能量
- 当前饥饿度

---

## 11.2 输出

网络输出：

- Turn Left
- Turn Right
- Forward
- Accelerate / Escape

第一版不需要复杂动作空间。

---

## 11.3 能量

鱼持续消耗能量：

\[
E_{t+1}
=
E_t
-
C_{metabolism}
-
C_{movement}
+
R_{food}
\]

当能量过低：

- 行动能力下降
- 最终死亡

吃到食物：

\[
E\uparrow
\]

---

## 11.4 Fitness

第一版：

\[
F
=
\alpha N_{food}
+
\beta T_{survival}
-
\gamma E_{cost}
\]

后续可以加入：

- 捕食成功率
- 逃逸成功率
- 能量效率
- offspring 数量

---

# 12. Environment

至少准备 3 套环境。

### Food Rich

- 食物多
- 捕食者少

### Predator Rich

- 捕食者多
- 生存压力高

### Resource Scarce

- 食物少
- 能量压力高

后续：

### Mixed / Complex Environment

同时存在：

- 食物
- 捕食者
- 干扰目标
- 障碍物

目的：

> 比较不同生态压力下，不同神经网络的适应表现。

---

# 13. Evolution

每一代：

1. 所有人工斑马鱼进入 Danio Arena
2. 根据行为获得 fitness
3. 用户可以人工挑选亲本，也可以自动按 fitness 选择
4. 父母发生遗传
5. 产生 offspring DNA
6. offspring 重新经历 development
7. 生成新的 DanioNet
8. 进入下一代

核心区别：

不是：

\[
Network_{parent}
\rightarrow
Network_{offspring}
\]

而是：

\[
DNA_{parent}
\rightarrow
DNA_{offspring}
\rightarrow
Development
\rightarrow
Network_{offspring}
\]

---

# 14. 必须实现的可交互功能

## P0

- DNA 查看
- 单碱基编辑
- 选择人工鱼
- 查看 Fish Card
- 选择 Parent A
- 选择 Parent B
- Breed
- 自定义繁殖轮次
- Release into Arena
- 环境切换
- Reset demo

---

## P1

- 9:3:3:1 Mendel Mode
- Random Mutation
- Evolve 5 / 10 / 20 generations
- Population statistics
- Network activity visualization

---

## P2

- Virtual CRISPR
- Epistasis switch
- Recombination animation
- 更复杂 developmental rules
- Epigenetic state

---

# 15. 主要可视化

## 15.1 DNA Animation

希望达到：

- DNA 双螺旋缓慢旋转
- nucleotide 可点击
- mutation 位点高亮
- motif 区域发光
- TF scanning animation

目标视觉：

**“生命代码编辑器”**

---

## 15.2 Brain Development Animation

核心视觉链：

```text
DNA
 ↓
Motif activation
 ↓
Gene expression
 ↓
Neuron types appear
 ↓
Connections grow
 ↓
DanioNet activates
```

这一部分是整个项目的主要视觉高潮之一。

---

## 15.3 Neural Activity

网络运行时：

- 节点按 activation 发光
- prey circuit 激活时突出
- threat circuit 激活时突出
- left/right motor pool 可实时对比

目标：

> 可以一边看鱼游，一边看“大脑正在想什么”。

---

## 15.4 Danio Arena

要求：

- 2D 即可
- 重点是流畅和直观
- 大鱼 / 小鱼 / prey / obstacle 明显区分
- 小鱼有游动动画
- 捕食和逃逸有明显视觉反馈
- 选中个体后高亮

---

## 15.5 Evolution Dashboard

显示：

- Generation
- \(p(A)\)
- \(p(B)\)
- 四种 neural phenotype 比例
- mean fitness
- mean survival time
- best individual

环境切换时在曲线上标记。

---

# 16. 现场演示流程

目前建议把现场演示设计成 5 个连续步骤。

### Step 1：9:3:3:1

展示：

\[
AaBb\times AaBb
\]

得到：

\[
9:3:3:1
\]

并说明：

> 这里对应的不是四种豌豆，而是四种不同的神经网络表型。

---

### Step 2：选中一条鱼

打开：

- DNA
- genotype
- neural phenotype
- fitness
- brain network

---

### Step 3：改一个碱基

人工：

```text
C → T
```

观察：

```text
DNA
↓
Expression
↓
Brain
```

重新生成。

---

### Step 4：放入 Arena

点击：

**Release**

观察：

- 捕食
- 逃逸
- 饥饿
- 行为变化

---

### Step 5：繁殖和演化

人工挑选两条鱼：

```text
Parent A
Parent B
```

点击：

```text
Breed
```

然后：

```text
Evolve 10 Generations
```

观察：

- allele frequency
- phenotype distribution
- fitness

发生变化。

---

# 17. 项目核心宣传语

暂定：

## DNA2Brain

**Edit DNA. Grow Brains. Evolve Behavior.**

中文：

> **编辑 DNA，长出大脑，演化行为。**

核心表达：

> **我们不直接编码神经网络，而是编码产生神经网络的 DNA。**

另一句可用于现场：

> **改一个碱基，长出一个不同的大脑。**

---

# 18. 技术实现建议

## Frontend

建议：

- React / Next.js

用于：

- 控制界面
- DNA Lab
- Fish Card
- Dashboard

---

## DNA / Brain 可视化

可选：

- SVG
- D3.js
- Cytoscape.js
- Three.js

时间紧张时：

优先 SVG / Canvas，不必强求完整 3D。

---

## 游戏环境

推荐：

- Phaser.js

也可以：

- HTML Canvas

重点：

> 先保证稳定、流畅，再追求复杂视觉。

---

## 模型

推荐：

- Python
- PyTorch
- FastAPI

第一版网络规模应保持较小，避免现场推理和训练不稳定。

---

## 数据通信

如果前后端分离：

- REST API
- WebSocket

实时传输：

- neural activation
- fish state
- generation stats

---

# 19. 开发优先级

## P0：必须完成

1. DNA → Gene Expression
2. Gene Expression → DanioNet
3. DanioNet 能控制鱼
4. Danio Arena 可以运行
5. DNA 可人工编辑
6. 可以选鱼
7. 可以繁殖
8. 可以推进 Generation
9. 固定 Demo Seed
10. 一键 Reset

---

## P1：强烈建议

1. 9:3:3:1
2. DNA 动画
3. network growth 动画
4. environment switching
5. evolution dashboard
6. neural activity visualization

---

## P2：有时间再做

1. Virtual CRISPR
2. Epistasis
3. Growing body size
4. Complex recombination
5. Epigenetics
6. 更复杂发育过程

---

# 20. 推荐开发顺序

不要先做视觉。

建议严格按：

```text
DNA
 ↓
Developmental Decoder
 ↓
DanioNet
 ↓
Fish Controller
 ↓
Danio Arena
 ↓
Breeding
 ↓
Evolution
 ↓
Interaction UI
 ↓
Visualization Polish
```

即：

### 第一阶段
先证明：

> 不同 DNA 可以生成不同 network。

### 第二阶段
证明：

> network 能控制鱼。

### 第三阶段
证明：

> 不同 network 行为不同。

### 第四阶段
加入：

> breeding + evolution。

### 第五阶段
最后集中做：

> DNA 动画 + Brain Forge + Arena 美化。

---

# 21. Demo 稳定性

黑客松现场优先保证稳定。

必须准备：

- 固定 random seed
- 预计算好的 demo population
- 可加载 network checkpoint
- 一键 reset
- 一键跳到 Generation 10 / 20 的备份状态
- 网络模型和 Arena 解耦

原则：

\[
\boxed{
Demo\ Reliability
>
Model\ Complexity
}
\]

---

# 22. 当前最核心的三个验证目标

最终至少证明：

## 1

\[
\text{不同 DNA}
\rightarrow
\text{不同 Neural Architecture}
\]

## 2

\[
\text{不同 Neural Architecture}
\rightarrow
\text{不同 Behavior}
\]

## 3

\[
\text{不同 Environment}
\rightarrow
\text{不同 Selection Outcome}
\]

只要这三个闭环跑通，MVP 即成立。

---

# 23. 当前项目结构名称

### 总体框架

**DNA2Brain**

### 神经网络

**DanioNet**

### 实验 / 游戏环境

**Danio Arena**

完整关系：

```text
DNA2Brain
    ↓
 DanioNet
    ↓
Danio Arena
```

---

# 24. 下一步最需要团队尽快确定的问题

目前最优先需要讨论并锁定：

1. 人工 DNA 长度
2. motif 数量
3. gene-expression 数量
4. DanioNet 第一版 neuron types
5. Developmental Decoder 的具体公式
6. Danio Arena 的动作空间
7. 第一版是否训练网络，还是采用固定/规则化部分参数
8. 具体开发周期和人员分工
9. 前后端技术栈最终选择
10. MVP 截止时间

其中最重要的是：

> **先把 DNA → DanioNet 的最小数学映射确定下来。**

这是整个项目最核心的技术部分，也是后续最需要重点打磨和解释的内容。

---

## 当前阶段结论

项目当前方向暂定为：

> **以斑马鱼为生物模型，设计一种由人工 DNA 经过调控与发育规则生成的异质模块化神经网络 DanioNet，并在 Danio Arena 中通过捕食、逃逸、饥饿、繁殖和环境选择展示 DNA—神经结构—行为—演化之间的完整闭环。**

当前版本为 v0.1，后续可根据实现难度和实际测试结果继续缩减、调整或扩展。
