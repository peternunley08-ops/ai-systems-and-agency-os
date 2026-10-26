'use strict';
/**
 * Nestral — "ask your portfolio". A deterministic, zero-dependency query engine
 * over the latest brief snapshot. Answers the common operator questions without
 * an LLM; designed so an LLM can be dropped in later (set NESTRAL_LLM_KEY).
 */
const { money } = require('./brief');

function trend(s) {
  const m = s.metrics || {}; if (!m.revenuePrev7d) return m.revenue7d ? 100 : 0;
  return Math.round(((m.revenue7d - m.revenuePrev7d) / m.revenuePrev7d) * 100);
}
const live = (b) => b.stores.filter((s) => s.ok);

function ask(question, brief) {
  const q = String(question || '').toLowerCase().trim();
  const L = live(brief); const cur = brief.totals.currency;
  if (!q) return { answer: 'Ask me about your portfolio — e.g. "best week?", "what needs me?", "total revenue", "out of stock".' };

  // named workspace?
  const named = L.find((s) => q.includes(s.label.toLowerCase()));
  if (named) {
    const m = named.metrics;
    return { answer: `${named.label}: ${named.headline}. ${m.orders7d} orders / ${money(m.revenue7d, m.currency)} this week (${trend(named) >= 0 ? '+' : ''}${trend(named)}% wk/wk), ${m.unfulfilled} open, ${m.ordersToday} today.` };
  }
  if (/(best|top|winner|growing|up )/.test(q)) {
    const w = [...L].sort((a, b) => trend(b) - trend(a))[0];
    return { answer: w ? `Best momentum: ${w.label}, ${trend(w) >= 0 ? '+' : ''}${trend(w)}% wk/wk (${money(w.metrics.revenue7d, w.metrics.currency)}).` : 'No data.' };
  }
  if (/(worst|down|drop|losing|falling|struggl)/.test(q)) {
    const w = [...L].sort((a, b) => trend(a) - trend(b))[0];
    return { answer: w ? `Needs attention most: ${w.label}, ${trend(w)}% wk/wk — ${w.headline}.` : 'No data.' };
  }
  if (/(fulfil|ship|backlog|open order|to handle)/.test(q)) {
    const tops = [...L].filter((s) => s.metrics.unfulfilled).sort((a, b) => b.metrics.unfulfilled - a.metrics.unfulfilled);
    return { answer: `${brief.totals.unfulfilled} open across the portfolio.` + (tops.length ? ' Most: ' + tops.slice(0, 3).map((s) => `${s.label} (${s.metrics.unfulfilled})`).join(', ') + '.' : '') };
  }
  if (/(stock|inventory|out of)/.test(q)) {
    const oos = L.filter((s) => s.metrics.outOfStock || s.metrics.lowStock);
    return { answer: oos.length ? 'Stock risk: ' + oos.map((s) => `${s.label} (${s.metrics.outOfStock} out, ${s.metrics.lowStock} low)`).join('; ') + '.' : 'No stock risks right now.' };
  }
  if (/(revenue|sales|money|making|total|how much)/.test(q)) {
    return { answer: `Portfolio: ${money(brief.totals.revenueToday, cur)} today, ${money(brief.totals.revenue7d, cur)} over 7 days across ${brief.storeCount} workspaces.` };
  }
  if (/(need|urgent|today|do |priorit|focus)/.test(q)) {
    const hi = brief.topActions.filter((a) => a.severity === 'high').slice(0, 5);
    return { answer: hi.length ? 'Today: ' + hi.map((a) => `${a.store} — ${a.text}`).join(' · ') : 'Nothing urgent today. ✅' };
  }
  if (/(quiet|silent|no sales|dead|live)/.test(q)) {
    const dead = L.filter((s) => s.metrics.lastOrderAgeDays >= 7);
    return { answer: dead.length ? 'Gone quiet: ' + dead.map((s) => `${s.label} (${s.metrics.lastOrderAgeDays}d)`).join(', ') + '.' : 'Everything has recent activity.' };
  }
  // fallback summary
  const hi = brief.topActions.filter((a) => a.severity === 'high').length;
  return { answer: `${brief.storeCount} workspaces · ${money(brief.totals.revenue7d, cur)} this week · ${hi} need you today. Try "best week", "what needs me", or a workspace name.` };
}

module.exports = { ask };
