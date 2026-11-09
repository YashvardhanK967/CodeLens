import React from 'react';
import { Sparkles, AlertTriangle, ArrowRight, CheckCircle } from 'lucide-react';

export default function RecommendationsList({ recommendations = [], insights = [] }) {
  if ((!recommendations || recommendations.length === 0) && (!insights || insights.length === 0)) {
    return null;
  }

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'High':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'Medium':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      default:
        return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Actionable Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="text-amber-400" size={18} />
              AI Practice Recommendations
            </h3>
            <span className="text-xs text-slate-400 font-mono">{recommendations.length} insights</span>
          </div>

          <div className="space-y-3">
            {recommendations.map((rec, i) => (
              <div
                key={i}
                className="bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 rounded-xl p-4 transition space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${getPriorityBadge(
                      rec.priority
                    )}`}
                  >
                    {rec.priority} Priority
                  </span>
                  {rec.topic && (
                    <span className="text-xs font-semibold text-slate-300 font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {rec.topic}
                    </span>
                  )}
                </div>
                <p className="text-xs font-semibold text-slate-100">{rec.action}</p>
                <p className="text-[11px] text-slate-400 leading-relaxed">{rec.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. Analytical Insights */}
      {insights.length > 0 && (
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="text-indigo-400" size={18} />
              Profile Observations & Trends
            </h3>
            <span className="text-xs text-slate-400 font-mono">{insights.length} notes</span>
          </div>

          <div className="space-y-3">
            {insights.map((item, i) => (
              <div
                key={i}
                className="bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 rounded-xl p-4 transition space-y-1"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">{item.title}</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

