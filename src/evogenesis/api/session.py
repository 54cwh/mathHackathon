"""内存会话 + DanioArena 接线（`API接口.md` §1；端点 owner = `api/`）。

本模块是 Arena 侧端点（§1.1–§1.10）的**实现 owner**：会话在内存中持有
`DanioArena`，`release` 推进仿真、`snapshot` 返回全场快照。子种子经
`pipeline::arena_seeds_for(master_seed, 0)` 派生（`core §3` 例外条款：Arena 只接受
整数种子，不得把 `master_seed` 根部直接交给 Arena）。

模型/实验侧端点（§2）为 501 stub（`stubs.py`），待相应管线接入后实现。
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import replace
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException

from evogenesis.api import environmental_selections as selections
from evogenesis.api import ws as ws_hub
from evogenesis.api.schemas import (
    FishCard,
    JobStatus,
    Leaderboard,
    LeaderboardEntry,
    Problem,
    SessionCreate,
    SessionSummary,
    Snapshot,
)
from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import expert_policy_from_config
from evogenesis.experiment.config import load_experiment_config
from evogenesis.pipeline import (
    arena_seeds_for,
    danionet_of,
    initial_population,
    load_demo_checkpoint,
    load_model_chain_config,
    motif_catalog,
    phenotypes_of,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: `snapshot.events` 返回的最近事件条数（`API接口.md` §7.4）。
_EVENTS_TAIL = 200

#: 会话所用 Arena 子种子索引（`core §3` 实体序号 t；单会话取 0，`reset` 亦复现同一随机流）。
_SESSION_ARENA_INDEX = 0


def _resolve(path: str) -> Path:
    """仓库根相对路径解析（`configs/*.yaml`）。"""
    p = Path(path)
    return p if p.is_absolute() else _REPO_ROOT / p


class Session:
    """一个绑定 `master_seed` 的内存会话（`API接口.md` §7.1：无持久化）。"""

    def __init__(self, session_id: str, create: SessionCreate) -> None:
        self.session_id = session_id
        self.environment = create.environment
        self.master_seed = create.master_seed
        self.arena_config_path = create.arena_config_path
        self.model_config_path = create.model_config_path
        self.generation = 0
        self.running = True
        cfg = load_arena_config(_resolve(create.arena_config_path))
        spawn_seed, dynamics_seed = arena_seeds_for(create.master_seed, _SESSION_ARENA_INDEX)
        # 模型驱动会话（`API接口.md` §7.2，已定稿）：由 DanioNet 驱动并推送 `brain.activation`。
        self.model_driven = bool(create.model_driven)
        self.net = None
        self._activation: dict[str, list[float]] = {}
        if self.model_driven:
            chain = load_model_chain_config(_resolve(create.model_config_path))
            if create.checkpoint_path:
                # 冻结 checkpoint 路径（`pipeline §6`）：直接加载，免重建/免训练。
                ckpt = load_demo_checkpoint(_resolve(create.checkpoint_path))
                self.net = ckpt.build_net(config=chain.network)
                keep_fish = [ind.fish_id for ind in ckpt.individuals]
                keep_genomes = [ind.genome_id for ind in ckpt.individuals]
            else:
                motifs = motif_catalog(create.master_seed, chain.layout)
                individuals = initial_population(
                    master_seed=create.master_seed,
                    experiment_id=session_id,
                    n=cfg.population.n_fish,
                    layout=chain.layout,
                )
                phenotypes = phenotypes_of(individuals, motifs, master_seed=create.master_seed)
                keep = [i for i, p in enumerate(phenotypes) if p.viable]
                if not keep:
                    raise ValueError("模型驱动会话：该 seed 无 viable 个体（RGCD §7）")
                self.net = danionet_of(
                    [phenotypes[i] for i in keep], master_seed=create.master_seed
                )
                keep_fish = [individuals[i].fish_id for i in keep]
                keep_genomes = [individuals[i].genome_id for i in keep]
            cfg = replace(cfg, population=replace(cfg.population, n_fish=len(keep_fish)))
            self.arena = DanioArena(
                cfg,
                spawn_seed=spawn_seed,
                dynamics_seed=dynamics_seed,
                fish_ids=keep_fish,
                genome_ids=keep_genomes,
            )
        else:
            self.arena = DanioArena(cfg, spawn_seed=spawn_seed, dynamics_seed=dynamics_seed)
        self.expert = expert_policy_from_config(self.arena.cfg)
        # 同步 `def` 路由由 FastAPI 丢进线程池并发执行，单 worker ≠ 单线程；同一会话的
        # 并发调用须串行化（见 `API接口.md` §7.1）。
        self._lock = threading.Lock()
        self.reset_arena()

    def reset_arena(self) -> None:
        with self._lock:
            self.arena.reset()
            if self.net is not None:
                self.net.reset()
            self._activation = {}
            self.generation = 0
            self.running = True

    def advance(self, steps: int = 1, use_expert: bool = True) -> list:
        """推进仿真 `steps` 步（`B1` 定稿）；`running=False` 时整段短路。返回本次新增事件。"""
        new_events: list = []
        with self._lock:
            if not self.running:
                return new_events
            for _ in range(steps):
                if self.arena.step_idx >= self.arena.cfg.world.episode_steps:
                    break
                actions: dict[str, tuple[float, float]] = {}
                if self.net is not None:
                    fish_ids = list(self.arena.fish)
                    obs = np.stack([self.arena.observe(fid) for fid in fish_ids])
                    omega, speed = self.net.step(obs)
                    omega = omega.detach()
                    speed = speed.detach()
                    activation = self.net.h.detach()
                    for index, fid in enumerate(fish_ids):
                        if self.arena.fish[fid].alive:
                            actions[fid] = (float(omega[index]), float(speed[index]))
                            self._activation[fid] = [float(x) for x in activation[index]]
                elif use_expert:
                    for fid, fish in self.arena.fish.items():
                        if fish.alive:
                            actions[fid] = self.expert(self.arena.observe(fid))
                result = self.arena.step(actions)
                new_events.extend(result.events)
                if result.done:
                    break
        return new_events

    def activation(self) -> dict[str, list[float]]:
        """最近一步的逐鱼激活（模型驱动会话；`brain.activation` 推送用）。"""
        with self._lock:
            return dict(self._activation)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot()

    def _snapshot(self) -> Snapshot:
        fish_out = self._fish_out()
        prey_out = {
            pid: {
                "x": float(p.pos[0]),
                "y": float(p.pos[1]),
                "size": float(p.size),
                "alive": p.alive,
            }
            for pid, p in self.arena.prey.items()
        }
        pred_out = {
            did: {"x": float(d.pos[0]), "y": float(d.pos[1]), "size": float(d.size)}
            for did, d in self.arena.predators.items()
        }
        obst_out = [
            {"x": float(o.pos[0]), "y": float(o.pos[1]), "radius": float(o.radius)}
            for o in self.arena.obstacles
        ]
        return Snapshot(
            session_id=self.session_id,
            step=self.arena.step_idx,
            fish=fish_out,
            prey=prey_out,
            predators=pred_out,
            obstacles=obst_out,
            events=[e.to_dict() for e in self.arena.events[-_EVENTS_TAIL:]],
        )

    def _fish_out(self) -> dict[str, dict]:
        return {
            fid: {
                "x": float(f.pos[0]),
                "y": float(f.pos[1]),
                "heading": float(f.heading),
                "speed": float(f.speed),
                "energy": float(f.energy),
                "size": float(f.size),
                "alive": f.alive,
            }
            for fid, f in self.arena.fish.items()
        }

    def fish_state(self) -> dict[str, dict]:
        """`arena.fish_state` 推送用的逐鱼变换+能量（`API与系统工程.md` §5）。"""
        with self._lock:
            return self._fish_out()

    def fish_card(self, fish_id: str) -> FishCard:
        with self._lock:
            return self._fish_card(fish_id)

    def _fish_card(self, fish_id: str) -> FishCard:
        f = self.arena.fish[fish_id]
        return FishCard(
            fish_id=f.entity_id,
            generation=f.generation,
            genome_id=f.genome_id,
            viable=True,  # developmental viability; arena survival is in metrics
            energy=float(f.energy),
            size=float(f.size),
            fitness=None,
            cell_counts={},
            metrics={
                "alive": f.alive,
                "captures": f.captures,
                "encounters": f.encounters,
                "predator_encounters": f.predator_encounters,
                "escape_successes": f.escape_successes,
                "survival_steps": f.survival_steps,
            },
        )

    def leaderboard(self) -> Leaderboard:
        with self._lock:
            return self._leaderboard()

    def _leaderboard(self) -> Leaderboard:
        entries = [
            LeaderboardEntry(
                rank=rank,
                fish_id=fid,
                captures=f.captures,
                survival_steps=f.survival_steps,
                energy=float(f.energy),
                fitness=None,
            )
            for rank, (fid, f) in enumerate(
                sorted(
                    self.arena.fish.items(),
                    key=lambda kv: (kv[1].captures, kv[1].survival_steps),
                    reverse=True,
                ),
                start=1,
            )
        ]
        return Leaderboard(session_id=self.session_id, generation=self.generation, entries=entries)


class SessionManager:
    """内存会话表（MVP；无持久化 / TTL / 淘汰；`API接口.md` §7.1）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, create: SessionCreate) -> Session:
        sid = f"session_{uuid.uuid4().hex[:12]}"
        s = Session(sid, create)
        self._sessions[sid] = s
        return s

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def summary(self, s: Session) -> SessionSummary:
        with s._lock:
            return SessionSummary(
                session_id=s.session_id,
                generation=s.generation,
                environment=s.environment,
                population=len(s.arena.fish),
                running=s.running,
                master_seed=s.master_seed,
                fish_alive=sum(1 for f in s.arena.fish.values() if f.alive),
                prey_remaining=sum(1 for p in s.arena.prey.values() if p.alive),
            )


