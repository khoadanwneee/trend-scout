"use client";

import { useEffect, useMemo, useState } from "react";

type Repo = {
  id: number;
  full_name: string;
  category: string;
  url: string;
  description: string | null;
  language: string | null;
  stars: number;
  stars_period: number | null;
  topics: string | null;
  first_seen: string;
};
type Job = {
  id: number;
  source: string;
  url: string;
  title: string;
  company: string;
  location: string;
  salary: string;
  tags: string;
  posted_text: string;
  is_fresher: number;
  first_seen: string;
};
type Status = {
  source: string;
  status: string;
  message: string;
  items: number;
  last_run: string | null;
};
type Data = {
  generated_at: string;
  categories: string[];
  repos: Repo[];
  jobs: Job[];
  status: Status[];
};

const CATEGORY_LABEL: Record<string, string> = {
  trending: "Trending tuần",
  frontend: "Frontend",
  backend: "Backend",
  "design-ui": "Design / UI",
  ux: "UX",
  data: "Data",
  video: "Video",
  writing: "Viết bài",
  ai: "AI",
};

const STATUS_STYLE: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-800",
  blocked: "bg-red-100 text-red-800",
  unsupported: "bg-amber-100 text-amber-800",
  disabled: "bg-zinc-200 text-zinc-700",
  error: "bg-red-100 text-red-800",
  empty: "bg-amber-100 text-amber-800",
  never_run: "bg-zinc-100 text-zinc-600",
};

const norm = (s: string | null | undefined) => (s ?? "").toLowerCase();
const fmtTime = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" }) : "chưa chạy";

