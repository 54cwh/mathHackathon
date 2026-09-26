# ExpertPolicy 基线（冻结）

> 状态：**已冻结（2026-09-26）**。文件 `exp_arena_expert_ref_v3_summary.json` 为跨 seed 汇总。

## 内容
- 基线：3 个正式种子 `1103 / 2207 / 3301` × 600 步 × 12 鱼（ExpertPolicy 驱动，非模型结果）。
- 指标（mean ± std, n=3）：survival 0.9188±0.1362、capture_rate 0.0030±0.0014、
  prey_capture 0.5148±0.2972、escape_success 0.3032±0.1354、
  energy_efficiency −9.25e−4±1.62e−4、composite_fitness 0.3828±0.0725。

## 复现命令
```bash
uv run python scripts/run_arena.py --experiment-id exp_arena_expert_ref_v3 --seeds 1103,2207,3301
```
- 配置：`configs/default_arena.yaml`（默认；含已冻结的 arena 参数，见 `docs/参数总表.json` v0.14）。
- 复现核验：在 commit `82d8dcc` 上重跑，与本文件**逐位一致**。

## 适用边界
- 仅作 **ExpertPolicy 参考基线 / 环境 pre-check / 消融对照**，不是 DanioNet 模型正式结果。
- ExpertPolicy 只读 `obs[0..5]` 与 `obs[11]`，**不读** `obs[6..10]`，故 A5 looming 改动不影响本基线。
- 冻结口径：arena 参数（含 24 个原「标定占位」）已按**设计选择（D）**定稿；**若任何取值变更，本基线解冻并须重跑**（`docs/参数总表.json`）。
