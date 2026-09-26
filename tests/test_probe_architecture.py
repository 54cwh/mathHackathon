"""架构尺寸 probe（`scripts/probe_architecture.py`）的守护测试。

守住三件事，对应论文「禁止填空」的凭证要求：

1. **同 seed 可复现**：同一入参两次调用 payload 完全相同（含 ``digest``），且
   ``digest`` 确实是内容哈希（改一个数字就变）—— 否则「可重生成」只是口号。
2. **字段齐全且自洽**：边数 <= N(N-1)、密度 == 边数 / (N(N-1))、六类计数之和 == N、
   左右 motor 池之和 == motor 计数、活跃数 == N；``Theta`` 张量 48x48 = 2304 且
   **支撑内可训练元素数 == 支撑边数**（两者同源，不等即说明 `DanioNet` 的支撑口径漂了）。
3. **没有静默丢个体**：``pooled`` 的 n 与 ``per_individual`` 长度一致，
   构造 `DanioNet` 失败的个体被**记下来**（``danionet_built=false`` + 原因），不静默跳过。

小样本跑（``n=3``），`develop` 单次约 10ms，不必跑满 42。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_architecture.py"

#: 小样本 probe 的固定 seed（正式 seed 轴的第一项，见 `configs/experiment_seeds.yaml`）。
PROBE_SEED = 1103
#: 主样本规模：2026-09-26 实测本档 14 个体**全部可构造且全部通过 viability**
#: （§7 修复前该档为 可构造 12 / 不可构造 2 / viable 1，且 ``n=3`` 时 viable 为 0）。
#: 旧分档已不可达，故「失败 / 空子集」两条分支改由下方**显式注入**钉住，与真实读数解耦。
PROBE_N = 14

#: 密度是 6 位小数舍入后的值，容差取 1e-6（舍入误差上界 5e-7）。
DENSITY_TOL = 1e-6


def _load_script():
    """把脚本当模块载入（`scripts/` 不是包，故走 importlib 按路径载入）。"""
    spec = importlib.util.spec_from_file_location("probe_architecture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def probe():
    return _load_script()


@pytest.fixture(scope="module")
def payload(probe):
    """小样本 payload（module 级共享，避免每个测试各跑一次发育）。"""
    return probe.probe_architecture([PROBE_SEED], n_individuals=PROBE_N)


# ---------------------------------------------------------------------------
# 1. 可复现
# ---------------------------------------------------------------------------


def test_same_input_is_byte_identical(probe, payload):
    """同一入参两次调用：payload（含 digest）完全相同。"""
    again = probe.probe_architecture([PROBE_SEED], n_individuals=PROBE_N)
    assert again == payload
    assert json.dumps(again, sort_keys=True) == json.dumps(payload, sort_keys=True)


def test_digest_is_content_hash(probe, payload):
    """digest 可自校验；且改一个数字必然改 digest（否则 digest 是装饰）。"""
    assert payload["digest"] == probe.content_digest(payload)

    tampered = json.loads(json.dumps(payload))
    tampered["per_individual"][0]["support_edges"] += 1
    assert probe.content_digest(tampered) != payload["digest"]


def test_different_seed_gives_different_architecture(probe, payload):
    """不同 seed 必须给出不同个体 —— 否则「seed 依赖」是假的。"""
    other = probe.probe_architecture([PROBE_SEED + 1], n_individuals=PROBE_N)
    assert [r["n_neurons"] for r in other["per_individual"]] != [
        r["n_neurons"] for r in payload["per_individual"]
    ]


def test_empty_subset_degrades_gracefully(probe, payload):
    """子集可能**一个个体都没有** —— 汇总块必须降级成 ``n = 0`` + ``None``，而不是崩掉。

    这是本次 probe 踩到的真实崩溃路径（``min() arg is an empty sequence``），不是假想边界。
    2026-09-26 起 §7 修复使本档 14/14 全部 viable、全部可构造，真实数据**再也不会**产出空子集，
    故这里改用**显式注入**空行表来钉住该降级路径（否则这条守护会因前提消失而静默失效）；
    同时把真实子集的当前读数一并钉住。
    """
    empty = {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    domains = tuple(payload["domains"])

    injected = probe._aggregate([], domains)
    assert injected["n_individuals"] == 0
    assert injected["n_neurons"] == empty
    assert injected["cell_type_counts"]["motor"] == empty
    assert injected["n_viable"] == 0 and injected["n_danionet_built"] == 0

    # 真实 n=3 子集的当前读数：全 viable（旧档此处为 0 —— 见 PROBE_N 注）
    tiny = probe.probe_architecture([PROBE_SEED], n_individuals=3)
    assert tiny["pooled_viable"]["n_individuals"] == 3
    assert tiny["pooled"]["n_individuals"] == 3
    assert tiny["pooled"]["n_viable"] == 3
# ---------------------------------------------------------------------------
# 2. 字段齐全 + 自洽
# ---------------------------------------------------------------------------


def test_payload_has_required_blocks(payload):
    """论文要引用的每个量都必须有落点（少一个就是「引用无凭证」）。"""
    for key in (
        "probe",
        "generated_by",
        "master_seeds",
        "n_individuals_per_seed",
        "config_path",
        "config_sha256",
        "domains",
        "max_nodes",
        "target_density",
        "per_individual",
        "per_seed",
        "pooled",
        "pooled_viable",
        "pooled_danionet_built",
        "theta",
        "median_individual",
        "digest",
    ):
        assert key in payload, f"payload 缺字段 {key}"

    entry = payload["per_individual"][0]
    for key in (
        "master_seed",
        "index",
        "genome_id",
        "fish_id",
        "n_neurons",
        "active_neurons",
        "support_edges",
        "support_density",
        "cell_type_counts",
        "motor_left",
        "motor_right",
        "phenotype_viable",
        "viability_reason",
        "danionet_built",
        "danionet_error",
        "theta_shape",
        "trainable_elements",
    ):
        assert key in entry, f"per_individual 缺字段 {key}"


def test_per_individual_is_self_consistent(payload):
    """结构自洽：边数 <= N(N-1)、密度 == 边数/(N(N-1))、六类计数之和 == N、
    motor 池之和 == motor 数。"""
    domains = payload["domains"]
    for row in payload["per_individual"]:
        n = row["n_neurons"]
        assert 1 < n <= payload["max_nodes"], row
        assert row["active_neurons"] == n, "本次冻结配置下 M 全活跃；不等说明发育口径变了"

        assert 0 <= row["support_edges"] <= n * (n - 1), row
        expected = row["support_edges"] / (n * (n - 1))
        assert abs(row["support_density"] - expected) <= DENSITY_TOL, row

        assert set(row["cell_type_counts"]) == set(domains), row
        assert sum(row["cell_type_counts"].values()) == n, row

        assert row["motor_left"] + row["motor_right"] == row["cell_type_counts"]["motor"], row


def test_pooled_aggregates_match_rows(payload):
    """汇总块必须由 per_individual 直接推出（且缺口用 n 显式暴露，不静默丢个体）。"""
    rows = payload["per_individual"]
    pooled = payload["pooled"]
    assert pooled["n_individuals"] == len(rows)
    assert pooled["n_danionet_built"] == sum(1 for r in rows if r["danionet_built"])
    assert pooled["n_viable"] == sum(1 for r in rows if r["phenotype_viable"])

    neurons = sorted(r["n_neurons"] for r in rows)
    assert (pooled["n_neurons"]["min"], pooled["n_neurons"]["max"]) == (neurons[0], neurons[-1])
    assert pooled["n_neurons"]["n"] == len(rows)

    assert payload["pooled_viable"]["n_individuals"] == pooled["n_viable"]
    assert payload["pooled_danionet_built"]["n_individuals"] == pooled["n_danionet_built"]


def test_individuals_are_never_silently_dropped(payload):
    """个体只增不减：``pooled`` 的 n 与 ``per_individual`` 长度一致，不漏也不插补。

    2026-09-26 实测：§7 发育门禁修复后 motor 池恒非空，本档 14/14 **全部可构造且全部 viable**
    （旧档为 12 可构造 / 1 viable）。**数值本身即是守护** —— 口径再变时这里红灯，而不是静默通过。
    """
    rows = payload["per_individual"]
    assert payload["pooled"]["n_individuals"] == len(rows) == PROBE_N
    assert payload["pooled"]["n_danionet_built"] == len(rows)
    assert payload["pooled"]["n_viable"] == len(rows)

    for row in rows:
        assert row["danionet_built"] is True
        assert row["danionet_error"] is None
        assert row["theta_shape"] == [1, payload["max_nodes"], payload["max_nodes"]]
        assert isinstance(row["trainable_elements"], int)
        assert row["trainable_elements"] == row["support_edges"]
        assert row["support_edges"] > 0


def test_unbuildable_rows_are_recorded_not_imputed(probe, payload):
    """构造 `DanioNet` 失败的个体必须留痕（``danionet_built=false`` + 原因 + **不插补**可训练数）。

    本档已无失败个体（见上一条），故这里**显式注入**一行失败记录走 `_aggregate`，钉住三件事：
    (i) 失败行仍计入 ``n_individuals``（不静默丢）、(ii) 不计入 ``n_danionet_built`` / ``n_viable``、
    (iii) 其余数值字段照常参与统计。注入行的字段形状照 `_probe_individual` 的失败分支构造。
    """
    domains = tuple(payload["domains"])
    built = {
        "master_seed": PROBE_SEED, "index": 0, "genome_id": "g", "fish_id": "f",
        "n_neurons": 40, "active_neurons": 40, "support_edges": 238,
        "support_density": round(238 / (40 * 39), 6),
        "cell_type_counts": {d: 6 for d in domains},
        "motor_left": 3, "motor_right": 3,
        "phenotype_viable": True, "viability_reason": None,
        "danionet_built": True, "danionet_error": None,
        "theta_shape": [1, 48, 48], "trainable_elements": 238,
    }
    failed = dict(built)
    failed.update({
        "index": 1, "n_neurons": 36, "active_neurons": 36, "support_edges": 195,
        "support_density": round(195 / (36 * 35), 6),
        "motor_left": 0, "motor_right": 0,
        "phenotype_viable": False, "viability_reason": "missing_fate:motor",
        "danionet_built": False, "danionet_error": "motor pool empty",
        "theta_shape": None, "trainable_elements": None,
    })

    agg = probe._aggregate([built, failed], domains)
    assert agg["n_individuals"] == 2, "失败行不得被静默丢弃"
    assert agg["n_danionet_built"] == 1
    assert agg["n_viable"] == 1
    assert agg["n_neurons"]["n"] == 2
    assert (agg["n_neurons"]["min"], agg["n_neurons"]["max"]) == (36, 40)
# ---------------------------------------------------------------------------
# 3. Theta 张量与可训练元素数
# ---------------------------------------------------------------------------


def test_theta_tensor_shape_and_trainable_elements(payload):
    """`Theta` padding 到 ``development.max_neurons``，支撑内才可训练 —— 两者都要对上。"""
    max_nodes = payload["max_nodes"]
    theta = payload["theta"]

    assert theta["max_nodes"] == max_nodes == 48
    assert theta["elements_per_individual"] == max_nodes**2 == 2304
    assert theta["shape_per_individual"] == [[1, max_nodes, max_nodes]]

    built = [r for r in payload["per_individual"] if r["danionet_built"]]
    assert built, "小样本里应至少有一个可构造的个体"
    for row in built:
        assert row["theta_shape"] == [1, max_nodes, max_nodes]
        # 支撑边数与 DanioNet.support 的元素和同源；不等说明支撑口径漂了
        assert row["trainable_elements"] == row["support_edges"], row
        assert row["trainable_elements"] <= row["n_neurons"] * (row["n_neurons"] - 1)

    # 可训练数必须显著小于张量总元素数（否则「支撑冻结」是空话）
    assert theta["trainable_elements"]["max"] < theta["elements_per_individual"]


def test_median_individual_is_a_real_row(payload):
    """``median_individual`` 必须是 per_individual 中真实存在的一行（可直接引用）。"""
    median_row = payload["median_individual"]
    assert median_row in payload["per_individual"]


# ---------------------------------------------------------------------------
# 4. CLI 端到端
# ---------------------------------------------------------------------------


def test_cli_writes_json_and_matches_in_process_payload(tmp_path: Path, payload):
    """入口可跑、落盘可读，且**跨进程**得到同一 digest（可重生成的最低要求）。"""
    out = tmp_path / "architecture_probe.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seeds",
            str(PROBE_SEED),
            "--n-individuals",
            str(PROBE_N),
            "--json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert out.is_file()

    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["digest"] == payload["digest"]
    assert written["per_individual"] == payload["per_individual"]
