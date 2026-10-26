'use strict';
/**
 * Nestral — history. Appends each brief's totals to data/history.jsonl so the
 * product can show real day-over-day trends (sparkline, "vs yesterday").
 * Zero dependencies.
 */
const fs = require('fs');
const path = require('path');
const { ROOT } = require('./nestral');

const DIR = path.join(ROOT, 'data');
const FILE = path.join(DIR, 'history.jsonl');

function record(brief) {
  try {
    fs.mkdirSync(DIR, { recursive: true });
    const t = brief.totals || {};
    const row = {
      date: brief.date, at: new Date().toISOString(),
      ordersToday: t.ordersToday || 0, revenueToday: t.revenueToday || 0,
      orders7d: t.orders7d || 0, revenue7d: t.revenue7d || 0,
      unfulfilled: t.unfulfilled || 0,
      high: (brief.topActions || []).filter((a) => a.severity === 'high').length,
      currency: t.currency || 'USD',
    };
    fs.appendFileSync(FILE, JSON.stringify(row) + '\n');
    return row;
  } catch { return null; }
}

// Latest row per date, oldest→newest, capped to `days`.
function read(days = 14) {
  try {
    const lines = fs.readFileSync(FILE, 'utf8').trim().split('\n').filter(Boolean);
    const byDate = new Map();
    for (const l of lines) { try { const r = JSON.parse(l); byDate.set(r.date, r); } catch {} }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date)).slice(-days);
  } catch { return []; }
}

module.exports = { record, read, FILE };
