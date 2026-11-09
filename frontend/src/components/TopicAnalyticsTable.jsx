import React, { useState } from 'react';
import { Layers, Search, CheckCircle, Target, ArrowUpDown } from 'lucide-react';

export default function TopicAnalyticsTable({ topics = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');

  if (!topics || topics.length === 0) return null;

  const filteredTopics = topics.filter((t) => {
    const matchesSearch = t.topic.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesClass = filterClass === 'ALL' || t.classification === filterClass;
    return matchesSearch && matchesClass;
  });

  const getBadgeStyle = (classification) => {
    switch (classification) {
      case 'Strong':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'Good':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'Developing':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'Needs Improvement':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-4">
      {/* Table Header with Search and Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="text-purple-400" size={20} />
            DSA Topic Mastery & Accuracy
          </h2>
          <p className="text-xs text-slate-400">
            Deduplicated topic completion rates and judged submission accuracy.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Search Bar */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Filter topics..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-950/80 border border-slate-800 text-xs rounded-xl pl-8 pr-3 py-1.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition w-36 sm:w-48"
            />
          </div>

          {/* Classification Dropdown */}
          <select
            value={filterClass}
            onChange={(e) => setFilterClass(e.target.value)}
            className="bg-slate-950/80 border border-slate-800 text-xs rounded-xl px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Status</option>
            <option value="Strong">Strong</option>
            <option value="Good">Good</option>
            <option value="Developing">Developing</option>
            <option value="Needs Improvement">Needs Improvement</option>
            <option value="Insufficient Data">Insufficient Data</option>
          </select>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800 bg-slate-950/40">
            <tr>
              <th className="py-3 px-4 rounded-l-xl">Topic</th>
              <th className="py-3 px-4">Solved / Attempted</th>
              <th className="py-3 px-4">Problem Completion</th>
              <th className="py-3 px-4">Judged Submissions</th>
              <th className="py-3 px-4">Submission Accuracy</th>
              <th className="py-3 px-4 rounded-r-xl">Skill Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredTopics.length > 0 ? (
              filteredTopics.map((t) => (
                <tr key={t.topic} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-sans font-semibold text-slate-100">{t.topic}</td>
                  <td className="py-3 px-4 text-slate-300">
                    <span className="text-emerald-400 font-bold">{t.solved ?? '—'}</span> /{' '}
                    <span>{t.attempted ?? '—'}</span>
                  </td>
                  <td className="py-3 px-4">
                    {t.completion_rate !== null && t.completion_rate !== undefined ? (
                      <span className="font-semibold text-slate-200">{t.completion_rate}%</span>
                    ) : (
                      <span className="text-slate-500">N/A</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    <span className="text-emerald-400 font-medium">{t.accepted_submissions ?? 0} OK</span> /{' '}
                    <span className="text-rose-400/80 font-medium">{t.failed_submissions ?? 0}</span>
                  </td>
                  <td className="py-3 px-4 font-semibold text-indigo-300">
                    {t.submission_success_rate !== null && t.submission_success_rate !== undefined
                      ? `${t.submission_success_rate}%`
                      : 'N/A'}
                  </td>
                  <td className="py-3 px-4 font-sans">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getBadgeStyle(
                        t.classification
                      )}`}
                    >
                      {t.classification}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                  No topics match your filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

