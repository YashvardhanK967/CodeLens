import React, { useState } from 'react';
import { 
  Code2, Sparkles, ArrowRight, ShieldCheck, 
  BarChart3, Activity, Layers, ExternalLink 
} from 'lucide-react';

export default function LandingPage({ onSubmit, loading, error }) {
  const [formData, setFormData] = useState({
    display_name: 'Kishlay Yashvardhan',
    codeforces: 'https://codeforces.com/profile/YashvardhanK07',
    leetcode: 'https://leetcode.com/u/Kishlay_Yashvardhan/',
    codechef: '',
    geeksforgeeks: '',
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFillDemo = () => {
    setFormData({
      display_name: 'Kishlay Yashvardhan',
      codeforces: 'https://codeforces.com/profile/YashvardhanK07',
      leetcode: 'https://leetcode.com/u/Kishlay_Yashvardhan/',
      codechef: '',
      geeksforgeeks: '',
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const isFormValid =
    formData.codeforces.trim() ||
    formData.leetcode.trim() ||
    formData.codechef.trim() ||
    formData.geeksforgeeks.trim();

  return (
    <div className="relative min-h-[90vh] flex flex-col justify-center items-center px-4 py-12">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-indigo-600/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 left-1/3 w-[300px] h-[250px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-4 mb-10 relative z-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold tracking-wide uppercase">
          <Sparkles size={14} className="text-indigo-400" />
          Multi-Platform Competitive Programming Engine
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Unified Analytics for <br />
          <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
            Every Coding Platform
          </span>
        </h1>

        <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto">
          Aggregate solved problems, track real-time rating trajectories, discover topic mastery, 
          and visualize unified activity heatmaps across Codeforces, LeetCode, CodeChef, and GeeksforGeeks.
        </p>
      </div>

      {/* Main 4-Box Form */}
      <div className="w-full max-w-3xl mx-auto relative z-10">
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 shadow-2xl shadow-indigo-950/40 rounded-3xl p-6 md:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 gap-3">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Code2 className="text-indigo-400" size={20} />
                Enter Coding Profiles
              </h2>
              <p className="text-xs text-slate-400">
                Provide usernames or full profile URLs. Provide at least one platform.
              </p>
            </div>
            <button
              type="button"
              onClick={handleFillDemo}
              className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-800 text-indigo-300 hover:bg-slate-700/80 transition self-start sm:self-auto border border-slate-700/50"
            >
              Fill Example Handles
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Optional Display Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Display Name
              </label>
              <input
                type="text"
                placeholder="e.g. Kishlay Yashvardhan"
                value={formData.display_name}
                onChange={(e) => handleChange('display_name', e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition"
              />
            </div>

            {/* 4 Platform Boxes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Box 1: Codeforces */}
              <div className="group relative bg-slate-950/50 hover:bg-slate-950/80 p-4 rounded-2xl border border-slate-800/90 hover:border-indigo-500/40 transition">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center font-bold text-xs">
                      CF
                    </span>
                    <span className="font-semibold text-sm text-white">Codeforces</span>
                  </div>
                  <span className="text-[11px] text-slate-500">API verified</span>
                </div>
                <input
                  type="text"
                  placeholder="https://codeforces.com/profile/username"
                  value={formData.codeforces}
                  onChange={(e) => handleChange('codeforces', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800/80 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition font-mono"
                />
              </div>

              {/* Box 2: LeetCode */}
              <div className="group relative bg-slate-950/50 hover:bg-slate-950/80 p-4 rounded-2xl border border-slate-800/90 hover:border-amber-500/40 transition">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xs">
                      LC
                    </span>
                    <span className="font-semibold text-sm text-white">LeetCode</span>
                  </div>
                  <span className="text-[11px] text-slate-500">GraphQL synced</span>
                </div>
                <input
                  type="text"
                  placeholder="https://leetcode.com/u/username/"
                  value={formData.leetcode}
                  onChange={(e) => handleChange('leetcode', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800/80 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500 transition font-mono"
                />
              </div>

              {/* Box 3: CodeChef */}
              <div className="group relative bg-slate-950/50 hover:bg-slate-950/80 p-4 rounded-2xl border border-slate-800/90 hover:border-orange-500/40 transition">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-400 flex items-center justify-center font-bold text-xs">
                      CC
                    </span>
                    <span className="font-semibold text-sm text-white">CodeChef</span>
                  </div>
                  <span className="text-[11px] text-slate-500">Scraped rating</span>
                </div>
                <input
                  type="text"
                  placeholder="Username or profile URL"
                  value={formData.codechef}
                  onChange={(e) => handleChange('codechef', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800/80 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-orange-500 transition font-mono"
                />
              </div>

              {/* Box 4: GeeksforGeeks */}
              <div className="group relative bg-slate-950/50 hover:bg-slate-950/80 p-4 rounded-2xl border border-slate-800/90 hover:border-emerald-500/40 transition">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                      GFG
                    </span>
                    <span className="font-semibold text-sm text-white">GeeksforGeeks</span>
                  </div>
                  <span className="text-[11px] text-slate-500">Practice score</span>
                </div>
                <input
                  type="text"
                  placeholder="Username or profile URL"
                  value={formData.geeksforgeeks}
                  onChange={(e) => handleChange('geeksforgeeks', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800/80 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 transition font-mono"
                />
              </div>
            </div>

            {error && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!isFormValid || loading}
              className={`w-full py-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 shadow-lg transition duration-200 ${
                !isFormValid || loading
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                  : 'bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white shadow-indigo-500/25 cursor-pointer active:scale-[0.99]'
              }`}
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Connecting Platforms & Analyzing...</span>
                </>
              ) : (
                <>
                  <span>Generate Unified Analytics</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-8">
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-slate-400 text-xs">
            <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
            <span>Exact Deduplication</span>
          </div>
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-slate-400 text-xs">
            <Activity size={16} className="text-cyan-400 shrink-0" />
            <span>Interactive Heatmaps</span>
          </div>
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-slate-400 text-xs">
            <BarChart3 size={16} className="text-indigo-400 shrink-0" />
            <span>Side-by-Side Charts</span>
          </div>
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/40 border border-slate-800/60 text-slate-400 text-xs">
            <Layers size={16} className="text-purple-400 shrink-0" />
            <span>DSA Topic Mastery</span>
          </div>
        </div>
      </div>
    </div>
  );
}

