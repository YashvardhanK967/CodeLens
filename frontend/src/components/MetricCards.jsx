import React from 'react';
import { 
  CheckCircle2, TrendingUp, Trophy, Calendar, 
  Layers, AlertCircle, ArrowUpRight 
} from 'lucide-react';

export default function MetricCards({ overview, userSummary, dataQuality }) {
  if (!overview) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Solved */}
      <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between text-slate-400 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Solved</span>
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <CheckCircle2 size={18} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">{overview.total_solved}</span>
          <span className="text-xs text-slate-400 font-mono">problems</span>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span>Reported by platforms:</span>
          <span className="font-semibold text-slate-200">{overview.platform_reported_solved}</span>
        </div>
      </div>

      {/* 2. Success Rate */}
      <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between text-slate-400 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Accuracy Rate</span>
          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <TrendingUp size={18} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">
            {overview.success_rate !== null ? `${overview.success_rate}%` : 'N/A'}
          </span>
          <span className="text-xs text-slate-400 font-mono">accuracy</span>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span className="text-emerald-400 font-medium">{overview.correct_submissions} accepted</span>
          <span className="text-rose-400/80 font-medium">{overview.failed_submissions} failed</span>
        </div>
      </div>

      {/* 3. Contests */}
      <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between text-slate-400 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Contests</span>
          <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
            <Trophy size={18} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">{overview.total_contests}</span>
          <span className="text-xs text-slate-400 font-mono">competitions</span>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span>Active profiles:</span>
          <span className="font-semibold text-slate-200">{userSummary?.platforms_connected || 1} platforms</span>
        </div>
      </div>

      {/* 4. Active Days */}
      <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between text-slate-400 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Practice Consistency</span>
          <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
            <Calendar size={18} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">
            {overview.active_days !== null && overview.active_days !== undefined ? overview.active_days : '—'}
          </span>
          <span className="text-xs text-slate-400 font-mono">active days</span>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <span>History status:</span>
          <span className="font-semibold text-emerald-400">
            {dataQuality?.history_complete ? 'Complete History' : 'Synchronized'}
          </span>
        </div>
      </div>
    </div>
  );
}

