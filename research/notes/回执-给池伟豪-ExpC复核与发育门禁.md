# 回执：给池伟豪 —— Exp C 复核 + 发育门禁两条独立实测

**来自**：李辰钊（Exp C / 基线对照侧）　**日期**：2026-09-26
**性质**：独立复核回执 + 两个请你知悉/拍板的点。**不阻塞**你手上的活。

---

## 一句话

你 rgcd.py 的**两处确定性重定我都独立实测确认了**，并各自复现了你记录的动因。`_clamp_domain_identity_spread` 落地后，Exp C 需要的 12 个 viable 在 3 个 seed 上**全部以 200/200 满足**。

---

## 1. 你的 `missing_fate` 观测，我独立复现到了（在我先跑的那一版上）

我 09-26 先按你工作区当时的 `rgcd.py`（blob `6451688`，**只有 ρ 重定、还没有 `_clamp_domain_identity_spread`**）跑了启动前门（`n_danio=200`，`experiment_id=expC`）：

| seed | viable | 拒因分布 |
|---|---|---|
| 1103 | **20/200（10.0%）** | `missing_fate:threat` 124 / `prey,threat` 48 / `prey` 8 / `ok` 20 |
| 2207 | 200/200（100%） | 全 `ok` |
| 3301 | 200/200（100%） | 全 `ok` |

即：**ρ 重定只解开了 ρ 轴，命运轴仍是逐 seed 的整跑一枚硬币**——与你 docstring 里写的「20 个 seed 中 5 个（25%）使某个域被系统性改判，该 seed 下 33%–67% 个体不可育」是同一现象。我这边落在 1103 上（10%），另两个 seed 落在另一端（100%）。

## 2. 你的 `_clamp_domain_identity_spread` 修复，实测确认有效

换成你现在的 `rgcd.py`（blob `8847959`）+ `development/config.py`（`3f712b3`）后：

```
seed=1103  viable=200/200  [('ok', 200)]
seed=2207  viable=200/200  [('ok', 200)]
seed=3301  viable=200/200  [('ok', 200)]
```

`missing_fate` 在默认配置下如你 docstring 所述不再触发；`rho_w0_target=0.9` 令 (iv) 亦不再绑定。**Exp C 的 12 viable 门（默认抛错、`--allow-partial` 才降级）在三个 seed 上都是轻松通过。**

## 3. 两个连带影响（我已记录，供你知情）

1. **`n_danio=200` 的签署依据已失效。** 200 是按「viable ≈ 10%、P(≥12) ≈ 0.98」推的；新 regime 下 viability 非 0 即 ~100%（fate 轴已不可达，ρ 轴已重定），故 200 是**超额 17 倍**。降到 12–24 就够。本轮已按 200 跑，**不改**（改配置要重跑，且 200 不影响正确性，只是慢一点）。
2. **`experiment/实验与评价体系.md` §3.3 里我记录的实测 viable 数（33/35/28，7.0–8.8%）基于旧 `rgcd`，现已失效。** 我会在 Exp C 跑完后按第 2 节的 200/200 回写。

## 4. 请你拍板：把这 9 个文件作为**一个连贯提交**落地

它们目前全部在未暂存区（`git status` 9 个 `M`）：

```
configs/default_model.yaml            (+ rho_w0_target: 0.9)
src/evogenesis/core/config.py         (+ ConnectomeConfig.rho_w0_target: float)
src/evogenesis/core/seed.py           (+ development_params = 17)
src/evogenesis/development/config.py
src/evogenesis/development/grn.py
src/evogenesis/development/rgcd.py    (fate clamp + rho 重定)
tests/test_config.py  tests/test_rgcd.py  tests/test_seed.py
```

**为什么必须一起提交**：`core/config.py` 的 `rho_w0_target` 是**必填字段**，而它只由 `configs/default_model.yaml` 提供。两者一个提交、一个不提交都会让另一侧加载失败（我踩过：用 HEAD 的 yaml 配工作区的 `config.py` ⇒ `ValidationError: connectome.rho_w0_target Field required`）。当前 HEAD 本身自洽但**不能复现任何一次 run**——因为 run 用的是你工作区的实现。

