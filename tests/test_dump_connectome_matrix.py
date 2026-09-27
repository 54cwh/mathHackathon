"""F7 连接矩阵落盘（`scripts/dump_connectome_matrix.py`）的守护测试。

守住五件事：

1. **可复现**：同入参两次运行 payload 相同（含 ``digest``），且落盘的 JSON / CSV
   逐字节一致 —— 本产物是 F7 的**唯一**数据源，「可重生成」必须是真的。
2. **48x48 与补零纪律**：形状 ``48 x 48 = 2304``；``N .. 47`` 的行 / 列恒 0；对角恒 0
   （``allow_self_loops = false``）。
3. **与 `probe_architecture` 口径一致**：同一 ``(seed, index)`` 上 ``N`` / 支撑边数 /
   可训练元素数必须与 probe 逐值相等（本脚本直接调 probe 的函数，故这同时钉住了
   「复用而非重写」）；且 ``trainable_elements == support_edges``。
4. **Dale 符号自洽**（`RGCD §10`）：符号由**突触前**（行）类型决定 —— 抑制性行的支撑元
   全 ``< 0``、其余行的支撑元全 ``> 0``。
5. **只重发育代表个体是安全的**：代表个体的活跃块必须等于「整种群批量发育」的同一
   个体（``develop`` 的随机流按 ``(master_seed, index)`` 派生，与调用顺序无关）。
   破了这条，落盘的矩阵会静默地不是种群里的那个个体。

另有一条**论文数字锚**（``test_pooled_sizes_match_the_method_section_anchor``）：
「N 中位 37.0（27--43）、支撑连接中位 192.5 条（105--289）、密度中位 0.149」就是本产物
在 3 个正式 seed x 14 个体上的读数
（2026-09-27 §5 通道 β 0.0→1.0 后更新；旧读数 36.5 / 195 / 0.149）。
口径漂了要在这里红灯，而不是等论文被审稿人抓。

小样本跑（``n=14``，`develop` 单次约 10ms）。
"""

from __future__ import annotations

