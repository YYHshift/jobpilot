"use client";

import { useState, useEffect } from "react";
import {
  Search,
  MapPin,
  Loader2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Terminal,
  Code2,
  BarChart3,
  PieChart as PieIcon,
  ArrowLeft,
  Briefcase,
  Map,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

interface Job {
  job_title: string;
  company: string;
  location: string;
  work_type: string;
  salary: string;
  level: string;
  requirements: string[];
  source: string;
  url: string;
}

interface StatsData {
  skills: { name: string; value: number }[];
  levels: { name: string; value: number }[];
  locations: { name: string; value: number }[]; // ✅ 新增
  types: { name: string; value: number }[]; // ✅ 新增
  total_jobs: number;
  filter_keyword?: string;
}

const COLORS = [
  "#0891b2",
  "#10b981",
  "#8b5cf6",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#6366f1",
];

export default function Home() {
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("Australia");
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const [hasSearched, setHasSearched] = useState(false);

  // Dashboard State
  const [showDashboard, setShowDashboard] = useState(false);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const url = keyword
        ? `http://127.0.0.1:8000/api/stats?keyword=${encodeURIComponent(keyword)}`
        : "http://127.0.0.1:8000/api/stats";

      const res = await fetch(url);
      const data = await res.json();
      if (data.success) {
        setStats(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingStats(false);
    }
  };

  const toggleDashboard = () => {
    if (!showDashboard) {
      fetchStats();
    }
    setShowDashboard(!showDashboard);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword) return;

    setLoading(true);
    setError("");
    setJobs([]);
    setCurrentPage(1);
    setHasSearched(true);
    setShowDashboard(false);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword, location }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed");

      setJobs(data.data);
    } catch (err) {
      console.error(err);
      setError("System Error: Backend connection failed or timeout.");
    } finally {
      setLoading(false);
    }
  };

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentJobs = jobs.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(jobs.length / itemsPerPage);
  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

  return (
    <main
      className={`min-h-screen bg-slate-950 text-slate-300 font-sans selection:bg-cyan-500/30 selection:text-cyan-200 flex flex-col transition-all duration-700 ease-in-out ${
        hasSearched && !showDashboard
          ? "justify-start pt-10"
          : "justify-center -mt-16"
      }`}
    >
      <div className="absolute top-6 right-6 z-50">
        <button
          onClick={toggleDashboard}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-700 hover:border-cyan-500 rounded-lg transition-all text-sm font-mono hover:text-cyan-400 shadow-lg"
        >
          {showDashboard ? (
            <>
              <ArrowLeft size={16} /> BACK
            </>
          ) : (
            <>
              <BarChart3 size={16} /> ANALYTICS
            </>
          )}
        </button>
      </div>

      <div
        className={`w-full max-w-6xl mx-auto px-6 space-y-8 transition-all duration-700 ${
          hasSearched && !showDashboard
            ? "translate-y-0"
            : showDashboard
              ? "translate-y-0 pt-20"
              : "scale-105"
        }`}
      >
        {/* ==================== DASHBOARD VIEW ==================== */}
        {showDashboard ? (
          <div className="animate-in fade-in slide-in-from-bottom-10 duration-500 space-y-6">
            <div className="text-center space-y-2 mb-8">
              <h2 className="text-3xl font-bold text-slate-100 font-mono tracking-tight">
                Market Intelligence
              </h2>
              <p className="text-slate-500 text-sm font-mono">
                Target:{" "}
                <span className="text-cyan-400">
                  {stats?.filter_keyword || "Global"}
                </span>{" "}
                ({stats?.total_jobs || 0} jobs)
              </p>
            </div>

            {loadingStats ? (
              <div className="h-96 flex items-center justify-center">
                <Loader2 className="animate-spin w-10 h-10 text-cyan-500" />
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-6">
                {/* 1. Skills Chart */}
                <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                  <h3 className="text-sm font-bold text-cyan-400 mb-4 flex items-center gap-2 font-mono">
                    <Code2 size={16} /> TOP SKILLS
                  </h3>
                  <div className="h-[250px] text-xs font-mono">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={stats?.skills}
                        layout="vertical"
                        margin={{ left: 20 }}
                      >
                        <XAxis type="number" hide />
                        <YAxis
                          dataKey="name"
                          type="category"
                          width={80}
                          stroke="#94a3b8"
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            borderColor: "#1e293b",
                            color: "#f1f5f9",
                          }}
                          cursor={{ fill: "#1e293b" }}
                        />
                        <Bar
                          dataKey="value"
                          fill="#0891b2"
                          radius={[0, 4, 4, 0]}
                          barSize={15}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 2. Seniority Chart */}
                <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                  <h3 className="text-sm font-bold text-emerald-400 mb-4 flex items-center gap-2 font-mono">
                    <PieIcon size={16} /> SENIORITY LEVEL
                  </h3>
                  <div className="h-[250px] text-xs font-mono">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={stats?.levels}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {stats?.levels.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index % COLORS.length]}
                              stroke="transparent"
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            borderColor: "#1e293b",
                            color: "#f1f5f9",
                          }}
                        />
                        <Legend iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 3. Location Chart (New) */}
                <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                  <h3 className="text-sm font-bold text-purple-400 mb-4 flex items-center gap-2 font-mono">
                    <Map size={16} /> HOT LOCATIONS
                  </h3>
                  <div className="h-[250px] text-xs font-mono">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats?.locations}>
                        <XAxis dataKey="name" stroke="#94a3b8" />
                        <YAxis hide />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            borderColor: "#1e293b",
                            color: "#f1f5f9",
                          }}
                          cursor={{ fill: "#1e293b" }}
                        />
                        <Bar
                          dataKey="value"
                          fill="#8b5cf6"
                          radius={[4, 4, 0, 0]}
                          barSize={30}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 4. Work Type Chart (New) */}
                <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                  <h3 className="text-sm font-bold text-orange-400 mb-4 flex items-center gap-2 font-mono">
                    <Briefcase size={16} /> WORK TYPE
                  </h3>
                  <div className="h-[250px] text-xs font-mono">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={stats?.types}
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          dataKey="value"
                        >
                          {stats?.types.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index + (3 % COLORS.length)]}
                              stroke="transparent"
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            borderColor: "#1e293b",
                            color: "#f1f5f9",
                          }}
                        />
                        <Legend iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ==================== SEARCH VIEW ==================== */
          <>
            <div className="text-center space-y-4 font-mono">
              <h1
                className={`font-bold text-slate-100 tracking-tighter transition-all duration-700 ${
                  hasSearched
                    ? "text-3xl flex items-center justify-center gap-2"
                    : "text-6xl mb-6"
                }`}
              >
                <span className="text-cyan-500">
                  {hasSearched ? ">" : ">_"}
                </span>
                Job_Pilot
              </h1>
            </div>

            <div
              className={`transition-all duration-700 ${hasSearched ? "max-w-3xl mx-auto" : "max-w-2xl mx-auto w-full"}`}
            >
              <form
                onSubmit={handleSearch}
                className="bg-slate-900 p-1 rounded-xl shadow-2xl border border-slate-800 flex flex-col md:flex-row gap-1"
              >
                <div className="flex-1 flex items-center px-4 h-14 bg-slate-950/50 rounded-lg focus-within:bg-slate-950 focus-within:border-slate-700 transition-all border border-transparent">
                  <Code2 className="text-slate-500 w-5 h-5 mr-3" />
                  <input
                    type="text"
                    placeholder="Job Title (e.g. Barista)"
                    className="bg-transparent w-full outline-none text-slate-100 text-sm font-mono"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                  />
                </div>
                <div className="flex-1 flex items-center px-4 h-14 bg-slate-950/50 rounded-lg focus-within:bg-slate-950 focus-within:border-slate-700 transition-all border border-transparent">
                  <MapPin className="text-slate-500 w-5 h-5 mr-3" />
                  <input
                    type="text"
                    placeholder="Location"
                    className="bg-transparent w-full outline-none text-slate-100 text-sm font-mono"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
                <button
                  disabled={loading}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white px-8 h-14 rounded-lg font-bold transition-all min-w-[140px] flex justify-center items-center shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <Loader2 className="animate-spin w-4 h-4" />
                  ) : (
                    <span className="font-mono text-sm">RUN {">"}</span>
                  )}
                </button>
              </form>
            </div>

            <div
              className={`space-y-4 transition-all duration-1000 delay-200 ${hasSearched ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10 pointer-events-none hidden"}`}
            >
              {error && (
                <div className="bg-red-950/30 text-red-400 p-4 rounded-lg border border-red-900/50 text-sm font-mono">
                  {error}
                </div>
              )}
              {currentJobs.map((job, index) => (
                <div
                  key={index}
                  className="bg-slate-900/50 p-6 rounded-xl border border-slate-800 hover:border-cyan-500/50 transition-all group cursor-pointer relative overflow-hidden"
                  onClick={() => window.open(job.url, "_blank")}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-bold text-slate-100 group-hover:text-cyan-400 transition-colors font-mono">
                      {job.job_title}
                    </h3>
                    <ExternalLink className="text-slate-600 group-hover:text-cyan-400 w-4 h-4" />
                  </div>
                  <div className="flex flex-wrap gap-2 font-mono text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Briefcase size={12} /> {job.company}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin size={12} /> {job.location}
                    </span>
                    {job.salary && job.salary !== "Not Specified" && (
                      <span className="text-emerald-400">{job.salary}</span>
                    )}
                  </div>
                </div>
              ))}
              {/* Pagination Controls */}
              {!loading && jobs.length > 0 && (
                <div className="flex justify-center items-center gap-4 py-4 font-mono text-sm">
                  <button
                    onClick={() => paginate(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-400 disabled:opacity-30"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <span className="text-slate-500">
                    PAGE <span className="text-cyan-400">{currentPage}</span> /{" "}
                    {totalPages}
                  </span>
                  <button
                    onClick={() => paginate(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-cyan-400 disabled:opacity-30"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
