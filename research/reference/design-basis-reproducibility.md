# EvoGenesis 复现性设计依据：seed 派生 与 数值确定性

> 搜索时间：2026-09-26 ｜ 用途：为核心机制文档 `src/evogenesis/core/核心机制与数据流.md` §10 #6「seed 派生函数形式」及 §3 复现判据提供权威依据。
> 证据清单见同目录 `design-basis-reproducibility.json`。本文件只做摘要与建议，不修改代码。

## 0. 项目现状（只读核对）

- 工具链：`numpy>=2.5.3`、`torch>=2.14.0`（`pyproject.toml`）。
- 现有代码：`src/evogenesis/core/seed.py` 仅 `set_global_seed(seed)`（`random.seed` / `np.random.seed` / `torch.manual_seed` / `cuda.manual_seed_all`），**尚无 namespace → 子种子的派生函数**。
- 文档状态：§10 #6 标为待定；现有复现判据为「同一 `(config 文件, master seed)` 在同设备、同线程数下结果一致；跨设备只要求统计等价」。

---

## 1. seed 派生依据（逐条）

### 1.1 官方文档

| 名称 | URL | 一句话 |
|---|---|---|
| NumPy — Parallel random number generation | https://numpy.org/doc/stable/reference/random/parallel.html | 官方给出 `SeedSequence.spawn` 树哈希：相近种子 → 相距很远的初始状态，碰撞上界约 `n²·2⁻¹²⁸`；并明确 **`root_seed + worker_id` 相加派生是不安全做法**，推荐 `[worker_id, root_seed]`（变化 ID 前置）。 |
| NumPy — `SeedSequence` 类 | https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html | 提供 `entropy / spawn_key / pool_size / generate_state / spawn` 全部官方 API；给出「记录 entropy 以便复现」的最佳实践。 |
| NumPy — `Philox` | https://numpy.org/doc/stable/reference/random/bit_generators/philox.html | 计数器型 RNG，不同 `key` 产生独立序列，支持 `advance/jumped`；保证「固定 seed 永远产生相同整数流」。 |
| NumPy — Compatibility policy | https://numpy.org/doc/stable/reference/random/compatibility.html | 逐位可复现的严格条件：同 BitGenerator、同 seed、同调用序列、同构建、同环境、**同机器**；不同 CPU 浮点实现会改变结果。 |
| JAX — PRNG Design (JEP 263) | https://docs.jax.dev/en/latest/jep/263-prng.html | 函数式 splittable PRNG：`split(key) = (hash key 0, hash key 1)`；目标是后端无关、对 `@jit` 边界不变。 |
| JAX — `jax.random` 模块 | https://docs.jax.dev/en/latest/jax.random.html | 现行 API `key / split / fold_in`；权衡表明确 threefry/philox **「identical across CPU/GPU/TPU ✅」**（指随机位流，非浮点结果）。 |
| PyTorch — `torch.Generator` | https://docs.pytorch.org/docs/2.14/generated/torch.Generator.html | `manual_seed(seed)`、`get_state()/set_state()`；CUDA 侧为 Philox4x32-10 流。注意种子位宽措辞不一致。 |

### 1.2 同行评审论文

| 名称 | URL | 一句话 |
|---|---|---|
| Salmon et al., *Parallel Random Numbers: As Easy as 1, 2, 3* (SC11, 2011) | https://doi.org/10.1145/2063384.2063405 | 计数器型 PRNG（AES/Threefish/Philox）的奠基论文；≥2⁶⁴ 条独立流，每条周期 ≥2¹²⁸，通过 BigCrush。 |
| Claessen & Pałka, *Splittable PRNGs Using Cryptographic Hashing* (ICFP 2013) | https://doi.org/10.1145/2503778.2503784 | 为「split 得到的子流可视为独立」给出形式化证明，是 JAX splittable 模型的理论依据。 |

**交叉验证**：NumPy `Philox` 文档引用 Salmon 2011；JAX `jax.random` 文档同时引用 Salmon 2011 与 Claessen & Pałka 2013。三者构成一致的证据链。

---

## 2. 数值 / 设备确定性依据（逐条）

