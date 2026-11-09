import React, { useState, useMemo } from 'react';
import { Activity, Flame, Calendar, Info } from 'lucide-react';
import { generateYearDays, getIntensityClass } from '../utils/heatmapUtils';

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

export default function ActivityHeatmap({ 
  dailyActivity = [], 
  platformDailyActivity = {}, 
  availablePlatforms = [] 
}) {
  const [selectedPlatform, setSelectedPlatform] = useState('ALL');
  const [hoveredDay, setHoveredDay] = useState(null);

  // Compute active activity list based on tab
  const activeActivityData = useMemo(() => {
    if (selectedPlatform === 'ALL') {
      return dailyActivity || [];
    }
    return platformDailyActivity[selectedPlatform] || [];
  }, [selectedPlatform, dailyActivity, platformDailyActivity]);

  // Generate 52-week calendar grid
  const { weeks, totalSubmissions, activeDays, maxSingleDay } = useMemo(() => {
    return generateYearDays(activeActivityData);
  }, [activeActivityData]);

  // Month label calculation across weeks
  const monthHeaders = useMemo(() => {
    const headers = [];
    let lastMonth = -1;

    weeks.forEach((week, weekIndex) => {
      const firstValidDay = week.find((d) => d.date);
      if (firstValidDay) {
        const month = new Date(firstValidDay.date).getMonth();
        if (month !== lastMonth) {
          headers.push({ index: weekIndex, name: MONTH_NAMES[month] });
          lastMonth = month;
        }
      }
    });

    return headers;
  }, [weeks]);

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header & Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="text-emerald-400" size={20} />
            Submission Activity Heatmap
          </h2>
          <p className="text-xs text-slate-400">
            View practice frequency across 365 days. Toggle between combined and platform-specific heatmaps.
          </p>
        </div>

        {/* Platform Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-950/80 rounded-xl border border-slate-800/80 self-start lg:self-auto">
          <button
            type="button"
            onClick={() => setSelectedPlatform('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              selectedPlatform === 'ALL'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            Combined (All Platforms)
          </button>

          {availablePlatforms.map((platform) => (
            <button
              key={platform}
              type="button"
              onClick={() => setSelectedPlatform(platform)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                selectedPlatform === platform
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {platform}
            </button>
          ))}
        </div>
      </div>

      {/* Heatmap Quick Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-2 text-xs">
        <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/60">
          <span className="text-slate-400 block mb-0.5">Submissions in 365 Days</span>
          <span className="text-base font-extrabold text-white">{totalSubmissions}</span>
        </div>
        <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/60">
          <span className="text-slate-400 block mb-0.5">Active Days</span>
          <span className="text-base font-extrabold text-emerald-400">{activeDays}</span>
        </div>
        <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/60">
          <span className="text-slate-400 block mb-0.5">Max Submissions in a Day</span>
          <span className="text-base font-extrabold text-cyan-400">{maxSingleDay}</span>
        </div>
        <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/60">
          <span className="text-slate-400 block mb-0.5">Selected View</span>
          <span className="text-base font-extrabold text-indigo-400">
            {selectedPlatform === 'ALL' ? 'Aggregated' : selectedPlatform}
          </span>
        </div>
      </div>

      {/* The 52-Week Calendar Grid */}
      <div className="overflow-x-auto pb-2 pt-1">
        <div className="min-w-[780px]">
          {/* Month Labels */}
          <div className="flex text-[11px] text-slate-400 mb-2 pl-7 font-mono relative h-4">
            {monthHeaders.map((m) => (
              <span
                key={`${m.name}-${m.index}`}
                className="absolute"
                style={{ left: `${m.index * 14.5 + 28}px` }}
              >
                {m.name}
              </span>
            ))}
          </div>

          <div className="flex gap-2">
            {/* Day of Week Labels (Mon, Wed, Fri) */}
            <div className="flex flex-col gap-[3px] text-[10px] text-slate-500 font-mono pr-1 pt-[1px]">
              {DAY_LABELS.map((d, i) => (
                <div key={i} className="h-3 leading-3 flex items-center justify-end w-5">
                  {d}
                </div>
              ))}
            </div>

            {/* Weeks columns */}
            <div className="flex gap-[3px]">
              {weeks.map((week, weekIdx) => (
                <div key={weekIdx} className="flex flex-col gap-[3px]">
                  {week.map((day, dayIdx) => {
                    const count = day.count;
                    const isHovered = hoveredDay && hoveredDay.date === day.date;
                    const intensityClass = getIntensityClass(count);

                    return (
                      <div
                        key={`${day.date}-${dayIdx}`}
                        onMouseEnter={() => !day.isFuture && setHoveredDay(day)}
                        onMouseLeave={() => setHoveredDay(null)}
                        className={`w-3 h-3 rounded-[2.5px] transition-all cursor-pointer ${
                          day.isFuture ? 'opacity-0 pointer-events-none' : intensityClass
                        } ${isHovered ? 'ring-2 ring-white scale-125 z-10' : ''}`}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tooltip & Legend Footer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800 gap-3">
        {/* Dynamic Tooltip Info */}
        <div className="font-mono flex items-center gap-1.5 h-5">
          {hoveredDay ? (
            <span className="text-slate-200">
              <strong className="text-emerald-400">{hoveredDay.count} submissions</strong> on{' '}
              {new Date(hoveredDay.date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
          ) : (
            <span className="text-slate-500">Hover over any day square to see details</span>
          )}
        </div>

        {/* Intensity Legend */}
        <div className="flex items-center gap-2">
          <span>Less</span>
          <div className="flex gap-1">
            <div className="w-3 h-3 rounded-[2px] bg-slate-800/80" title="0" />
            <div className="w-3 h-3 rounded-[2px] bg-emerald-950 border border-emerald-800/60" title="1-2" />
            <div className="w-3 h-3 rounded-[2px] bg-emerald-700" title="3-5" />
            <div className="w-3 h-3 rounded-[2px] bg-emerald-500" title="6-10" />
            <div className="w-3 h-3 rounded-[2px] bg-emerald-400" title="11+" />
          </div>
          <span>More</span>
        </div>
      </div>
    </div>
  );
}