export default function Home() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"repos" | "jobs" | "sources">("repos");

  const [category, setCategory] = useState("");
  const [rq, setRq] = useState("");
  const [language, setLanguage] = useState("");
  const [minStars, setMinStars] = useState(0);
  const [sort, setSort] = useState<"stars" | "period" | "new">("stars");

  const [jq, setJq] = useState("");
  const [location, setLocation] = useState("");
  const [fresherOnly, setFresherOnly] = useState(true);

  useEffect(() => {
    fetch("/data.json", { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(`Không tải được data.json: ${e.message}`));
  }, []);

  const repos = useMemo(() => {
    if (!data) return [];
    const q = norm(rq);
    const out = data.repos.filter(
      (r) =>
        (!category || r.category === category) &&
        (!language || norm(r.language) === norm(language)) &&
        r.stars >= minStars &&
        (!q || norm(r.full_name).includes(q) || norm(r.description).includes(q) || norm(r.topics).includes(q)),
    );
    const key = {
      stars: (r: Repo) => r.stars,
      period: (r: Repo) => r.stars_period ?? 0,
      new: (r: Repo) => Date.parse(r.first_seen),
    }[sort];
    return out.sort((a, b) => key(b) - key(a)).slice(0, 100);
  }, [data, category, rq, language, minStars, sort]);

  const jobs = useMemo(() => {
    if (!data) return [];
    const q = norm(jq);
    const loc = norm(location);
    return data.jobs
      .filter(
        (j) =>
          (!fresherOnly || j.is_fresher) &&
          (!loc || norm(j.location).includes(loc)) &&
          (!q || norm(j.title).includes(q) || norm(j.company).includes(q) || norm(j.tags).includes(q)),
      )
      .slice(0, 200);
  }, [data, jq, location, fresherOnly]);

  const input = "rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-900";

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 text-zinc-900">
      <header className="mb-5">
        <h1 className="text-2xl font-semibold">Trend Scout</h1>
        <p className="text-sm text-zinc-600">
          Repo GitHub đang hot và job IT fresher tại Việt Nam
          {data && <> · cập nhật lần cuối {fmtTime(data.generated_at)}</>}
        </p>
      </header>

      {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {!data && !error && <p className="text-sm text-zinc-500">Đang tải…</p>}

      {data && (
        <>
          <nav className="mb-5 flex gap-1 border-b border-zinc-200">
            {(
              [
                ["repos", "Repo hot"],
                ["jobs", "Job fresher"],
                ["sources", "Nguồn dữ liệu"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => setTab(k)}
                className={`px-4 py-2 text-sm ${
                  tab === k ? "border-b-2 border-zinc-900 font-medium" : "text-zinc-600"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

          {tab === "repos" && (
            <section>
              <div className="mb-4 flex flex-wrap gap-2">
                <select className={input} value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="">Tất cả lĩnh vực</option>
                  {data.categories.map((c) => (
                    <option key={c} value={c}>
                      {CATEGORY_LABEL[c] ?? c}
                    </option>
                  ))}
                </select>
                <input className={input} placeholder="Tìm tên / mô tả / topic" value={rq} onChange={(e) => setRq(e.target.value)} />
                <input className={input} placeholder="Ngôn ngữ (vd. TypeScript)" value={language} onChange={(e) => setLanguage(e.target.value)} />
                <input
                  className={`${input} w-32`}
                  type="number"
                  min={0}
                  placeholder="Sao tối thiểu"
                  value={minStars || ""}
                  onChange={(e) => setMinStars(Number(e.target.value) || 0)}
                />
                <select className={input} value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
                  <option value="stars">Nhiều sao nhất</option>
                  <option value="period">Tăng sao tuần (Trending)</option>
                  <option value="new">Mới thấy gần đây</option>
                </select>
              </div>
              <p className="mb-2 text-xs text-zinc-500">{repos.length} repo</p>
              <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white">
                {repos.map((r) => (
                  <li key={r.id} className="p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <a href={r.url} target="_blank" rel="noreferrer" className="font-medium text-blue-700 hover:underline">
                        {r.full_name}
                      </a>
                      <span className="text-sm text-zinc-600">
                        ★ {r.stars.toLocaleString("vi-VN")}
                        {r.stars_period ? ` (+${r.stars_period.toLocaleString("vi-VN")} tuần)` : ""}
                      </span>
                    </div>
                    {r.description && <p className="mt-1 text-sm text-zinc-700">{r.description}</p>}
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      <span className="rounded bg-zinc-100 px-2 py-0.5">{CATEGORY_LABEL[r.category] ?? r.category}</span>
                      {r.language && <span className="rounded bg-zinc-100 px-2 py-0.5">{r.language}</span>}
                    </div>
                  </li>
                ))}
                {repos.length === 0 && <li className="p-6 text-sm text-zinc-500">Không có repo khớp bộ lọc.</li>}
              </ul>
            </section>
          )}

          {tab === "jobs" && (
            <section>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <input className={input} placeholder="Tìm vị trí / công ty / kỹ năng" value={jq} onChange={(e) => setJq(e.target.value)} />
                <input className={input} placeholder="Địa điểm (vd. Hà Nội)" value={location} onChange={(e) => setLocation(e.target.value)} />
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={fresherOnly} onChange={(e) => setFresherOnly(e.target.checked)} />
                  Chỉ fresher/intern/junior
                </label>
              </div>
              <p className="mb-2 text-xs text-zinc-500">{jobs.length} job</p>
              <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white">
                {jobs.map((j) => (
                  <li key={j.id} className="p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <a href={j.url} target="_blank" rel="noreferrer" className="font-medium text-blue-700 hover:underline">
                        {j.title}
                      </a>
                      <span className="text-xs text-zinc-500">
                        {j.source} · {j.posted_text}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-zinc-700">
                      {[j.company, j.location, j.salary].filter(Boolean).join(" · ")}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                      {j.tags
                        .split(",")
                        .filter(Boolean)
                        .map((t) => (
                          <span key={t} className="rounded bg-zinc-100 px-2 py-0.5">
                            {t}
                          </span>
                        ))}
                    </div>
                  </li>
                ))}
                {jobs.length === 0 && <li className="p-6 text-sm text-zinc-500">Không có job khớp bộ lọc.</li>}
              </ul>
            </section>
          )}

          {tab === "sources" && (
            <section>
              <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 bg-white">
                {data.status.map((s) => (
                  <li key={s.source} className="p-4">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{s.source}</span>
                      <span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLE[s.status] ?? "bg-zinc-100"}`}>
                        {s.status}
                      </span>
                    </div>
                    {s.message && <p className="mt-1 max-w-2xl text-sm text-zinc-600">{s.message}</p>}
                    <p className="mt-1 text-xs text-zinc-500">
                      {s.items} mục · lần chạy cuối: {fmtTime(s.last_run)}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
