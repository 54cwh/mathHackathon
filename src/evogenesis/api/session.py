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
from pathlib import Path

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import (
    FishCard,
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
from evogenesis.pipeline import arena_seeds_for

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
        # model_config_path 为占位契约（`API接口.md` §7.2）：Demo 用 ExpertPolicy 驱动，
        # 不加载 DanioNet，故该字段被接收但不参与本层行为。
        self.model_config_path = create.model_config_path
        self.generation = 0
        self.running = True
        cfg = load_arena_config(_resolve(create.arena_config_path))
        spawn_seed, dynamics_seed = arena_seeds_for(create.master_seed, _SESSION_ARENA_INDEX)
        self.arena = DanioArena(cfg, spawn_seed=spawn_seed, dynamics_seed=dynamics_seed)
        self.expert = expert_policy_from_config(self.arena.cfg)
        # 同步 `def` 路由由 FastAPI 丢进线程池并发执行，单 worker ≠ 单线程；同一会话的
        # 并发调用须串行化（见 `API接口.md` §7.1）。
        self._lock = threading.Lock()
        self.reset_arena()

    def reset_arena(self) -> None:
        with self._lock:
            self.arena.reset()
            self.generation = 0
            self.running = True

    def advance(self, steps: int = 1, use_expert: bool = True) -> None:
        """推进仿真 `steps` 步（`B1` 定稿）；`running=False` 时整段短路。"""
        with self._lock:
            if not self.running:
                return
            for _ in range(steps):
                if self.arena.step_idx >= self.arena.cfg.world.episode_steps:
                    break
                actions: dict[str, tuple[float, float]] = {}
                if use_expert:
                    for fid, fish in self.arena.fish.items():
                        if fish.alive:
                            actions[fid] = self.expert(self.arena.observe(fid))
                result = self.arena.step(actions)
                if result.done:
                    break

    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot()

    def _snapshot(self) -> Snapshot:
        fish_out = {
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
    s.advance(steps=steps, use_expert=use_expert)
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
