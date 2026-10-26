'use strict';
/**
 * Nestral — Shopify data layer
 * Pulls a 30-day snapshot per store from the Shopify Admin API, or returns a
 * realistic seeded MOCK snapshot when a store has no real token yet (so the
 * product is fully runnable/demoable before any credentials exist).
 *
 * A store with token === 'mock' (or config.demo === true) → mock snapshot.
 * Zero dependencies. Node 18+ (built-in fetch).
 */

const API_VERSION = '2024-10';
const DAY = 864e5;

// ---- tiny seeded RNG so the demo is stable & varied per store ----
function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function mulberry32(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

async function jget(url, headers) {
  const r = await fetch(url, { headers });
  const text = await r.text();
  let json; try { json = JSON.parse(text); } catch { json = null; }
  if (!r.ok) { const e = new Error(`HTTP ${r.status}`); e.status = r.status; e.body = json || text; throw e; }
  return json;
}

// ---- metric shape every store resolves to ----
function emptyMetrics() {
  return {
    currency: 'USD',
    ordersToday: 0, revenueToday: 0,
    orders7d: 0, revenue7d: 0,
    ordersPrev7d: 0, revenuePrev7d: 0,
    orders30: 0, revenue30: 0,
    unfulfilled: 0, pendingPayment: 0,
    outOfStock: 0, lowStock: 0,
    lastOrderAgeDays: null,
  };
}

function trendPct(cur, prev) {
  if (!prev) return cur ? 100 : 0;
  return Math.round(((cur - prev) / prev) * 100);
}

// ============================ REAL ============================
async function fetchReal(store) {
  const H = { 'X-Shopify-Access-Token': store.token, 'Content-Type': 'application/json' };
  const base = `https://${store.domain}/admin/api/${API_VERSION}`;
  const now = Date.now();
  const dayStart = new Date(); dayStart.setHours(0, 0, 0, 0);
  const min30 = new Date(now - 30 * DAY).toISOString();

  const m = emptyMetrics();

  // Orders (last 30d)
  const od = await jget(`${base}/orders.json?status=any&created_at_min=${encodeURIComponent(min30)}&fields=created_at,total_price,currency,financial_status,fulfillment_status&limit=250`, H);
  const orders = od.orders || [];
  const sum = (arr) => arr.reduce((a, o) => a + parseFloat(o.total_price || 0), 0);
  const inWindow = (o, lo, hi) => { const t = new Date(o.created_at).getTime(); return t >= lo && t < hi; };

  m.currency = orders[0]?.currency || 'USD';
  m.orders30 = orders.length; m.revenue30 = sum(orders);
  const today = orders.filter((o) => new Date(o.created_at) >= dayStart);
  m.ordersToday = today.length; m.revenueToday = sum(today);
  const w7 = orders.filter((o) => inWindow(o, now - 7 * DAY, now));
  const wp7 = orders.filter((o) => inWindow(o, now - 14 * DAY, now - 7 * DAY));
  m.orders7d = w7.length; m.revenue7d = sum(w7);
  m.ordersPrev7d = wp7.length; m.revenuePrev7d = sum(wp7);
  m.unfulfilled = orders.filter((o) => o.fulfillment_status == null && o.financial_status !== 'voided' && o.financial_status !== 'refunded').length;
  m.pendingPayment = orders.filter((o) => o.financial_status === 'pending' || o.financial_status === 'authorized').length;
  if (orders.length) {
    const latest = Math.max(...orders.map((o) => new Date(o.created_at).getTime()));
    m.lastOrderAgeDays = Math.floor((now - latest) / DAY);
  }

  // Inventory (active products)
  try {
    const pd = await jget(`${base}/products.json?status=active&fields=id,title,variants&limit=250`, H);
    for (const p of pd.products || []) {
      for (const v of p.variants || []) {
        if (v.inventory_management == null) continue; // not tracked
        const q = Number(v.inventory_quantity);
        if (Number.isFinite(q)) { if (q <= 0) m.outOfStock++; else if (q <= 5) m.lowStock++; }
      }
    }
  } catch { /* inventory optional */ }

  return { label: store.label || store.domain, domain: store.domain, ok: true, mock: false, metrics: m };
}

// ============================ MOCK ============================
function fetchMock(store) {
  const rnd = mulberry32(hash(store.label || store.domain || 'store'));
  const m = emptyMetrics();
  const tier = rnd(); // store "health archetype"
  const aov = 40 + Math.floor(rnd() * 160);

  // baseline daily orders
  let perDay = Math.floor(rnd() * 9);
  let archetype = 'healthy';
  if (tier < 0.2) { perDay = 0; archetype = 'stalled'; }           // no sales
  else if (tier < 0.4) { archetype = 'dropping'; }                  // declining
  else if (tier < 0.55) { archetype = 'spiking'; }                  // surging

  const mk = (n) => Math.max(0, Math.round(n));
  m.orders7d = mk(perDay * 7 * (archetype === 'spiking' ? 1.8 : 1));
  m.ordersPrev7d = mk(perDay * 7 * (archetype === 'dropping' ? 1.7 : archetype === 'spiking' ? 0.7 : 1));
  m.revenue7d = m.orders7d * aov; m.revenuePrev7d = m.ordersPrev7d * aov;
  m.orders30 = mk(perDay * 30); m.revenue30 = m.orders30 * aov;
  m.ordersToday = archetype === 'stalled' ? 0 : mk(perDay * (0.5 + rnd()));
  m.revenueToday = m.ordersToday * aov;
  m.unfulfilled = archetype === 'stalled' ? 0 : Math.floor(rnd() * 14);
  m.pendingPayment = Math.floor(rnd() * 3);
  m.outOfStock = rnd() < 0.4 ? 1 + Math.floor(rnd() * 3) : 0;
  m.lowStock = rnd() < 0.5 ? 1 + Math.floor(rnd() * 4) : 0;
  m.lastOrderAgeDays = archetype === 'stalled' ? 7 + Math.floor(rnd() * 20) : 0;
  m.currency = 'USD';

  return { label: store.label || store.domain || 'Store', domain: store.domain || 'demo.myshopify.com', ok: true, mock: true, metrics: m };
}

// ============================ public ============================
async function fetchStoreSnapshot(store, opts = {}) {
  const isMock = opts.demo || !store.token || store.token === 'mock';
  if (isMock) return fetchMock(store);
  try {
    return await fetchReal(store);
  } catch (e) {
    return { label: store.label || store.domain, domain: store.domain, ok: false, mock: false,
      error: e.status === 401 ? 'Bad/expired Admin token — reconnect' : String(e.message || e) };
  }
}

module.exports = { fetchStoreSnapshot, trendPct, API_VERSION };