**我可以帮的**：如果你希望我来落这个提交（只 add 这 9 个文件、不碰 frontend），说一声即可；否则请你自己提交，我不动你的在制品。

## 5. 一个建议写进 limitation 的点（你 docstring 已如实写明）

`_clamp_domain_identity_spread` 的口径代价是「**默认配置下 §6 的 `argmax z` 恒等于谱系域**」。也就是：默认配置下细胞身份分化不再有随机性，`missing_fate` 这条判据在默认配置里**结构性地不可达**（判因词表保留 token 是对的）。

评审若问「为什么默认配置下命运采纳是确定性的」，建议在 `RGCD数学模型.md` §7 或论文 limitations 里用一句点明这是**为消除「每-seed 抽签型门禁」而付的可识别性代价**，而不是被掩盖的失因。这属于你的 lane，我只是提示。

## 6. Exp C 正在跑，用的就是你工作区这两个 blob

- 启动来源已存档（`config_snapshot/` 只含配置、不含代码，故代码来源另记）：
  `results/runs/expC_launch_provenance_v2.json`
  —— 记了本轮依赖的 6 个上游模块 blob 哈希，其中与发育相关的正是 `rgcd.py=8847959`、`development/config.py=3f712b3`。
- **请在 Exp C 跑完（约 1.5 h）前不要改 `rgcd.py` / `development/config.py`**；若你需要改，告诉我，我按新 blob 重跑并在 provenance 里记明。改其他文件（tests/、docs/）不影响在跑的进程。

---

## 附：复现命令

```bash
# 启动前门（viable 比例）
uv run --frozen python -c "
import collections
from evogenesis.pipeline import (load_model_chain_config, initial_population,
                                 motif_catalog, phenotypes_of)
chain = load_model_chain_config('configs/default_model.yaml')
for seed in (1103, 2207, 3301):
    pop = initial_population(master_seed=seed, experiment_id='expC', n=200, layout=chain.layout)
    ph = phenotypes_of(pop, motif_catalog(seed, chain.layout),
                       master_seed=seed, config=chain.rgcd, device='cpu')
    print(seed, sum(p.viable for p in ph), '/200',
          collections.Counter(p.viability_reason for p in ph).most_common(2))
"
```

证据留档：`results/runs/expC_viability_probe.json`（v1）、`results/runs/expC_launch_provenance_v2.json`（v2）。
（均在 `results/`，按 `.gitignore:53` 不入库，故结论写在本文件里。）

---

## 追加（同日稍后）—— §4 与 §6 已由你闭合，本轮 provenance 升级为「可由 commit 复现」

发出上文的同一天，你已落地 `3ab3e0e fix(development): Θ_D 改每-seed，并修 ρ(W⁰) 与 U 跨域散布两处校准失配`。核对后：

- **§4 不必再做**：那 9 个文件已随 `3ab3e0e` 提交（我逐一核对了 worktree 与 `HEAD:` 的 blob 一致）。
- **§6 的顾虑解除**：Exp C v2 启动时依赖的 6 个上游模块 blob 与 `3ab3e0e` **逐一相同**
  （`core/seed.py`、`core/config.py`、`development/{config,grn,rgcd}.py`、`configs/default_model.yaml`），
  故本轮 run **可由该 commit 复现**，不再依赖未提交工作区；原先记的
  `results/runs/expC_launch_provenance_v2.json` 仍是准确的来源快照。
- 因此 §6 里「跑完前别改 rgcd.py / development/config.py」**已无必要**——它们已在 `3ab3e0e` 冻结；
  若你后续再改，请告诉我，我按新 commit 重跑。

上文 §4「请你拍板」一节据此视为**已闭合**。§3 的两个连带影响（`n_danio=200` 依据失效、
§3.3 旧 viable 数失效）仍待我在 Exp C 跑完后回写。
