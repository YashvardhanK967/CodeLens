import React, { useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  LineChart, Line, CartesianGrid, Legend, Cell 
} from 'recharts';
import { BarChart3, TrendingUp, PieChart, Layers } from 'lucide-react';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6'];

export default function GraphsSection({ 
  charts, 
  platformComparison = [], 
  contestAnalytics, 
  topicAnalytics = [] 
}) {
  const [activeTab, setActiveTab] = useState('ALL');

  if (!charts) return null;

  const availablePlatforms = platformComparison.map((p) => p.platform);

  // Contest rating history for individual platforms
  const getPlatformContestSeries = (platformName) => {
    const series = charts.contest_rating_by_platform?.find(
      (s) => s.platform.toLowerCase() === platformName.toLowerCase()
    );
    return series?.data || [];
  };

  // Platform-specific metrics
  const selectedPlatformData = platformComparison.find(
    (p) => p.platform.toLowerCase() === activeTab.toLowerCase()
  );

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header and Toggle Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart3 className="text-indigo-400" size={20} />
            Performance & Trajectory Graphs
          </h2>
          <p className="text-xs text-slate-400">
            Interactive charts with toggle between aggregated metrics and platform-specific curves.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-950/80 rounded-xl border border-slate-800/80 self-start lg:self-auto">
          <button
            type="button"
            onClick={() => setActiveTab('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'ALL'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            Aggregated Overview
          </button>

          {availablePlatforms.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setActiveTab(p)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === p
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* VIEW 1: AGGREGATED */}
      {activeTab === 'ALL' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Platform Solved Breakdown */}
          <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/70">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <PieChart size={16} className="text-indigo-400" />
                Solved Problems by Platform
              </h3>
              <span className="text-xs text-slate-400">Distinct counts</span>
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.platform_solved || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="platform" stroke="#64748b" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      color: '#f8fafc',
                    }}
                  />
                  <Bar dataKey="solved" radius={[6, 6, 0, 0]}>
                    {(charts.platform_solved || []).map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Top Topic Mastery */}
          <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/70">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <Layers size={16} className="text-purple-400" />
                Top DSA Topic Distribution
              </h3>
              <span className="text-xs text-slate-400">Unique problems solved</span>
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={(charts.topic_distribution || []).slice(0, 8)}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="topic" type="category" stroke="#94a3b8" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      color: '#f8fafc',
                    }}
                  />
                  <Bar dataKey="solved" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Combined Multi-Platform Contest Rating Trajectory */}
          {charts.contest_rating_by_platform?.length > 0 && (
            <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/70 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                  <TrendingUp size={16} className="text-cyan-400" />
                  Contest Rating Progression Across Platforms
                </h3>
                <span className="text-xs text-slate-400">Normalized Timeline</span>
              </div>

              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" domain={['auto', 'auto']} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '8px',
                        color: '#f8fafc',
                      }}
                    />
                    <Legend />
                    {charts.contest_rating_by_platform.map((series, idx) => (
                      <Line
                        key={series.platform}
                        data={series.data}
                        type="monotone"
                        dataKey="rating"
                        name={series.platform}
                        stroke={COLORS[idx % COLORS.length]}
                        strokeWidth={2.5}
                        dot={{ r: 3 }}
                        activeDot={{ r: 6 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: INDIVIDUAL PLATFORM */}
      {activeTab !== 'ALL' && (
        <div className="space-y-6">
          {/* Platform Specific Stat Header */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/70">
              <span className="text-xs text-slate-400 block mb-1">Platform</span>
              <span className="text-base font-bold text-white">{activeTab}</span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/70">
              <span className="text-xs text-slate-400 block mb-1">Current Rating</span>
              <span className="text-base font-bold text-amber-400">
                {selectedPlatformData?.current_rating || 'Unrated'}
              </span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/70">
              <span className="text-xs text-slate-400 block mb-1">Problems Solved</span>
              <span className="text-base font-bold text-emerald-400">
                {selectedPlatformData?.solved || 0}
              </span>
            </div>
            <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/70">
              <span className="text-xs text-slate-400 block mb-1">Accuracy</span>
              <span className="text-base font-bold text-cyan-400">
                {selectedPlatformData?.submission_success_rate ?? 'N/A'}%
              </span>
            </div>
          </div>

          {/* Individual Contest Rating Progression */}
          {getPlatformContestSeries(activeTab).length > 0 ? (
            <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/70">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-400" />
                  {activeTab} Contest Rating History
                </h3>
                <span className="text-xs text-slate-400">
                  {getPlatformContestSeries(activeTab).length} Contests Logged
                </span>
              </div>

              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={getPlatformContestSeries(activeTab)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" domain={['auto', 'auto']} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '8px',
                        color: '#f8fafc',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rating"
                      stroke="#6366f1"
                      strokeWidth={3}
                      dot={{ r: 3, fill: '#6366f1' }}
                      activeDot={{ r: 6, fill: '#818cf8' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="bg-slate-950/50 p-8 rounded-xl border border-slate-800/70 text-center text-slate-400 text-xs">
              No rating history recorded for {activeTab}.
            </div>
          )}

          {/* Submission Accuracy Ratio Bar for this platform */}
          {selectedPlatformData && (
            <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/70">
              <h3 className="font-semibold text-sm text-white mb-3">Submission Breakdown ({activeTab})</h3>
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'Accepted Submissions', count: selectedPlatformData.correct_submissions },
                      { name: 'Failed Submissions', count: selectedPlatformData.failed_submissions },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '8px',
                        color: '#f8fafc',
                      }}
                    />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      <Cell fill="#10b981" />
                      <Cell fill="#f43f5e" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

