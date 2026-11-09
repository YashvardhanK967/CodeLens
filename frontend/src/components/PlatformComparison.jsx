import React from 'react';
import { 
  Trophy, CheckCircle2, XCircle, Award, 
  ExternalLink, BarChart2 
} from 'lucide-react';

const PLATFORM_THEMES = {
  Codeforces: {
    badge: 'CF',
    color: 'from-red-500/20 to-red-600/5',
    border: 'border-red-500/30',
    text: 'text-red-400',
    ring: 'bg-red-500',
    urlBase: 'https://codeforces.com/profile/',
  },
  LeetCode: {
    badge: 'LC',
    color: 'from-amber-500/20 to-amber-600/5',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    ring: 'bg-amber-500',
    urlBase: 'https://leetcode.com/u/',
  },
  CodeChef: {
    badge: 'CC',
    color: 'from-orange-500/20 to-orange-600/5',
    border: 'border-orange-500/30',
    text: 'text-orange-400',
    ring: 'bg-orange-500',
    urlBase: 'https://www.codechef.com/users/',
  },
  GeeksforGeeks: {
    badge: 'GFG',
    color: 'from-emerald-500/20 to-emerald-600/5',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    ring: 'bg-emerald-500',
    urlBase: 'https://www.geeksforgeeks.org/user/',
  },
};

export default function PlatformComparison({ platforms = [] }) {
  if (!platforms || platforms.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart2 className="text-indigo-400" size={20} />
            Side-by-Side Platform Breakdown
          </h2>
          <p className="text-xs text-slate-400">
            Compare performance metrics and ratings across your connected profiles.
          </p>
        </div>
        <span className="text-xs font-medium px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
          {platforms.length} Platforms Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {platforms.map((p) => {
          const theme = PLATFORM_THEMES[p.platform] || {
            badge: p.platform.slice(0, 2).toUpperCase(),
            color: 'from-indigo-500/20 to-indigo-600/5',
            border: 'border-indigo-500/30',
            text: 'text-indigo-400',
            ring: 'bg-indigo-500',
            urlBase: '',
          };

          const accuracy = p.submission_success_rate !== null && p.submission_success_rate !== undefined 
            ? `${p.submission_success_rate}%` 
            : '—';

          return (
            <div
              key={`${p.platform}-${p.username}`}
              className={`bg-gradient-to-b ${theme.color} bg-slate-900/90 border ${theme.border} rounded-2xl p-5 flex flex-col justify-between shadow-xl transition-all hover:scale-[1.01]`}
            >
              <div>
                {/* Platform Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs bg-slate-950/80 border border-slate-800 ${theme.text}`}>
                      {theme.badge}
                    </span>
                    <div>
                      <h3 className="font-bold text-white text-base leading-none">{p.platform}</h3>
                      {theme.urlBase ? (
                        <a
                          href={`${theme.urlBase}${p.username}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1 mt-1 transition font-mono"
                        >
                          @{p.username}
                          <ExternalLink size={10} />
                        </a>
                      ) : (
                        <span className="text-xs text-slate-400 font-mono mt-1 block">@{p.username}</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Rating Card */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 mb-4">
                  <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
                    <span>Current Rating</span>
                    <Trophy size={14} className={theme.text} />
                  </div>
                  <div className="text-2xl font-black text-white tracking-tight">
                    {p.current_rating ? p.current_rating : <span className="text-slate-500 text-lg font-normal">Unrated</span>}
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Solved Problems:</span>
                    <span className="font-bold text-white text-sm">{p.solved}</span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Submission Accuracy:</span>
                    <span className="font-semibold text-emerald-400">{accuracy}</span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">Submissions (OK / Failed):</span>
                    <span className="font-mono text-slate-300">
                      <span className="text-emerald-400">{p.correct_submissions}</span> /{' '}
                      <span className="text-rose-400">{p.failed_submissions}</span>
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1.5">
                    <span className="text-slate-400">Contests Participated:</span>
                    <span className="font-bold text-white">{p.contests_participated}</span>
                  </div>
                </div>
              </div>

              {/* Progress bar visual for accuracy */}
              {p.submission_success_rate !== null && p.submission_success_rate !== undefined && (
                <div className="mt-4 pt-3 border-t border-slate-800/80">
                  <div className="w-full bg-slate-950/80 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${theme.ring}`}
                      style={{ width: `${Math.min(100, p.submission_success_rate)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

