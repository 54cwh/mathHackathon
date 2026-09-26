"""F12 数据流总览图（`scripts/make_fig_pipeline.py`）的守护测试。

守住四件事：

1. **可追溯到 `core §2`**：图的节点/边必须覆盖 `核心机制与数据流.md` §2 的管线骨架
   （`genome` / `development` / `connectome` / `arena` / `fitness` / `selection` …），
   且每个节点都写明出处小节 —— 这张图的立身之本就是「不是随手画的架构图」。
2. **遗传边界显式可见**：必须存在一条 `kind == "blocked"` 的 `Delta W -> 下一代 genome`
   边，且其说明写明「不遗传」。这是论文核心卖点（`core §4.4`），不能被画丢。
3. **图的文字一律英文**：matplotlib 默认字体不含 CJK，中文会渲染成方框
   （`make_figs.py` docstring）。中文只允许出现在配套 `.xlsx` 的说明列里。
4. **配套 Excel 合规**：与图**同名**、落在同级 `data/`、首 sheet 为 `_manifest`，
   且节点表 / 边表可回读。
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from evogenesis.viz import fig_pipeline
from evogenesis.viz.figdata import MANIFEST_SHEET, workbook_path

#: 图上**不得**出现的字符区间（CJK 统一表意文字 + 全角标点）。
_CJK = re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]")


@pytest.fixture(scope="module")
def figmod():
    return fig_pipeline


# ---------------------------------------------------------------------------
# 1. 可追溯到 core §2
# ---------------------------------------------------------------------------


def test_key_nodes_are_all_present(figmod):
    """`core §2` 的管线骨架节点一个都不能少（图号 F12 的内容契约）。"""
    ids = {nid for nid, *_ in figmod.PIPELINE_NODES}
    missing = set(figmod.KEY_NODES) - ids
    assert not missing, f"figure F12 缺关键节点：{sorted(missing)}"
    # 任务书点名要求出现的六个 + 两个去向
    for required in (
        "genome",
        "development",
        "connectome",
        "arena",
        "fitness",
        "selection",
        "results_runs",
        "artifacts",
    ):
        assert required in ids, f"缺节点 {required}"


def test_spine_order_matches_core_section_2(figmod):
    """主轴顺序 = `core §2` 的 `configs -> SeedManager -> genome -> development ->
    connectome -> Arena`，再 `fitness -> selection -> 下一代 genome`。"""
    edges = {(src, dst) for src, dst, _, _ in figmod.PIPELINE_EDGES}
    for pair in (
        ("configs", "seed_manager"),
        ("seed_manager", "genome"),
        ("genome", "development"),
        ("development", "connectome"),
        ("connectome", "arena"),
        ("fitness", "selection"),
        ("selection", "next_genome"),
    ):
        assert pair in edges, f"主轴缺边 {pair[0]} -> {pair[1]}"


def test_next_generation_genome_loops_back(figmod):
    """闭环：下一代 genome 回到 genome（`core §2` 的「回到 genome」）。"""
    assert ("next_genome", "genome") in {(src, dst) for src, dst, _, _ in figmod.PIPELINE_EDGES}


def test_three_parallel_branches_fan_out_from_arena(figmod):
    """三条同源分支都从 Arena 分出（`core §2`：专家轨迹 / 事件日志 / 帧快照）。"""
    assert len(figmod.BRANCH_HEADS) == 3
    edges = {(src, dst) for src, dst, _, _ in figmod.PIPELINE_EDGES}
    for head in figmod.BRANCH_HEADS:
        assert ("arena", head) in edges, f"分支 {head} 未从 arena 分出"


def test_every_node_states_its_source_section(figmod):
    """每个节点都要写出处小节 —— 没有出处的节点就是「编的」。"""
    for nid, label, kind, note, source in figmod.PIPELINE_NODES:
        assert source.strip(), f"节点 {nid} 缺出处"
        assert "§" in source, f"节点 {nid} 的出处未给小节号：{source!r}"
        assert nid in source or "§" in source  # 出处必须是「文档 §小节」形态
        assert label.strip() and kind.strip() and note.strip(), f"节点 {nid} 有空字段"


def test_figure_sources_include_core_section_2(figmod):
    """图的权威出处必须点明 core §2 的小节号（任务书要求进 `_manifest`）。"""
    assert figmod.CORE_SECTION == "core §2"
    assert "核心机制与数据流.md" in figmod.AUTHORITATIVE_SOURCE
    assert "§2" in figmod.AUTHORITATIVE_SOURCE


# ---------------------------------------------------------------------------
# 2. 遗传边界（论文核心卖点，不能画丢）
# ---------------------------------------------------------------------------


def test_genetic_boundary_edge_is_blocked_and_says_not_inherited(figmod):
    """必须有一条「不遗传」的 ΔW 边界边，且 `kind == "blocked"`。"""
    blocked = [e for e in figmod.PIPELINE_EDGES if e[2] == "blocked"]
    assert blocked, "缺 kind=blocked 的遗传边界边"
    assert len(blocked) == 1, f"遗传边界应恰好一条，实得 {len(blocked)}"
    src, dst, _kind, note = blocked[0]
    assert (src, dst) == ("delta_w", "next_genome")
    assert "不遗传" in note, f"边界边说明未写明「不遗传」：{note!r}"
    assert "NOT inherited" in note, "边界边说明未给出图上的英文标注 NOT inherited"


def test_delta_w_is_produced_by_bc_and_source_is_core_4_4(figmod):
    """ΔW 的产者与出处：`bc_training -> delta_w`，出处 core §4.4（遗传边界）。"""
    edges = {(src, dst) for src, dst, _, _ in figmod.PIPELINE_EDGES}
    assert ("bc_training", "delta_w") in edges
    label, note, source = {
        nid: (label, note, source) for nid, label, _k, note, source in figmod.PIPELINE_NODES
    }["delta_w"]
    assert "§4.4" in source
    assert "NOT inherited" in label, "ΔW 的图上标签必须显式标出 NOT inherited"
    assert "不遗传" in note


def test_no_inheritance_edge_from_delta_w_into_the_spine(figmod):
    """除图示用的 blocked 边外，ΔW **不得**有进入遗传通路的实边。"""
    real = [
        (src, dst, kind)
        for src, dst, kind, _ in figmod.PIPELINE_EDGES
        if src == "delta_w" and kind != "blocked"
    ]
    assert not real, f"ΔW 出现了进入繁殖通路的实边（破坏遗传边界）：{real}"
    # 反过来：下一代 genome 的入边只允许来自 selection（和图示的 blocked 边）
    incoming = sorted(
        (src, kind) for src, dst, kind, _ in figmod.PIPELINE_EDGES if dst == "next_genome"
    )
    assert incoming == [("delta_w", "blocked"), ("selection", "flow")]


# ---------------------------------------------------------------------------
# 3. 图的文字一律英文
# ---------------------------------------------------------------------------


def test_all_figure_labels_are_free_of_cjk(figmod):
    """图上的文字（`label`）不得含 CJK —— 否则渲染成方框。"""
    for nid, label, *_ in figmod.PIPELINE_NODES:
        assert not _CJK.search(label), f"节点 {nid} 的图上标签含 CJK：{label!r}"


def test_notes_are_chinese_so_the_excel_stays_informative(figmod):
    """中文只允许出现在 `.xlsx` 的说明列里 —— 说明列必须真的有中文。

    `source` 是「文档 §小节」指针，允许纯英文（如 ``core §2``），故不在此断言。
    """
    for nid, _label, _kind, note, _source in figmod.PIPELINE_NODES:
        assert _CJK.search(note), f"节点 {nid} 的 note 没有中文说明（Excel 会失去信息量）"
    for src, dst, _kind, note in figmod.PIPELINE_EDGES:
        assert _CJK.search(note), f"边 {src}->{dst} 的 note 没有中文说明"


# ---------------------------------------------------------------------------
# 4. 图与配套 Excel
# ---------------------------------------------------------------------------


def test_edges_reference_declared_nodes_only(figmod):
    """引用完整性：边的两端必须都是已声明的节点（防拼错 id）。"""
    ids = {nid for nid, *_ in figmod.PIPELINE_NODES}
    for src, dst, _kind, _note in figmod.PIPELINE_EDGES:
        assert src in ids, f"边起点 {src!r} 未在节点表中声明"
        assert dst in ids, f"边终点 {dst!r} 未在节点表中声明"
        assert src != dst, f"出现自环 {src}"


def test_frames_have_expected_columns(figmod):
    nodes = figmod.nodes_frame()
    edges = figmod.edges_frame()
    assert list(nodes.columns) == ["id", "label", "kind", "note", "source"]
    assert list(edges.columns) == ["from", "to", "kind", "note"]
    assert len(nodes) == len(figmod.PIPELINE_NODES)
    assert len(edges) == len(figmod.PIPELINE_EDGES)
    assert nodes["id"].is_unique, "节点 id 必须唯一"


def test_build_figure_writes_png_and_same_stem_workbook(figmod, tmp_path, monkeypatch):
    """一个调用 = 一张图 + 一份**同名不同后缀**的数据表，Excel 落在图同级 `data/`。"""
    monkeypatch.setattr(figmod, "OUT", tmp_path)
    fig_path, workbook, _sheets, _prov = figmod.build_figure("unit test note")
    assert fig_path == tmp_path / "fig_pipeline.png"
    assert fig_path.is_file() and fig_path.stat().st_size > 10_000
    assert workbook_path(fig_path) == workbook == tmp_path / "data" / "fig_pipeline.xlsx"
    assert workbook.is_file()
    assert workbook.stem == fig_path.stem


def test_workbook_has_manifest_first_with_nodes_and_edges(figmod, tmp_path, monkeypatch):
    """首 sheet 必须是 `_manifest`；节点表 / 边表可回读且与内存逐值一致。"""
    monkeypatch.setattr(figmod, "OUT", tmp_path)
    _fig, workbook, sheets, provenance = figmod.build_figure("unit test note")
    xl = pd.ExcelFile(workbook)
    assert xl.sheet_names[0] == MANIFEST_SHEET, "manifest 必须是第一个 sheet"
    assert list(xl.sheet_names[1:]) == ["nodes", "edges"]

    manifest = xl.parse(MANIFEST_SHEET)
    for column in ("sheet", "figure", "caption", "shape", "columns", "source"):
        assert column in manifest.columns
    assert {"nodes", "edges"} <= set(manifest["sheet"])
    data_rows = manifest[manifest["sheet"].isin(sheets)]
    assert data_rows["shape"].fillna("").str.contains("rows x").all()
    assert data_rows["source"].fillna("").ne("").all()

    # 不看代码也能找到权威出处：core §2 的小节号必须在 manifest 里
    texts = (
        " ".join(manifest["caption"].fillna("").astype(str))
        + " "
        + " ".join(manifest["source"].fillna("").astype(str))
    )
    assert figmod.CORE_SECTION in texts
    assert provenance["core_section"] == figmod.CORE_SECTION

    for name in ("nodes", "edges"):
        back = xl.parse(name)
        pd.testing.assert_frame_equal(
            back, sheets[name], check_dtype=False, check_column_type=False
        )
    # 边表的遗传边界行必须原样落盘（不因 Excel 往返而改名）
    edges_back = xl.parse("edges")
    blocked = edges_back[edges_back["kind"] == "blocked"]
    assert len(blocked) == 1
    assert (blocked.iloc[0]["from"], blocked.iloc[0]["to"]) == ("delta_w", "next_genome")


def test_module_entry_point_uses_utf8_guard():
    """出图模块入口必须调 `force_utf8_stdout()`（`experiment/console.py` 的约定）。"""
    source = Path(fig_pipeline.__file__).read_text(encoding="utf-8")
    assert "force_utf8_stdout()" in source
    assert "force_utf8_stdout" in source.split("def main")[1]