import csv
import importlib.util
import json
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from evogenesis.pipeline.model_chain import (
    initial_population,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dump_connectome_matrix.py"
CONFIG_PATH = ROOT / "configs" / "default_model.yaml"

#: 主样本 seed（正式 seed 轴之首，`configs/experiment_seeds.yaml`）。
PROBE_SEED = 1103
#: 三个正式 seed（`02-method.tex` 的「3 个正式 seed x 14 个体共 42 个基因型」）。
FORMAL_SEEDS = (1103, 2207, 3301)
#: 每 seed 个体数（与 `probe_architecture` / F6 同档，口径可比）。
SAMPLE_N = 14


def _load_script():
    """把脚本当模块载入（`scripts/` 不是包，故走 importlib 按路径载入）。"""
    name = "dump_connectome_matrix"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dump():
    return _load_script()


@pytest.fixture(scope="module")
def payload(dump):
    """小样本 payload（module 级共享，避免每个测试各跑一次发育）。"""
    return dump.build_payload([PROBE_SEED], n_individuals=SAMPLE_N)


@pytest.fixture(scope="module")
def formal_payload(dump):
    """3 个正式 seed 的 payload（只给论文数字锚用一次）。"""
    return dump.build_payload(list(FORMAL_SEEDS), n_individuals=SAMPLE_N)


# ---------------------------------------------------------------------------
# 1. 可复现
# ---------------------------------------------------------------------------


def test_same_input_is_byte_identical(dump, payload):
    """同一入参两次调用：payload（含 digest）完全相同，JSON 文本逐字节相同。"""
    again = dump.build_payload([PROBE_SEED], n_individuals=SAMPLE_N)
    assert again == payload
    assert json.dumps(again, sort_keys=True) == json.dumps(payload, sort_keys=True)


def test_written_files_are_byte_identical(dump, payload, tmp_path):
    """落盘文件逐字节一致（含 CSV 的换行符不随平台漂）。"""
    first = tmp_path / "a"
    second = tmp_path / "b"
    dump.write_json(payload, first / "m.json")
    dump.write_csv(payload, first / "m.csv")
    dump.write_json(payload, second / "m.json")
    dump.write_csv(payload, second / "m.csv")
    assert (first / "m.json").read_bytes() == (second / "m.json").read_bytes()
    assert (first / "m.csv").read_bytes() == (second / "m.csv").read_bytes()


def test_digest_is_content_hash(dump, payload):
    """digest 可自校验；改一个数字必然改 digest（否则 digest 是装饰）。"""
    assert payload["digest"] == dump.load_probe_module().content_digest(payload)

    tampered = json.loads(json.dumps(payload))
    tampered["representatives"][0]["support_edges"] += 1
    assert dump.load_probe_module().content_digest(tampered) != payload["digest"]


def test_load_payload_rejects_tampered_digest(dump, payload, tmp_path):
    """读回时校验 digest —— 手工改过 JSON 就不能再当凭证用。"""
    path = tmp_path / "m.json"
    dump.write_json(payload, path)
    assert dump.load_payload(path) == payload

    broken = json.loads(path.read_text(encoding="utf-8"))
    broken["max_nodes"] = 47
    path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        dump.load_payload(path)


# ---------------------------------------------------------------------------
# 2. 48x48 与补零纪律
# ---------------------------------------------------------------------------


def test_matrix_is_48x48_with_zero_padding_and_no_self_loops(payload):
    max_nodes = payload["max_nodes"]
    assert max_nodes == 48
    assert max_nodes**2 == 2304

    for rep in payload["representatives"]:
        n = rep["n_neurons"]
        w0 = np.asarray(rep["w0"], dtype=float)
        support = np.asarray(rep["support"], dtype=int)

        assert w0.shape == (max_nodes, max_nodes), rep["index"]
        assert support.shape == (max_nodes, max_nodes), rep["index"]
        assert np.asarray(rep["theta"]).shape == (max_nodes, max_nodes)
        assert rep["theta_shape"] == [1, max_nodes, max_nodes]

        # 补零区（真实槽位之外）必须**整块**为 0 —— 这正是「容量 48 != 实际 N」的证据
        assert np.count_nonzero(w0[n:, :]) == 0
        assert np.count_nonzero(w0[:, n:]) == 0
        assert np.count_nonzero(support[n:, :]) == 0
        assert np.count_nonzero(support[:, n:]) == 0

        # allow_self_loops=false：对角恒 0（支撑与权重都是）
        assert np.count_nonzero(np.diagonal(w0)) == 0
        assert np.count_nonzero(np.diagonal(support)) == 0

        assert rep["neuron_mask"][:n] == [True] * n
        assert rep["neuron_mask"][n:] == [False] * (max_nodes - n)


def test_support_coordinates_are_sorted_and_match_the_mask(payload):
    for rep in payload["representatives"]:
        support = np.asarray(rep["support"], dtype=int)
        rows, cols = np.nonzero(support)
        assert rep["support_coordinates"] == [
            [int(r), int(c)] for r, c in zip(rows, cols, strict=True)
        ]
        assert len(rep["support_coordinates"]) == rep["support_edges"]


# ---------------------------------------------------------------------------
# 3. 与 probe_architecture 口径一致
# ---------------------------------------------------------------------------


def test_support_edges_match_the_architecture_probe(dump, payload):
    """同一 (seed, index) 上，本产物的尺寸必须与 `probe_architecture` 逐值相等。

    这是「口径不分叉」的机械凭证：本脚本把 probe 的记录嵌进 ``probe_record``，
    但**断言用的是现算一遍的 probe**（而不是信嵌入副本），否则嵌入副本可以自说自话。
    """
    probe = dump.load_probe_module()
    fresh = probe.probe_architecture([PROBE_SEED], n_individuals=SAMPLE_N)
    index = {(r["master_seed"], r["index"]): r for r in fresh["per_individual"]}

    for rep in payload["representatives"]:
        record = index[(rep["master_seed"], rep["index"])]
        assert rep["n_neurons"] == record["n_neurons"]
        assert rep["support_edges"] == record["support_edges"]
        assert rep["trainable_elements"] == record["trainable_elements"]
        assert rep["support_density"] == record["support_density"]
        # 嵌入副本也必须与重算的一致（防止嵌入路径被改坏）
        assert rep["probe_record"]["support_edges"] == record["support_edges"]


def test_support_edges_equal_trainable_elements(payload):
    """支撑边数 == ``DanioNet.support`` 的元素和 == Theta 的可训练元素数。"""
    for rep in payload["representatives"]:
        support = np.asarray(rep["support"], dtype=int)
        assert int(support.sum()) == rep["support_edges"]
        assert rep["trainable_elements"] == rep["support_edges"]
        # 与单元素计数同源
        assert sum(rep["support_edges_by_pre_type"].values()) == rep["support_edges"]
        assert sum(rep["support_edges_by_post_type"].values()) == rep["support_edges"]
        assert rep["excitatory_edges"] + rep["inhibitory_edges"] == rep["support_edges"]
        assert (
            rep["support_edges_by_pre_type"][payload["domains"][rep["inhibitory_index"]]]
            == rep["inhibitory_edges"]
        )


def test_representative_selection_rule_is_the_buildable_median(payload):
    """代表个体 = 可构造子集里 ``|N - median(N)|`` 最小的那个（并列取小 index）。"""
    records = payload["architecture_probe"]["per_individual"]
    for seed in payload["master_seeds"]:
        built = sorted(
            (r for r in records if r["master_seed"] == seed and r["danionet_built"]),
            key=lambda r: r["index"],
        )
        assert built, "本档样本每 seed 都应至少有一个可构造个体"
        target = statistics.median([r["n_neurons"] for r in built])
        expected = sorted(built, key=lambda r: (abs(r["n_neurons"] - target), r["index"]))[0]
        chosen = [r for r in payload["representatives"] if r["master_seed"] == seed]
        assert len(chosen) == payload["representatives_per_seed"]
        assert chosen[0]["index"] == expected["index"]
        assert chosen[0]["n_neurons"] == expected["n_neurons"]


def test_pooled_sizes_match_the_method_section_anchor(formal_payload):
    """论文 §「48-node 的含义」引用的数字必须能在本产物上重算出来。

    `paper/latex/sections/02-method.tex` 写的「3 个正式 seed x 14 个体共 42 个基因型上实测：
    N 中位 37.0（27--43），支撑连接中位 192.5 条（105--289），密度中位 0.149」。
    **若此断言失败：不要改断言去迁就** —— 要么 `develop` 的随机数纪律被破坏，
    要么 02-method.tex 的数字已过期，两者都必须先查清。
    2026-09-26：§7 发育门禁修复（`U` 散布钳制 + `W⁰` 谱半径归位）改变了表型规模，
    由 36（26--44）/ 186（94--287）/ 0.148 移至本值；论文与断言同批更新。
    2026-09-27：§5 基因组通道 β 0.0 → 1.0（用户授权）+ K=16，表型规模再移至
    37.0（27--43）/ 192.5（105--289）/ 0.149。本次成因是**配置变更**（非随机数纪律被破坏），
    依本 docstring 的处置：论文 02-method / 06-limitations / 04-baselines 与断言**同批**更新。
    """
    pooled = formal_payload["architecture_probe"]["pooled"]
    assert pooled["n_individuals"] == len(FORMAL_SEEDS) * SAMPLE_N == 42

    assert pooled["n_neurons"]["median"] == 37.0
    assert (pooled["n_neurons"]["min"], pooled["n_neurons"]["max"]) == (27, 43)

    assert pooled["support_edges"]["median"] == 192.5
    assert (pooled["support_edges"]["min"], pooled["support_edges"]["max"]) == (105, 289)

    assert round(pooled["support_density"]["median"], 3) == 0.149
    # 支撑远小于张量容量：这条对比是 F7 (a)/(d) 面板的立论基础
    assert pooled["support_edges"]["median"] < formal_payload["max_nodes"] ** 2


# ---------------------------------------------------------------------------
# 4. Dale 符号自洽
# ---------------------------------------------------------------------------


def test_dale_sign_is_decided_by_the_presynaptic_type(payload):
    """`RGCD §10`：符号由**突触前**（行）类型定，抑制性 -> -1、其余 -> +1。"""
    for rep in payload["representatives"]:
        n = rep["n_neurons"]
        w0 = np.asarray(rep["w0"], dtype=float)[:n, :n]
        support = np.asarray(rep["support"], dtype=bool)[:n, :n]
        inhibitory_index = rep["inhibitory_index"]
        cell_type = np.asarray(rep["cell_type"], dtype=int)[:n]
        assert rep["support_edges_by_pre_type"]["inhibitory"] == rep["inhibitory_edges"]

        is_inhibitory = cell_type == inhibitory_index
        assert is_inhibitory.any() and (~is_inhibitory).any(), "六类里应有抑制性也有非抑制性"

        # 抑制性行：支撑元全 <= 0 且至少一个 < 0
        inhibitory_block = w0[is_inhibitory][:, :] * support[is_inhibitory]
        assert inhibitory_block.max() <= 0.0
        assert inhibitory_block.min() < 0.0
        # 其余行：支撑元全 >= 0 且至少一个 > 0
        excitatory_block = w0[~is_inhibitory] * support[~is_inhibitory]
        assert excitatory_block.min() >= 0.0
        assert excitatory_block.max() > 0.0

        # 落盘的 sign 矩阵必须与 w0 一致（不能只是「看起来像」）
        assert np.array_equal(np.asarray(rep["sign"], dtype=int), np.sign(rep["w0"]))


def test_theta_reconstructs_w0_through_softplus(payload):
    """``W = A ⊙ (sign(W^0) ⊙ softplus(Theta))``（`DanioNet` §3）必须能由落盘的 Theta 复原。

    注意支撑外 ``Theta`` **恒为 0** 而不是 ``|W^0|`` 的反函数（``softplus(0) = log 2 != 0``）——
    掩码靠 ``support`` 因子生效，不靠梯度。所以复原式必须显式乘上支撑。
    """
    for rep in payload["representatives"]:
        support = np.asarray(rep["support"], dtype=bool)
        w0 = np.asarray(rep["w0"], dtype=float)
        theta = np.asarray(rep["theta"], dtype=float)
        reconstructed = np.where(support, np.sign(w0) * np.log1p(np.exp(theta)), 0.0)
        np.testing.assert_allclose(reconstructed, w0, rtol=1e-5, atol=1e-6)
        # 支撑外 Theta 严格为 0（含补零区与「活跃但无连接」的槽位）
        assert np.count_nonzero(theta[~support]) == 0


# ---------------------------------------------------------------------------
# 5. 只重发育代表个体是安全的
# ---------------------------------------------------------------------------


def test_representative_matches_full_batch_development(dump, payload):
    """代表个体的活跃块必须等于「整种群批量发育」的同一个个体的产物。

    本脚本为了省时只重发育被选中的个体（不跑满 14 个）。这条断言钉住那个假设：
    ``develop`` 的随机流按 ``(master_seed, index)`` 派生，与「之前发育过谁」无关。
    """
    chain = load_model_chain_config(CONFIG_PATH)
    population = initial_population(
        master_seed=PROBE_SEED, experiment_id="connectome-matrix", n=SAMPLE_N, layout=chain.layout
    )
    motifs = motif_catalog(PROBE_SEED, chain.layout)
    phenotypes = phenotypes_of(population, motifs, master_seed=PROBE_SEED, config=chain.rgcd)

    for rep in payload["representatives"]:
        assert rep["master_seed"] == PROBE_SEED
        n = rep["n_neurons"]
        full = phenotypes[rep["index"]]
        assert int(full.adjacency.shape[0]) == n
        np.testing.assert_allclose(
            np.asarray(rep["w0"])[:n, :n], full.weights0.numpy(), rtol=0, atol=0
        )
        assert np.array_equal(
            np.asarray(rep["support"], dtype=bool)[:n, :n],
            full.adjacency.numpy().astype(bool),
        )


# ---------------------------------------------------------------------------
# 6. 长表与 CLI
# ---------------------------------------------------------------------------


def test_long_table_has_2304_flat_rows_per_representative(dump, payload):
    """长表：每代表个体 48x48 = 2304 行、9 列；padding 行用标签显式标出。"""
    records = dump.long_records(payload)
    per_rep = payload["max_nodes"] ** 2
    assert len(records) == per_rep * len(payload["representatives"])
    assert tuple(records[0]) == dump.LONG_COLUMNS

    padding = [r for r in records if r["pre_cell_type"] == dump.PADDING_LABEL]
    assert padding, "补零行必须被显式标成 padding（其 cell_type 数值上与 sensory 撞号）"
    for row in padding:
        assert row["w0"] == 0.0 and row["support_bool"] == 0 and row["sign"] == 0


def test_csv_round_trip(dump, payload, tmp_path):
    path = dump.write_csv(payload, tmp_path / "m.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == payload["max_nodes"] ** 2 * len(payload["representatives"])

    rep = payload["representatives"][0]
    for row in rows[:1]:
        assert int(row["master_seed"]) == rep["master_seed"]
        assert int(row["individual_index"]) == rep["index"]
        assert float(row["w0"]) == rep["w0"][0][0]
        assert int(row["support_bool"]) == rep["support"][0][0]


def test_cli_writes_both_artifacts_with_same_digest(tmp_path, payload):
    """入口可跑、两个文件都落盘，且**跨进程**得到同一 digest。"""
    json_path = tmp_path / "m.json"
    csv_path = tmp_path / "m.csv"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seeds",
            str(PROBE_SEED),
            "--n-individuals",
            str(SAMPLE_N),
            "--json",
            str(json_path),
            "--csv",
            str(csv_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json_path.is_file() and csv_path.is_file()
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["digest"] == payload["digest"]
    assert written["representatives"] == payload["representatives"]


def test_script_entry_point_uses_utf8_guard():
    """脚本入口必须调 `force_utf8_stdout()`（`experiment/console.py` 的约定）。"""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "force_utf8_stdout()" in source
    assert "force_utf8_stdout" in source.split("def main")[1]
