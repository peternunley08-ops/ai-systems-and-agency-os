'use strict';
/**
 * Nestral — brief engine
 * Turns a set of per-store snapshots into ONE portfolio brief, ranked by
 * "what needs YOU today". This is the product's core value: signal, not dashboards.
 *
 * Pure functions, zero dependencies.
 */
const { trendPct } = require('./shopify');

const SEV = { high: 3, med: 2, low: 1 };

function money(n, cur = 'USD') {
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(n || 0); }
  catch { return '$' + Math.round(n || 0); }
}

// ---- rule engine: snapshot -> attention items ----
function analyzeStore(snap) {
  const items = [];
  if (!snap.ok) {
    items.push({ severity: 'high', text: `${snap.label}: ${snap.error || 'connection failed'}`, action: 'Reconnect the workspace token' });
    return { label: snap.label, source: snap.source, ok: false, items, headline: snap.error || 'connection failed' };
  }
  const m = snap.metrics;
  const cur = m.currency;
  const add = (severity, text, action) => items.push({ severity, text, action });

  // sales trend (7d vs prior 7d)
  const t = trendPct(m.revenue7d, m.revenuePrev7d);
  if (m.revenuePrev7d > 0 && t <= -30) add('high', `Sales down ${Math.abs(t)}% wk/wk (${money(m.revenue7d, cur)} vs ${money(m.revenuePrev7d, cur)})`, 'Check ad spend / traffic for this brand');
  else if (t >= 50 && m.revenue7d > 0) add('low', `Sales up ${t}% wk/wk — momentum`, 'Consider scaling the winning channel');

  // no sales
  if (m.lastOrderAgeDays != null && m.lastOrderAgeDays >= 7) add('high', `No orders in ${m.lastOrderAgeDays} days`, 'Is the store live + are ads running?');

  // fulfillment backlog
  if (m.unfulfilled >= 10) add('high', `${m.unfulfilled} orders awaiting fulfillment`, 'Fulfill / push to supplier today');
  else if (m.unfulfilled >= 3) add('med', `${m.unfulfilled} orders to fulfill`, 'Clear the fulfillment queue');

  // payments needing review
  if (m.pendingPayment >= 1) add('med', `${m.pendingPayment} order(s) with pending payment`, 'Capture or cancel');

  // inventory
  if (m.outOfStock >= 1) add('high', `${m.outOfStock} active variant(s) OUT of stock`, 'Reorder or pause ads to those products');
  else if (m.lowStock >= 1) add('med', `${m.lowStock} variant(s) low on stock`, 'Plan a reorder');

  items.sort((a, b) => SEV[b.severity] - SEV[a.severity]);
  const headline = items[0]?.text || `Healthy — ${m.orders7d} orders / ${money(m.revenue7d, cur)} this week`;
  return { label: snap.label, source: snap.source, ok: true, mock: snap.mock, metrics: m, items, headline };
}

function buildBrief(snaps, opts = {}) {
  const date = opts.date || new Date().toISOString().slice(0, 10);
  const stores = snaps.map(analyzeStore);

  // portfolio totals (only stores that resolved)
  const live = stores.filter((s) => s.ok);
  const cur = live[0]?.metrics?.currency || 'USD';
  const totals = live.reduce((a, s) => {
    a.ordersToday += s.metrics.ordersToday; a.revenueToday += s.metrics.revenueToday;
    a.orders7d += s.metrics.orders7d; a.revenue7d += s.metrics.revenue7d;
    a.unfulfilled += s.metrics.unfulfilled; return a;
  }, { ordersToday: 0, revenueToday: 0, orders7d: 0, revenue7d: 0, unfulfilled: 0, currency: cur });

  // top actions across the whole portfolio
  const topActions = [];
  for (const s of stores) for (const it of s.items) topActions.push({ store: s.label, ...it });
  topActions.sort((a, b) => SEV[b.severity] - SEV[a.severity]);

  const anyMock = stores.some((s) => s.mock);
  return { date, totals, stores, topActions, anyMock, storeCount: stores.length };
}

// ---- renderers ----
function bar(sev) { return sev === 'high' ? '🔴' : sev === 'med' ? '🟡' : '🟢'; }

function renderMarkdown(brief) {
  const t = brief.totals; const cur = t.currency;
  const L = [];
  L.push(`# 🪺 Nestral — morning brief · ${brief.date}`);
  if (brief.anyMock) L.push(`> ⚠️ Demo data (no live Shopify tokens connected yet).`);
  L.push('');
  L.push(`**Portfolio today:** ${t.ordersToday} orders · ${money(t.revenueToday, cur)}  |  **7-day:** ${t.orders7d} orders · ${money(t.revenue7d, cur)}  |  **${t.unfulfilled}** open across ${brief.storeCount} workspaces`);
  L.push('');
  const high = brief.topActions.filter((a) => a.severity === 'high');
  L.push(`## ${high.length ? `⚡ Needs you today (${high.length})` : '✅ Nothing urgent today'}`);
  for (const a of brief.topActions.slice(0, 8)) L.push(`- ${bar(a.severity)} **${a.store}** — ${a.text}  _→ ${a.action}_`);
  L.push('');
  L.push(`## Per workspace`);
  for (const s of brief.stores) {
    const tag = s.ok ? bar(s.items[0]?.severity || 'low') : '🔴';
    L.push(`- ${tag} **${s.label}** — ${s.headline}`);
  }
  return L.join('\n');
}

function renderText(brief) {
  return renderMarkdown(brief)
    .replace(/^#+\s*/gm, '').replace(/\*\*/g, '').replace(/_→/g, '→').replace(/_/g, '').replace(/^> /gm, '');
}

module.exports = { buildBrief, analyzeStore, renderMarkdown, renderText, money };
