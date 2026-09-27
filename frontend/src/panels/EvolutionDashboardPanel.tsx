import { SectionLabel } from "@/components/SectionLabel";
import { useCallback, useEffect, useState } from "react";
import { FlaskConical, RefreshCw, X } from "lucide-react";
import { Panel } from "@/components/Panel";
import {
  cancelJob,
  getJob,
  getSelection,
  launchSelection,
  listSelections,
} from "@/api/selections";
import { useUiStore } from "@/store/ui";
import { subscribe } from "@/api/ws";
import { getRunEvolution, listRuns } from "@/api/runs";
import { EvolutionMetrics } from "@/panels/EvolutionMetrics";
import type { RunEvolution, RunSummary } from "@/api/types";
import type {
  EnvironmentalSelectionDetail,
  EnvironmentalSelectionSummary,
  Environment,
  JobStatus,
  JobStatusKind,
} from "@/api/types";

/**
 * Evolution Dashboard —— Experiment F（环境选择，`api/API接口.md` §2.2）。
 *
 * 一次 launch = `seeds × generations` 代，每 seed 产出一个 `ExperimentRun`
 * （`results/runs/<experiment_id>-s<seed>/`）。请求即时返回 `202` + `job_id`，
 * 后台线程执行；本面板轮询 `GET /v1/jobs/{job_id}`（1s）直到终态。
 *
 * 不编造数据：列表/详情/进度全部来自后端；失败时直接显示后端的 `detail.error`。
 */

const ENVIRONMENTS: Environment[] = ["default", "food_rich", "predator_rich", "resource_scarce"];
const POLL_MS = 1000;
/** seeds 上限：每个 seed 都要跑完整代循环，防止误输入把机器打满。 */
const MAX_SEEDS = 8;

