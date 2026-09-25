"""In-memory session store + real Danio Arena wiring (contract skeleton).

Ownership: 李辰钊 (Arena/system). Session endpoints are functional for the
arena side; genome/development/breeding/evolution/experiments/jobs are
stubbed (see stubs.py) until 池伟豪's pipeline lands.
"""

import uuid

from fastapi import APIRouter, HTTPException

from evogenesis.api.schemas import (
    FishCard,
    Leaderboard,
    LeaderboardEntry,
    SessionCreate,
    SessionSummary,
    Snapshot,
)
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import ExpertPolicy

ENV_KEYS = ("food_rich", "predator_rich", "resource_scarce")


class Session:
    """One live Arena session bound to a master seed (API与系统工程.md §3 stable IDs)."""

    def __init__(self, session_id: str, create: SessionCreate):
        self.session_id = session_id
        self.environment = create.environment
        self.master_seed = create.master_seed
        self.generation = 0
        self.running = True
        self.arena = DanioArena(master_seed=create.master_seed)
        self.expert = ExpertPolicy()
        self.reset_arena()

    def reset_arena(self) -> None:
        self.arena.reset()
        self.generation = 0
        self.running = True

    # ---- arena interaction -------------------------------------------------
    def advance(self, steps: int = 1, use_expert: bool = True) -> None:
        """Drive the arena forward while the session is running. Default:
        ExpertPolicy steers every fish (imitation data source + live demo
        default). Manual actions land here once frontend control is in (P1)."""
        if not self.running:
            return
        for _ in range(steps):
            if self.arena.step_idx >= self.arena.cfg.world.episode_steps:
                break
            actions = {}
            if use_expert:
                for fid, fish in self.arena.fish.items():
                    if fish.alive:
                        actions[fid] = self.expert(self.arena.observe(fid))
            self.arena.step(actions)

    def snapshot(self) -> Snapshot:
        fish_out = {}
        for fid, f in self.arena.fish.items():
            fish_out[fid] = {
                "x": float(f.pos[0]),
                "y": float(f.pos[1]),
                "heading": float(f.heading),
                "speed": float(f.speed),
                "energy": float(f.energy),
                "size": float(f.size),
                "alive": f.alive,
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
            events=[e.to_dict() for e in self.arena.events[-200:]],
        )

    def fish_card(self, fish_id: str) -> FishCard:
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
        entries = []
        for rank, (fid, f) in enumerate(
            sorted(
                self.arena.fish.items(),
                key=lambda kv: (kv[1].captures, kv[1].survival_steps),
                reverse=True,
            ),
            start=1,
        ):
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    fish_id=fid,
                    captures=f.captures,
                    survival_steps=f.survival_steps,
                    energy=float(f.energy),
                    fitness=None,
                )
            )
        return Leaderboard(
            session_id=self.session_id,
            generation=self.generation,
            entries=entries,
        )


class SessionManager:
    """Holds live sessions in memory (MVP; no persistence)."""

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
        n_alive = sum(1 for f in s.arena.fish.values() if f.alive)
        n_prey = sum(1 for p in s.arena.prey.values() if p.alive)
        return SessionSummary(
            session_id=s.session_id,
            generation=s.generation,
            environment=s.environment,
            population=len(s.arena.fish),
            running=s.running,
            master_seed=s.master_seed,
            fish_alive=n_alive,
            prey_remaining=n_prey,
        )


router = APIRouter(prefix="/v1")
_manager = SessionManager()


def _get_session(session_id: str) -> Session:
    s = _manager.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return s


@router.post("/sessions", status_code=201, response_model=SessionSummary)
def create_session(create: SessionCreate):
    s = _manager.create(create)
    return _manager.summary(s)


@router.get("/sessions/{session_id}", response_model=SessionSummary)
def get_session(session_id: str):
    return _manager.summary(_get_session(session_id))


@router.post("/sessions/{session_id}/reset", response_model=SessionSummary)
def reset_session(session_id: str):
    s = _get_session(session_id)
    s.reset_arena()
    return _manager.summary(s)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    if not _manager.delete(session_id):
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


@router.post("/sessions/{session_id}/release", response_model=SessionSummary)
def release(session_id: str, steps: int = 1, use_expert: bool = True):
    s = _get_session(session_id)
    s.advance(steps=steps, use_expert=use_expert)
    return _manager.summary(s)


@router.post("/sessions/{session_id}/pause", response_model=SessionSummary)
def pause(session_id: str):
    s = _get_session(session_id)
    s.running = not s.running
    return _manager.summary(s)


@router.get("/sessions/{session_id}/snapshot", response_model=Snapshot)
def snapshot(session_id: str):
    return _get_session(session_id).snapshot()


@router.get("/sessions/{session_id}/fish/{fish_id}", response_model=FishCard)
def fish_card(session_id: str, fish_id: str):
    s = _get_session(session_id)
    if fish_id not in s.arena.fish:
        raise HTTPException(status_code=404, detail=f"fish {fish_id} not found")
    return s.fish_card(fish_id)


@router.get("/sessions/{session_id}/leaderboard", response_model=Leaderboard)
def leaderboard(session_id: str):
    return _get_session(session_id).leaderboard()
