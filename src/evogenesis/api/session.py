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
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException

from evogenesis.api import environmental_selections as selections
from evogenesis.api import genome_lab as lab
from evogenesis.api import ws as ws_hub
from evogenesis.api.genome_lab import stable_index
from evogenesis.api.schemas import (
    FishCard,
    IndividualSpawn,
    JobStatus,
    Leaderboard,
    LeaderboardEntry,
    Problem,
    SessionCreate,
    SessionSummary,
    Snapshot,
    SpawnedIndividual,
)
from evogenesis.arena.config import load_arena_config
from evogenesis.arena.env import DanioArena
from evogenesis.arena.policies import expert_policy_from_config
from evogenesis.connectome.danionet import DanioNet
from evogenesis.development.rgcd import ConnectomePhenotype
from evogenesis.experiment.config import load_experiment_config
from evogenesis.pipeline import (
    arena_seeds_for,
    danionet_of,
    initial_population,
    load_demo_checkpoint,
    load_model_chain_config,
    motif_catalog,
    phenotype_of,
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
        # 逐鱼登记（`core §3.1`）：默认会话 = 初始基因组种群（下方 `else` 分支填充）；
        # model_driven 会话为空，后续经 `POST /individuals`（§1.11）追加。
        # 每条鱼的网优先于 `self.net`（model_driven 的全局网）。
        self.individuals: dict[str, SpawnedIndividual] = {}
        self.nets: dict[str, DanioNet] = {}
        #: 模型链配置：模型驱动会话在此加载；其余会话**惰性**加载（§1.11 追加个体需要）。
        self._chain = None
        self._model_config_path = create.model_config_path
        if self.model_driven:
            chain = load_model_chain_config(_resolve(create.model_config_path))
            self._chain = chain
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
            # 默认会话（`API接口.md` §1.1，2026-09-27 定稿）：整种群基因组化。
            # 每个 genome 经 `initial_population` 生成 → 发育 → 只保留 viable → 各建自己的
            # DanioNet。发育口径与 Lab 的 DEVELOP / §1.11 追加个体**一致**：
            # `seed=0` + `index=stable_index(genome_id)` + 参考 motif 目录（`lab.motifs`），
            # 故 Arena 里这条鱼的行为 = 点开它在 Lab/Forge 看到的那次发育。
            chain = self.chain
            n = (
                create.population_size
                if create.population_size is not None
                else cfg.population.n_fish
            )
            if n < 1:
                raise ValueError("population_size 必须 ≥ 1")
            population = initial_population(
                master_seed=create.master_seed,
                experiment_id=session_id,
                n=n,
                layout=chain.layout,
            )
            phenotypes = phenotypes_of(population, lab.motifs(chain.layout), master_seed=0)
            keep = [i for i, p in enumerate(phenotypes) if p.viable]
            if not keep:
                raise ValueError("默认会话：该 seed 无 viable 个体（RGCD §7）")
            cfg = replace(cfg, population=replace(cfg.population, n_fish=len(keep)))
            # 鱼 ID 用 `genome_id`（不是 `initial_population` 另铸的 `fish_id`）：保持
            # §1.11 的不变量 `fish_id == genome_id`，否则同一 genome 会被重复追加。
            self.arena = DanioArena(
                cfg,
                spawn_seed=spawn_seed,
                dynamics_seed=dynamics_seed,
                fish_ids=[population[i].genome_id for i in keep],
                genome_ids=[population[i].genome_id for i in keep],
            )
            for i in keep:
                # 登记进 Lab store：`GET /v1/genomes/{id}` 能查到，点 Arena 的鱼即可回看 DNA。
                lab.store(population[i].genome)
                self._register_individual(
                    population[i].genome_id, population[i].genome_id, phenotypes[i], generation=0
                )
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
            # `reset` 按构造时的 `fish_ids` 重建初始基因组种群、丢掉 §1.11 追加的个体，
            # 故这里同步剪掉已不存在的登记（否则重复追加检测会误判 409）。
            keep = set(self.arena.fish)
            self.individuals = {k: v for k, v in self.individuals.items() if k in keep}
            self.nets = {k: v for k, v in self.nets.items() if k in keep}
            self._activation = {k: [] for k in self.nets}
            self.generation = 0
            self.running = True

    @property
    def chain(self):
        """模型链配置（惰性、只加载一次）。"""
        if self._chain is None:
            self._chain = load_model_chain_config(_resolve(self._model_config_path))
        return self._chain

    def _register_individual(
        self,
        fish_id: str,
        genome_id: str,
        phenotype: ConnectomePhenotype,
        *,
        generation: int,
        seed: int = 0,
    ) -> SpawnedIndividual:
        """登记一条**已存在**的鱼（由 Arena 造好）：建它自己的网 + 发育元数据。

        仅供本类内部使用：默认会话的初始种群（`__init__`）与 `spawn_individual` 共用，
        保证两条路径产出的 `SpawnedIndividual` 与网**完全一致**（`core §3.1`）。
        `seed` 即 `danionet_of` 的 `master_seed`（默认 0，与 Lab 的 DEVELOP 同口径）。
        """
        self.nets[fish_id] = danionet_of([phenotype], master_seed=seed, config=self.chain.network)
        counts = Counter(int(v) for v in phenotype.cell_type.tolist())
        individual = SpawnedIndividual(
            fish_id=fish_id,
            genome_id=genome_id,
            generation=generation,
            viable=bool(phenotype.viable),
            n_neurons=int(phenotype.cell_type.numel()),
            n_edges=int((phenotype.adjacency != 0).sum().item()),
            tau_mean=float(phenotype.tau.mean().item()),
            cell_type_counts={str(k): int(v) for k, v in sorted(counts.items())},
        )
        self.individuals[fish_id] = individual
        self._activation.setdefault(fish_id, [])
        return individual

    def spawn_individual(self, genome_id: str, *, seed: int = 0) -> SpawnedIndividual:
        """把实验室个体（genome → 发育 → DanioNet）**追加**进本会话的 Arena（`API接口.md` §1.11）。

        流程（全部复用既有模块，不新造模型）：
        `phenotype_of(genome, motifs, seed, index=stable_index(genome_id))` →
        `danionet_of([phenotype])`
        → `arena.spawn_fish(fish_id=genome_id, genome_id=...)`，并登记进 `self.nets` /
        `self.individuals`（`_register_individual`），于是 `advance` 里这条鱼由**它自己的网**驱动。

        稳定 ID（`core §3.1`）：`fish_id == genome_id`（自描述、可回查发育产物）。
        重复追加同一 genome → `409`；未知 genome → `404`（由路由层抛）。
        """
        if genome_id in self.individuals:
            raise HTTPException(
                status_code=409, detail=f"individual {genome_id!r} already in this session"
            )
        with self._lock:
            genome = lab.get(genome_id)
            if genome is None:
                raise HTTPException(status_code=404, detail=f"genome {genome_id!r} not found")
            phenotype = phenotype_of(
                genome,
                lab.motifs(self.chain.layout),
                master_seed=seed,
                index=stable_index(genome_id),
            )
            if not phenotype.viable:
                raise HTTPException(
                    status_code=422,
                    detail=f"genome {genome_id!r} not viable: {phenotype.viability_reason}",
                )
            fish = self.arena.spawn_fish(genome_id, genome_id=genome_id)
            return self._register_individual(
                fish.entity_id, genome_id, phenotype, generation=fish.generation, seed=seed
            )

    def advance(
        self,
        steps: int = 1,
        use_expert: bool = True,
        control: tuple[str, float, float] | None = None,
    ) -> list:
        """推进仿真 `steps` 步（`B1` 定稿）；`running=False` 时整段短路。返回本次新增事件。

        ``control``：Manual Control（`交互与可视化.md` §10）的**单鱼**动作覆盖
        ``(fish_id, omega, speed)``，每步都施加。动作语义与裁剪见 `arena §461 S1`：
        ``omega ∈ [-1, 1]``（rad/s）、``speed ∈ [0, 1]``（世界单位/秒）；越界在此裁剪，
        与 `DanioArena.step` 的裁剪同口径。被操控鱼优先于 ExpertPolicy / 网络输出，
        其余鱼照旧（`use_expert` 或全零）。
        """
        new_events: list = []
        with self._lock:
            if not self.running:
                return new_events
            for _ in range(steps):
                if self.arena.step_idx >= self.arena.cfg.world.episode_steps:
                    break
                actions: dict[str, tuple[float, float]] = {}
                alive_ids = [fid for fid, f in self.arena.fish.items() if f.alive]
                if self.net is not None:
                    # 全局网（model_driven）：**必须喂全部鱼**——它的内部状态维度固定
                    # （checkpoint / 初始种群），子集化会形状不匹配。死鱼也过一遍以保持维度。
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
                    # ExpertPolicy 只补「没有自己的网」的鱼（`use_expert=false` 时不给任何鱼补）。
                    for fid in alive_ids:
                        if fid not in self.nets:
                            actions[fid] = self.expert(self.arena.observe(fid))

                # 实验室个体（§1.11）：各自用自己的网，**覆盖**上面任何来源的动作
                for fid in alive_ids:
                    net = self.nets.get(fid)
                    if net is None:
                        continue
                    obs = self.arena.observe(fid)[None, :]
                    omega, speed = net.step(obs)
                    actions[fid] = (float(omega.detach()[0]), float(speed.detach()[0]))
                    self._activation[fid] = [float(x) for x in net.h.detach()[0]]

                # Manual Control：单鱼动作覆盖（`交互与可视化.md` §10）
                if control is not None:
                    cid, omega, speed = control
                    fish = self.arena.fish.get(cid)
                    if fish is not None and fish.alive:
                        actions[cid] = (
                            max(-1.0, min(1.0, float(omega))),
                            max(0.0, min(1.0, float(speed))),
                        )

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

    def individuals_list(self) -> list[SpawnedIndividual]:
        """会话内已登记的个体（初始种群 + §1.11 追加），按 Arena 的鱼顺序列出。"""
        with self._lock:
            return [self.individuals[k] for k in self.arena.fish if k in self.individuals]

    def _fish_card(self, fish_id: str) -> FishCard:
        f = self.arena.fish[fish_id]
        # 每条鱼都有真实 genome_id（§1.1 种群基因组化 / §1.11 追加）；登记的个体
        # 额外带上连接组摘要（`metrics` 是开放字典，§1.5）。
        individual = self.individuals.get(fish_id)
        return FishCard(
            fish_id=f.entity_id,
            generation=f.generation,
            genome_id=f.genome_id,
            viable=individual.viable if individual else True,
            energy=float(f.energy),
            size=float(f.size),
            fitness=None,
            cell_counts=dict(individual.cell_type_counts) if individual else {},
            metrics={
                "alive": f.alive,
                "captures": f.captures,
                "encounters": f.encounters,
                "predator_encounters": f.predator_encounters,
                "escape_successes": f.escape_successes,
                "survival_steps": f.survival_steps,
                # 实验室个体额外带上连接组摘要（`metrics` 是开放字典，§1.5）
                **(
                    {
                        "n_neurons": individual.n_neurons,
                        "n_edges": individual.n_edges,
                        "tau_mean": individual.tau_mean,
                    }
                    if individual
                    else {}
                ),
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
def release(
    session_id: str,
    steps: int = 1,
    use_expert: bool = True,
    fish_id: str | None = None,
    omega: float = 0.0,
    speed: float = 0.0,
) -> SessionSummary:
    """推进 `steps` 步；给 `fish_id` 时该鱼改用 (omega, speed) 手动动作（`API接口.md` §1.6）。

    手动动作只对**这一条**鱼生效，其余鱼仍按 `use_expert` 驱动；`fish_id` 不存在或已死时
    该参数被忽略（不报错 —— 前端 10Hz 连发，报错会刷屏）。
    """
    s = _get_session(session_id)
    control = (fish_id, omega, speed) if fish_id else None
    events = s.advance(steps=steps, use_expert=use_expert, control=control)
    # 模型驱动会话（全局网）与默认会话（逐鱼网，`self.nets`）都推 `brain.activation`。
    if s.net is not None or s.nets:
        ws_hub.publish_brain_activation(s.session_id, s.arena.step_idx, s.activation())
    if events:
        ws_hub.publish_fish_state(s.session_id, s.arena.step_idx, s.fish_state())
        ws_hub.publish_events(s.session_id, [e.to_dict() for e in events])
    return _manager.summary(s)


@router.post(
    "/sessions/{session_id}/individuals", status_code=201, response_model=SpawnedIndividual
)
def spawn_individual(session_id: str, body: IndividualSpawn) -> SpawnedIndividual:
    """把发育好的实验室个体追加进会话 Arena（`API接口.md` §1.11）。

    之后该鱼由**它自己的 DanioNet** 驱动；`brain.activation` 也会带上它（`fish[<fish_id>]`）。
    """
    s = _get_session(session_id)
    return s.spawn_individual(body.genome_id, seed=body.seed)


@router.get("/sessions/{session_id}/individuals", response_model=list[SpawnedIndividual])
def list_individuals(session_id: str) -> list[SpawnedIndividual]:
    """列出会话内已登记的个体（初始种群 + §1.11 追加）（`API接口.md` §1.11）。"""
    return _get_session(session_id).individuals_list()


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
