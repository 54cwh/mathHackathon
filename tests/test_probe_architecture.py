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
#: 主样本规模：这一档同时覆盖三条分支 —— 可构造 12 / 不可构造 2 / viable 1
#: （``n=3`` 时 viable 为 0，``n=1`` 时三者都退化，故不选）。
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


def test_empty_subset_degrades_gracefully(probe):
    """子集可能**一个个体都没有**（seed 1103 的前 3 个：viable = 0）——
    汇总块必须降级成 ``n = 0`` + ``None``，而不是让整个 probe 崩掉。

    这是本次 probe 踩到的真实崩溃路径（``min() arg is an empty sequence``），
    不是假想边界。
    """
    tiny = probe.probe_architecture([PROBE_SEED], n_individuals=3)
    empty = {"n": 0, "min": None, "median": None, "mean": None, "max": None}

    assert tiny["pooled_viable"]["n_individuals"] == 0
    assert tiny["pooled_viable"]["n_neurons"] == empty
    assert tiny["pooled_viable"]["cell_type_counts"]["motor"] == empty
    # 空子集不影响其余分支
    assert tiny["pooled"]["n_individuals"] == 3
    assert tiny["pooled"]["n_viable"] == 0


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


def test_unbuildable_individuals_are_recorded_not_skipped(payload):
    """构造 `DanioNet` 失败的个体必须留痕（`danionet_built=false` + 原因 + 空 trainable）。

    seed 1103 x 14 里确有 2 个（motor 池为空的个体）；「一个都没失败」说明发育口径变了，
    也要在本测试里暴露出来 —— 否则这条守护会悄悄失效。
    """
    rows = payload["per_individual"]
    built = [r for r in rows if r["danionet_built"]]
    unbuilt = [r for r in rows if not r["danionet_built"]]

    assert built and unbuilt, "本档样本应同时含可构造与不可构造个体"

    for row in built:
        assert row["danionet_error"] is None
        assert row["theta_shape"] is not None
        assert isinstance(row["trainable_elements"], int)

    for row in unbuilt:
        assert row["danionet_error"], "构造失败必须记下原因"
        assert "motor" in row["danionet_error"], row
        assert row["theta_shape"] is None
        assert row["trainable_elements"] is None
        assert row["support_edges"] > 0, "支撑本身仍应可测（失败只发生在 DanioNet 装配）"


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