router = APIRouter(
    prefix="/v1",
    responses={404: {"model": Problem, "description": "会话 / 鱼不存在"}},
)
_manager = SessionManager()


def _get_session(session_id: str) -> Session:
    s = _manager.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return s


@router.post("/sessions", status_code=201, response_model=SessionSummary)
def create_session(create: SessionCreate) -> SessionSummary:
    return _manager.summary(_manager.create(create))


@router.get("/sessions/{session_id}", response_model=SessionSummary)
def get_session(session_id: str) -> SessionSummary:
    return _manager.summary(_get_session(session_id))


@router.post("/sessions/{session_id}/reset", response_model=SessionSummary)
def reset_session(session_id: str) -> SessionSummary:
    s = _get_session(session_id)
    s.reset_arena()
    return _manager.summary(s)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    if not _manager.delete(session_id):
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


@router.post("/sessions/{session_id}/release", response_model=SessionSummary)
def release(session_id: str, steps: int = 1, use_expert: bool = True) -> SessionSummary:
    s = _get_session(session_id)
    events = s.advance(steps=steps, use_expert=use_expert)
    if s.net is not None:
        ws_hub.publish_brain_activation(s.session_id, s.arena.step_idx, s.activation())
    if events:
        ws_hub.publish_fish_state(s.session_id, s.arena.step_idx, s.fish_state())
        ws_hub.publish_events(s.session_id, [e.to_dict() for e in events])
    return _manager.summary(s)


