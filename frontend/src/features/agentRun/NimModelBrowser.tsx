/**
 * NimModelBrowser — displays NVIDIA NIM free endpoint models.
 * Fetches from GET /orchestrate/nim-models (falls back to static list).
 */
import { useEffect, useState } from "react";

interface NimModel {
  model_id: string;
  slug: string;
  name: string;
  context_length: number;
  use_cases: string[];
  publisher: string;
  free: boolean;
  build_url: string;
}

interface NimModelsResponse {
  nim_available: boolean;
  base_url: string;
  models: NimModel[];
  role_map: Record<string, string[]>;
}

const USE_CASE_COLORS: Record<string, string> = {
  reasoning: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  coding: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  agentic: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  planning: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  fast: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  chat: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  summarize: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  routing: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  safety: "bg-red-500/20 text-red-300 border-red-500/30",
  rag: "bg-teal-500/20 text-teal-300 border-teal-500/30",
};

function ctxLabel(n: number): string {
  if (n >= 1_000_000) return `${n / 1_000_000}M ctx`;
  if (n >= 1_000) return `${n / 1_000}K ctx`;
  return `${n} ctx`;
}

export function NimModelBrowser() {
  const [data, setData] = useState<NimModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    fetch("/api/orchestrate/nim-models")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const models = data?.models ?? [];
  const filtered = filter
    ? models.filter(
        (m) =>
          m.name.toLowerCase().includes(filter.toLowerCase()) ||
          m.publisher.toLowerCase().includes(filter.toLowerCase()) ||
          m.use_cases.some((u) => u.includes(filter.toLowerCase()))
      )
    : models;

  return (
    <div className="flex flex-col gap-4 h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">NVIDIA NIM Free Models</span>
          {data && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full border font-mono ${
                data.nim_available
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                  : "bg-zinc-700/50 text-zinc-400 border-zinc-600/30"
              }`}
            >
              {data.nim_available ? "API key set" : "No API key"}
            </span>
          )}
        </div>
        <a
          href="https://build.nvidia.com/models"
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-2"
        >
          build.nvidia.com →
        </a>
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Filter by name, publisher, or use case…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500 flex-shrink-0"
      />

      {/* Grid */}
      <div className="flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="text-sm text-zinc-500 py-8 text-center">Loading models…</div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-zinc-500 py-8 text-center">No models match.</div>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {filtered.map((m) => (
              <NimModelCard key={m.model_id} model={m} roleMap={data?.role_map ?? {}} />
            ))}
          </div>
        )}
      </div>

      {/* Footer hint */}
      {!data?.nim_available && (
        <p className="text-xs text-zinc-500 flex-shrink-0">
          Set <code className="text-zinc-300">NVIDIA_NIM_API_KEY</code> in your{" "}
          <code className="text-zinc-300">.env</code> to enable NIM routing.
        </p>
      )}
    </div>
  );
}

function NimModelCard({
  model,
  roleMap,
}: {
  model: NimModel;
  roleMap: Record<string, string[]>;
}) {
  // Which roles use this model?
  const usedByRoles = Object.entries(roleMap)
    .filter(([, models]) => models.includes(model.model_id))
    .map(([role]) => role);

  return (
    <div className="bg-zinc-800/60 border border-zinc-700/60 rounded-lg p-3 hover:border-zinc-600 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-zinc-100">{model.name}</span>
            <span className="text-xs text-zinc-500 font-mono">{ctxLabel(model.context_length)}</span>
          </div>
          <span className="text-xs text-zinc-500">{model.publisher}</span>
        </div>
        <a
          href={model.build_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300 shrink-0 mt-0.5"
          title="Open on build.nvidia.com"
        >
          ↗
        </a>
      </div>

      {/* Use case badges */}
      <div className="flex flex-wrap gap-1 mb-2">
        {model.use_cases.map((uc) => (
          <span
            key={uc}
            className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${
              USE_CASE_COLORS[uc] ?? "bg-zinc-700/50 text-zinc-400 border-zinc-600/30"
            }`}
          >
            {uc}
          </span>
        ))}
      </div>

      {/* Used-by-role tags */}
      {usedByRoles.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {usedByRoles.map((role) => (
            <span
              key={role}
              className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700/50 text-zinc-400 border border-zinc-600/30"
            >
              {role}
            </span>
          ))}
        </div>
      )}

      {/* Model ID (collapsed) */}
      <p className="text-[10px] font-mono text-zinc-600 mt-1.5 truncate">{model.model_id}</p>
    </div>
  );
}