| 名称 | URL | 一句话 |
|---|---|---|
| PyTorch — Reproducibility | https://docs.pytorch.org/docs/2.14/notes/randomness.html | **开篇即声明：CPU 与 GPU 即使同种子也不可复现**；给出 `manual_seed` / cuDNN `benchmark=False` / `deterministic=True` / DataLoader 播种的官方做法。 |
| PyTorch — `use_deterministic_algorithms` | https://docs.pytorch.org/docs/2.14/generated/torch.use_deterministic_algorithms.html | 强制确定性算子，无实现则报错；开启后 Inductor 进入 deterministic 模式；`fill_uninitialized_memory` 默认 True。 |
| PyTorch — `set_num_threads` | https://docs.pytorch.org/docs/2.14/generated/torch.set_num_threads.html | 设置 CPU intra-op 线程数，且必须在 eager/JIT/autograd 之前调用。 |
| NVIDIA cuBLAS — Results Reproducibility (2.1.4) | https://docs.nvidia.com/cuda/cublas/index.html#results-reproducibility | 同 toolkit + 同架构 + 同 SM 数量才逐位一致；**多并发 CUDA stream 会破坏**；此时设 `CUBLAS_WORKSPACE_CONFIG=:16:8` 或 `:4096:8`。 |
| Intel oneMKL — CNR | https://www.intel.com/content/www/us/en/developer/archive/training/conditional-numerical-reproducibility-cnr.html | CNR 前提之一：**计算线程数全程不变**；Strict CNR 使 `?gemm/?trsm/?symm` 与线程数无关。 |
| Python — `PYTHONHASHSEED` | https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED | 默认随机加盐；设整数即固定 hash 种子，`0` 禁用随机化。 |
| Goldberg 1991, *What Every Computer Scientist Should Know About Floating-Point Arithmetic* | https://doi.org/10.1145/103162.103163 | IEEE-754 浮点语义经典综述，解释舍入误差与非结合性。 |
| Demmel & Nguyen 2013, *Fast Reproducible Floating-Point Summation* | https://doi.org/10.1109/ARITH.2013.9 | 「动态调度 + 浮点非结合性」使并行归约难逐位复现；提出顺序无关求和技术。 |
| IEEE 754-2019 标准页 | https://standards.ieee.org/ieee/754/6210/ | 浮点标准（付费，本轮未抓正文，作为语义出处列出）。 |

---

## 3. 推荐采用（可直接写进规范）

### 3.1 seed 派生（推荐直接用，需项目定稿）

采用 NumPy `SeedSequence` 树哈希，二选一写死：

**(A) 命名空间列表法（最简，官方明文推荐）**

```python
NAMESPACE = {"mutation": 0, "crossover": 1, "development": 2, "arena_spawn": 3}
rng = numpy.random.default_rng([NAMESPACE[name], MASTER_SEED])
```

- 依据：官方明确 safe 用法为 `default_rng([worker_id, root_seed])`，且**变化 ID 必须前置**。
- 可复现：同一 `[namespace, master]` → 同一 `SeedSequence` → 同一初始状态。
- 互不相关：整数哈希（好雪崩性）混合熵，相近输入产生相距很远的初始状态；碰撞上界约 `n²·2⁻¹²⁸`（n=10⁶ 时约 2⁻⁸⁸）。

**(B) spawn 树法（等价，适合层级/实体级种子）**

```python
children = numpy.random.SeedSequence(MASTER_SEED).spawn(K)   # 只 spawn 一次，缓存
rng = numpy.random.default_rng(children[IDX[name]])
```

> ⚠️ 不要写 `SeedSequence(master).spawn(K)[i]`（每次重建再取第 i 个），会破坏构造顺序语义。

**喂给 PyTorch（组合用法待验证）**：

```python
child = numpy.random.SeedSequence([NAMESPACE[name], MASTER_SEED])
t_seed = int(child.generate_state(1, dtype=numpy.uint32)[0])
gen = torch.Generator(device="cpu").manual_seed(t_seed)
```

