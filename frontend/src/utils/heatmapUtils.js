export function generateYearDays(dailyActivity = []) {
  const activityMap = new Map();
  if (Array.isArray(dailyActivity)) {
    for (const item of dailyActivity) {
      if (item && item.date) {
        activityMap.set(item.date, (activityMap.get(item.date) || 0) + (item.activity_count || 0));
      }
    }
  }

  const today = new Date();
  today.setHours(23, 59, 59, 999);

  // Go back 364 days so we have 365 days total
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - 364);

  // Align start date to Sunday for a clean grid
  const startDay = startDate.getDay();
  startDate.setDate(startDate.getDate() - startDay);

  const weeks = [];
  let currentWeek = [];
  let currentDate = new Date(startDate);

  let totalSubmissions = 0;
  let activeDays = 0;
  let maxSingleDay = 0;

  while (currentDate <= today || currentWeek.length > 0) {
    const dateStr = currentDate.toISOString().split('T')[0];
    const isFuture = currentDate > today;
    const count = isFuture ? 0 : (activityMap.get(dateStr) || 0);

    if (!isFuture) {
      totalSubmissions += count;
      if (count > 0) activeDays += 1;
      if (count > maxSingleDay) maxSingleDay = count;
    }

    currentWeek.push({
      date: dateStr,
      count: isFuture ? null : count,
      dayOfWeek: currentDate.getDay(),
      isFuture,
    });

    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }

    if (currentDate > today && currentWeek.length === 0) {
      break;
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  return {
    weeks,
    totalSubmissions,
    activeDays,
    maxSingleDay,
  };
}

export function getIntensityClass(count) {
  if (count === null || count === undefined || count === 0) {
    return 'bg-slate-800/80 hover:ring-1 hover:ring-slate-500';
  }
  if (count <= 2) {
    return 'bg-emerald-950 text-emerald-300 border border-emerald-800/60 hover:ring-1 hover:ring-emerald-400';
  }
  if (count <= 5) {
    return 'bg-emerald-700 text-emerald-100 hover:ring-1 hover:ring-emerald-300';
  }
  if (count <= 10) {
    return 'bg-emerald-500 text-white hover:ring-1 hover:ring-emerald-200';
  }
  return 'bg-emerald-400 text-slate-950 font-bold hover:ring-1 hover:ring-white';
}

