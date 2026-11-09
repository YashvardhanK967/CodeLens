import React from 'react';
import { 
  ArrowLeft, RefreshCw, User, ShieldCheck, 
  Layers, Code2, AlertCircle 
} from 'lucide-react';
import MetricCards from './MetricCards';
import PlatformComparison from './PlatformComparison';
import ActivityHeatmap from './ActivityHeatmap';
import GraphsSection from './GraphsSection';
import TopicAnalyticsTable from './TopicAnalyticsTable';
import RecommendationsList from './RecommendationsList';

export default function AnalyticsDashboard({ data, onReset, onRefresh, loading }) {
  if (!data) return null;

  const {
    user_summary,
    overview,
    platform_comparison,
    topic_analytics,
    contest_analytics,
    charts,
    insights,
    recommendations,
    data_quality,
  } = data;

  const availablePlatforms = (platform_comparison || []).map((p) => p.platform);

  return (
    <div className="space-y-8 pb-16">
      {/* Top Navigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={onReset}
            className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Back to profile search"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-white tracking-tight">
                {user_summary?.username || 'Candidate Profile'}
              </h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-semibold">
                Unified
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Aggregated analytics across {user_summary?.platforms_connected || 1} connected platform profiles
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Re-fetch Data</span>
          </button>
        </div>
      </div>

      {/* 1. Aggregate Metric Cards */}
      <MetricCards
        overview={overview}
        userSummary={user_summary}
        dataQuality={data_quality}
      />

      {/* 2. Side-by-Side Platform Breakdown */}
      <PlatformComparison platforms={platform_comparison} />

      {/* 3. Activity Heatmap with Aggregated & Individual Platform Toggles */}
      <ActivityHeatmap
        dailyActivity={charts?.daily_activity || []}
        platformDailyActivity={charts?.platform_daily_activity || {}}
        availablePlatforms={availablePlatforms}
      />

      {/* 4. Performance & Trajectory Graphs with Aggregated & Individual Platform Toggles */}
      <GraphsSection
        charts={charts}
        platformComparison={platform_comparison}
        contestAnalytics={contest_analytics}
        topicAnalytics={topic_analytics}
      />

      {/* 5. Topic Analytics Table */}
      <TopicAnalyticsTable topics={topic_analytics} />

      {/* 6. AI Recommendations & Observations */}
      <RecommendationsList
        recommendations={recommendations}
        insights={insights}
      />

      {/* 7. Data Quality & Audit Notes */}
      {data_quality?.notes?.length > 0 && (
        <div className="bg-slate-900/40 border border-slate-800/60 rounded-2xl p-5 text-xs text-slate-400 space-y-2">
          <div className="flex items-center gap-2 font-semibold text-slate-300">
            <ShieldCheck size={16} className="text-emerald-400" />
            <span>Verification & Audit Diagnostics</span>
          </div>
          <ul className="list-disc list-inside space-y-1 pl-1 text-[11px] text-slate-400">
            {data_quality.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