function parseSeeds(text: string): number[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const token of text.split(/[\s,;]+/)) {
    if (!token) continue;
    const value = Number(token);
    if (!Number.isInteger(value)) continue;
    if (seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}

function statusColor(status: JobStatusKind): string {
  if (status === "done") return "text-brand-grass-green";
  if (status === "failed" || status === "cancelled") return "text-brand-danger-red";
  if (status === "running") return "text-brand-amber";
  return "text-muted-foreground";
}

export function EvolutionDashboardPanel() {
  // 表单
  const [name, setName] = useState("env-select");
  const [seedsText, setSeedsText] = useState("1,2,3");
  const [environment, setEnvironment] = useState<Environment>("default");
  const [generations, setGenerations] = useState(10);
  // 运行状态
  const [job, setJob] = useState<JobStatus | null>(null);
  /** job 来源：只有环境选择 job 完成才刷新「详情=最新实验」，会话演化不产 ExperimentRun。 */
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 列表与详情
  const [items, setItems] = useState<EnvironmentalSelectionSummary[]>([]);
  const [detail, setDetail] = useState<EnvironmentalSelectionDetail | null>(null);
  // 会话内演化（§2.3 过渡实现：复用环境选择 job）
  /** Arena 会话 id：仅用于顺带订阅全局 `job.progress`（见下方 WS effect），无会话时靠轮询。 */
  const sessionId = useUiStore((s) => s.sessionId);
  // §8 指标：磁盘 run（重启不丢，含非本进程产生的 run）
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [evolution, setEvolution] = useState<RunEvolution | null>(null);

  const seeds = parseSeeds(seedsText);
  const seedsValid = seeds.length > 0 && seeds.length <= MAX_SEEDS;

  const refreshList = useCallback(async () => {
    try {
      const page = await listSelections(20);
      setItems(page.items);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  const refreshRuns = useCallback(async () => {
    try {
      const page = await listRuns(20);
      setRuns(page.items);
      setRunId((current) => current ?? page.items[0]?.run_id ?? null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void refreshRuns();
  }, [refreshRuns]);

  // 选中 run -> 拉逐代指标（§8）
  useEffect(() => {
    if (!runId) return;
    let stop = false;
    void getRunEvolution(runId)
      .then((data) => !stop && setEvolution(data))
      .catch((e) => !stop && setError(String(e)));
    return () => {
      stop = true;
    };
  }, [runId]);

  // WS 优先：`job.progress` 是**全局**推送（session_id=None，所有订阅者都收），
  // 有活动会话就顺带订阅，实时更新进度；无会话时纯靠下面的轮询兜底。
  useEffect(() => {
    if (!sessionId || !job || job.status === "done" || job.status === "failed" || job.status === "cancelled") {
      return;
    }
    return subscribe(sessionId, {
      jobProgress: (payload) => {
        setJob((current) => {
          if (!current || current.job_id !== payload.job_id) return current;
          return {
            ...current,
            status: payload.status as JobStatusKind,
            progress: payload.progress,
          };
        });
      },
    });
  }, [sessionId, job]);

  // 轮询当前 job 到终态；终态后刷新列表并展开该实验的详情。
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed" || job.status === "cancelled") {
      return;
    }
    let stop = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await getJob(job.job_id);
        if (stop) return;
        setJob(next);
      } catch (e) {
        if (!stop) setError(String(e));
      }
    }, POLL_MS);
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [job]);

  useEffect(() => {
    if (job?.status !== "done") return;
    void refreshList();
    // 详情与 job 一一对应：实验列表首项即本次 launch 的 run（服务端按启动顺序追加）。
    void (async () => {
      try {
        const page = await listSelections(1);
        const first = page.items[0];
        if (first) setDetail(await getSelection(first.experiment_id));
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [job?.status, refreshList]);

  async function handleLaunch() {
    setBusy(true);
    setError(null);
    setDetail(null);
    try {
      setJob(
        await launchSelection({
          name,
          seeds,
          environment,
          generations: Math.max(1, Math.trunc(generations)),
        }),
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    if (!job) return;
    try {
      setJob(await cancelJob(job.job_id));
    } catch (e) {
      setError(String(e));
    }
  }

  const running = job?.status === "running" || job?.status === "queued";

  return (
    <Panel title="Evolution Dashboard" titleZh="演化面板" icon={<FlaskConical className="size-4 text-primary" />}>
      <div className="grid h-full min-h-0 grid-cols-2 divide-x divide-border">
        {/* 左：launch 表单 + 当前 job */}
        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto pr-3">
          <SectionLabel en="ENVIRONMENTAL SELECTION" zh="环境选择实验" />

          <label className="flex flex-col gap-1">
            <SectionLabel en="NAME" zh="名称" />
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
            />
          </label>

          <label className="flex flex-col gap-1">
            <SectionLabel en="SEEDS" zh="种子" />
            <input
              value={seedsText}
              onChange={(e) => setSeedsText(e.target.value)}
              className="border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
            />
            <span className="font-mono text-[10px] text-muted-foreground">
              {seeds.length}/{MAX_SEEDS} 个：{seeds.join(", ") || "—"}
            </span>
          </label>

          <div className="flex items-end gap-2">
            <label className="flex flex-col gap-1">
              <SectionLabel en="ENV" zh="环境" />
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as Environment)}
                className="border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
              >
                {ENVIRONMENTS.map((env) => (
                  <option key={env} value={env}>
                    {env}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <SectionLabel en="GENS" zh="代数" />
              <input
                type="number"
                min={1}
                value={generations}
                onChange={(e) => setGenerations(Number(e.target.value))}
                className="w-20 border border-border bg-transparent px-1 py-0.5 font-mono text-xs"
              />
            </label>
            <button
              type="button"
              onClick={() => void handleLaunch()}
              disabled={busy || running || !seedsValid}
              className="border border-border px-2 py-1 font-pixel text-[10px] leading-none disabled:cursor-not-allowed disabled:text-muted-foreground"
            >
              LAUNCH
            </button>
            {running && (
              <button
                type="button"
                onClick={() => void handleCancel()}
                className="inline-flex items-center gap-1 border border-border px-2 py-1 font-pixel text-[10px] leading-none"
              >
                <X className="size-3" />
                CANCEL
              </button>
            )}
          </div>

          {job && (
            <div className="space-y-1 border border-border p-2">
              <div className="flex items-center justify-between font-mono text-[10px]">
                <span className="truncate">{job.job_id}</span>
                <span className={statusColor(job.status)}>{job.status}</span>
              </div>
              <div className="h-3 w-full border border-border">
                <div
                  className="h-full bg-brand-amber"
                  style={{ width: `${Math.round(Math.max(0, Math.min(1, job.progress)) * 100)}%` }}
                />
              </div>
              <div className="font-mono text-[10px] text-muted-foreground">
                {(job.progress * 100).toFixed(0)}%
                {typeof job.detail?.error === "string" ? ` · ${job.detail.error}` : ""}
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            {error
              ? `⚠ ${error}`
              : "每个种子产出一个 run；后台执行，进度自动更新。"}
          </p>
        </div>

        {/* 右：历史实验列表 + 详情 */}
        <div className="flex min-h-0 flex-col gap-2 overflow-y-auto pl-3">
          <div className="flex items-center justify-between">
            <SectionLabel en="SELECTION JOBS" zh="实验任务" />
            <button
              type="button"
              onClick={() => {
                void refreshList();
                void refreshRuns();
              }}
              className="inline-flex items-center gap-1 border border-border px-2 py-0.5 font-pixel text-[10px] leading-none"
            >
              <RefreshCw className="size-3" />
              REFRESH
            </button>
          </div>

          <ul className="flex flex-col gap-1">
            {items.map((item) => (
              <li key={item.experiment_id}>
                <button
                  type="button"
                  onClick={() =>
                    void getSelection(item.experiment_id).then(setDetail).catch((e) => setError(String(e)))
                  }
                  className={`flex w-full items-center justify-between border border-border px-2 py-1 text-left font-mono text-[10px] ${
                    detail?.experiment_id === item.experiment_id ? "bg-brand-fish-navy text-brand-bone" : ""
                  }`}
                >
                  <span className="truncate">{item.name}</span>
                  <span className="truncate text-muted-foreground">
                    {item.experiment_id} · s{item.seeds.length}
                  </span>
                  <span className={statusColor(item.status)}>{item.status}</span>
                </button>
              </li>
            ))}
            {items.length === 0 && (
              <li className="font-mono text-[10px] text-muted-foreground">
                本进程尚未发起实验（内存表，重启即空）；历史 run 见下方 DISK RUNS。
              </li>
            )}
          </ul>

          {/* §8 指标（磁盘 run；与内存实验表无关，重启后仍在） */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <SectionLabel en="DISK RUNS" zh="历史运行" />
              <span className="font-mono text-[10px] text-muted-foreground">
                {runId ?? "未选择 run"}
              </span>
            </div>
            <ul className="flex max-h-24 flex-col gap-1 overflow-y-auto">
              {runs.map((run) => (
                <li key={run.run_id}>
                  <button
                    type="button"
                    onClick={() => setRunId(run.run_id)}
                    className={`flex w-full items-center justify-between border border-border px-2 py-0.5 text-left font-mono text-[10px] ${
                      runId === run.run_id ? "bg-brand-fish-navy text-brand-bone" : ""
                    }`}
                  >
                    <span className="truncate">{run.run_id}</span>
                    <span className="truncate text-muted-foreground">
                      s{run.seed ?? "—"} · {run.generations ?? 0} 代
                    </span>
                    <span className="truncate text-muted-foreground">{run.status}</span>
                  </button>
                </li>
              ))}
              {runs.length === 0 && (
                <li className="font-mono text-[10px] text-muted-foreground">
                  暂无历史 run
                </li>
              )}
            </ul>
            {evolution ? (
              <EvolutionMetrics evolution={evolution} />
            ) : (
              <div className="border border-border p-2 font-mono text-[10px] text-muted-foreground">
                选择上方任一 run 查看逐代指标。
              </div>
            )}
          </div>

          {detail && (
            <div className="border border-border p-2">
              <div className="mb-1 flex items-center justify-between">
                <SectionLabel en="RUN DETAIL" zh="运行详情" />
                <span className="font-mono text-[10px] text-muted-foreground">
                  {detail.experiment_id}
                </span>
              </div>
              <table className="w-full font-mono text-[10px]">
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="text-left font-normal">seed</th>
                    <th className="text-left font-normal">gens</th>
                    <th className="text-left font-normal">bottleneck</th>
                    <th className="text-left font-normal">run_dir</th>
                  </tr>
                </thead>
                <tbody>
                  {(detail.results?.runs ?? []).map((run) => (
                    <tr key={`${run.seed}`}>
                      <td>{run.seed}</td>
                      <td>{run.generations_run ?? "—"}</td>
                      <td>{run.bottleneck === undefined ? "—" : String(run.bottleneck)}</td>
                      <td className="truncate">{run.run_dir}</td>
                    </tr>
                  ))}
                  {(detail.results?.runs ?? []).length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-muted-foreground">
                        无 run（job 未完成或失败）
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}