组件 API 均有官方文档，但该组合**未在任何官方来源出现**，须标为项目选定并做最小复现验证（同 master 两次进程 → 同 torch 序列）。

### 3.2 确定性开关清单（推荐直接用）

| 配置项 | 建议值 | 出处 |
|---|---|---|
| `torch.manual_seed` | 程序入口设 master seed | PyTorch Reproducibility |
| `random.seed` / `np.random.seed` | 同步设值（更推荐改用局部 Generator） | PyTorch Reproducibility |
| `torch.use_deterministic_algorithms` | `True, warn_only=False` | PyTorch API 文档 |
| `torch.backends.cudnn.benchmark` | `False` | PyTorch Reproducibility |
| `torch.backends.cudnn.deterministic` | `True` | PyTorch Reproducibility |
| `torch.utils.deterministic.fill_uninitialized_memory` | `True`（默认） | PyTorch API 文档 |
| `torch.set_num_threads(K)` | 固定 K，须在 eager/JIT/autograd 前 | PyTorch API；动机来自 oneMKL CNR |
| `PYTHONHASHSEED` | 整数（如 `0`） | Python 官方文档 |
| `OMP_NUM_THREADS` / `MKL_NUM_THREADS` | 与 ⑦ 对齐 | Intel oneMKL（待验证） |
| `CUBLAS_WORKSPACE_CONFIG` | `:4096:8`，**仅多 CUDA stream 时** | NVIDIA cuBLAS（待验证） |

### 3.3 跨设备无法逐字节一致的理由链（推荐直接用）

1. PyTorch 官方：CPU 与 GPU 同种子也不可复现，跨版本/提交/平台均不保证；
2. 同一运算在不同后端/硬件上实现与累加顺序不同，而浮点加法非结合（PyTorch SDPA 文档明写）；
3. 并行归约的调度/线程数改变归约树，同设备也可能不同（Demmel & Nguyen 2013）；
4. GPU 库的复现保证本身有条件：cuBLAS 限同架构 + 同 SM 数量 + 同 toolkit；cuDNN 因算法基准选择而变。

→ 规范沿用：**同设备 + 同线程数 → 逐位复现；跨设备 → 只要求统计等价。**

---

## 4. 没找到 / 待验证

- 无任何官方来源给出「namespace → 子种子」的命名约定，须项目自行定稿（即 §10 #6）。
- PyTorch 2.14 文档已删除 `CUBLAS_WORKSPACE_CONFIG` 说明，是否必需无 PyTorch 侧明文。
- 无来源证明 `set_num_threads` 改变数值结果；由 oneMKL CNR + 浮点非结合性旁证。
- IEEE 754-2019 正文付费未抓取，以 Goldberg 1991 + Demmel & Nguyen 2013 为可访问代理。
- NumPy 不承诺跨机器/跨设备随机流一致；「随机流跨设备一致」仅 JAX 计数器型路径可承诺，且不代表浮点结果一致。
- **待人工复核**：Goldberg 1991 在 OpenAlex 作者名显示为 `David Theo Goldberg`（元数据歧义）；Salmon 2011 PDF 取自作者站点而非出版方；各文档页均未标注许可证，报告中 `license` 置 `null`。

---

## 5. 结论分级速览

| 分级 | 项目 |
|---|---|
| **推荐直接用** | `SeedSequence` 树哈希派生（A/B 两式）；PyTorch `manual_seed` + `use_deterministic_algorithms(True)` + cuDNN 两开关；`set_num_threads` 固定；`PYTHONHASHSEED`；跨设备只求统计等价的判据 |
| **仅作参考** | JAX 式计数器型 split / NumPy `Philox(key=...)`（仅在要求随机流跨设备逐位一致时考虑） |
| **不建议** | 为随机流一致性引入 JAX；无条件设置 `CUBLAS_WORKSPACE_CONFIG`；`root_seed + worker_id` 相加派生 |
| **需进一步验证** | `generate_state → torch.Generator` 的组合写法；线程数对数值结果的影响；`CUBLAS_WORKSPACE_CONFIG` 是否必需；`MKL_CBWR=AVX2,STRICT` 对 PyTorch CPU 路径的作用 |
