// TinyStep 習慣與產能核心邏輯 (移植自 Python 核心模型)

export function getTodayStr(tz = "Asia/Taipei") {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
  return formatter.format(now); // YYYY-MM-DD
}

export function getDayName(tz = "Asia/Taipei") {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short"
  });
  return formatter.format(now); // Mon, Tue, etc.
}

export function checkAndRolloverDay(data, tz = "Asia/Taipei") {
  const todayStr = getTodayStr(tz);
  const lastDate = data.last_date;

  if (!lastDate) {
    data.last_date = todayStr;
    return null;
  }

  if (lastDate !== todayStr) {
    const tasks = data.tasks || [];
    const completedTasks = tasks.filter(t => t.completed).map(t => t.id);
    const downscaledTasks = tasks.filter(t => t.is_downscaled).map(t => t.id);

    if (!data.history) {
      data.history = {};
    }

    data.history[lastDate] = {
      completed: completedTasks,
      downscaled: downscaledTasks,
      completion_count: completedTasks.length,
      total_tasks: tasks.length
    };

    // 重置今日待辦狀態
    for (const t of tasks) {
      t.completed = false;
      t.is_downscaled = false;
      t.completed_at = null;
    }

    data.last_date = todayStr;
    return lastDate;
  }

  return null;
}

export function calculateStreak(data, tz = "Asia/Taipei") {
  const tasks = data.tasks || [];
  const history = data.history || {};

  const todayHasCompletion = tasks.some(t => t.completed);
  let streak = todayHasCompletion ? 1 : 0;

  // 往前追溯歷史日期
  const todayStr = getTodayStr(tz);
  let curDate = new Date(todayStr);

  while (true) {
    curDate.setDate(curDate.getDate() - 1);
    const checkDateStr = curDate.toISOString().slice(0, 10);
    const rec = history[checkDateStr];
    if (rec && rec.completed && rec.completed.length > 0) {
      streak += 1;
    } else {
      break;
    }
  }

  return streak;
}

export function calculateCapacity(data) {
  const profile = data.profile || {
    daily_focus_hours: 3.5,
    buffer_multiplier: 1.4,
    context_switch_penalty: 15.0,
    sustainable_limit: 0.7
  };

  const tasks = data.tasks || [];
  let rawMinutes = 0;
  let bufferedMinutes = 0;

  for (const t of tasks) {
    const mins = t.estimated_minutes || 25;
    const friction = t.friction_weight || t.cognitive_friction || 1.2;
    rawMinutes += mins;
    bufferedMinutes += mins * friction * profile.buffer_multiplier;
  }

  const penalty = tasks.length * profile.context_switch_penalty;
  const totalEffectiveMinutes = bufferedMinutes + penalty;
  const availableMinutes = profile.daily_focus_hours * 60;
  const loadRatio = availableMinutes > 0 ? totalEffectiveMinutes / availableMinutes : 0;

  let status = "OPTIMAL";
  if (loadRatio > 1.0) {
    status = "OVERLOAD";
  } else if (loadRatio > profile.sustainable_limit) {
    status = "WARNING";
  }

  return {
    rawMinutes: Math.round(rawMinutes),
    bufferedMinutes: Math.round(bufferedMinutes),
    contextSwitchPenalty: Math.round(penalty),
    totalEffectiveMinutes: Math.round(totalEffectiveMinutes),
    totalEffectiveHours: (totalEffectiveMinutes / 60).toFixed(1),
    availableHours: profile.daily_focus_hours,
    sustainableLimitHours: (profile.daily_focus_hours * profile.sustainable_limit).toFixed(1),
    loadRatio: Math.round(loadRatio * 100),
    status
  };
}

export function checkTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  task.completed = true;
  task.completed_at = new Date().toISOString();

  // 為對應身分認同投票 +1
  const iden = identities.find(i => i.id === task.identity_id);
  if (iden) {
    iden.votes = (iden.votes || 0) + 1;
  }

  return { task, identity: iden };
}

export function downscaleTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  task.is_downscaled = true;
  task.completed = true;
  task.completed_at = new Date().toISOString();

  const iden = identities.find(i => i.id === task.identity_id);
  if (iden) {
    iden.votes = (iden.votes || 0) + 1;
  }

  return { task, identity: iden };
}

export function restoreTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  if (task.completed) {
    const iden = identities.find(i => i.id === task.identity_id);
    if (iden && iden.votes > 0) {
      iden.votes -= 1;
    }
  }

  task.completed = false;
  task.is_downscaled = false;
  task.completed_at = null;

  return task;
}