@router.post("/sessions/{session_id}/pause", response_model=SessionSummary)
def pause(session_id: str) -> SessionSummary:
    s = _get_session(session_id)
    s.running = not s.running
    return _manager.summary(s)


@router.get("/sessions/{session_id}/snapshot", response_model=Snapshot)
def snapshot(session_id: str) -> Snapshot:
    return _get_session(session_id).snapshot()


@router.get("/sessions/{session_id}/fish/{fish_id}", response_model=FishCard)
def fish_card(session_id: str, fish_id: str) -> FishCard:
    s = _get_session(session_id)
    if fish_id not in s.arena.fish:
        raise HTTPException(status_code=404, detail=f"fish {fish_id} not found")
    return s.fish_card(fish_id)


@router.get("/sessions/{session_id}/leaderboard", response_model=Leaderboard)
def leaderboard(session_id: str) -> Leaderboard:
    return _get_session(session_id).leaderboard()


@router.post("/sessions/{session_id}/evolutions", status_code=202, response_model=JobStatus)
def evolve(session_id: str, generations: int | None = None) -> JobStatus:
    """会话内演化（**过渡实现**：复用环境选择 job，`API接口.md` §2.3）。

    以会话的 `master_seed` + `environment` 启动一个环境选择实验（`generations` 缺省取
    `configs/experiment.yaml::generations`）；`generation` 由该 job 逐代推进。会话本身仍只持
    Arena，不直接持有种群——"真正的会话内演化"待 Evolution 面板定契约。
    """
    session = _get_session(session_id)
    gens = load_experiment_config().generations if generations is None else generations
    _, status = selections.launch(
        name=f"session-evolution:{session_id}",
        seeds=[session.master_seed],
        environment=session.environment,
        generations=gens,
    )
    return status
