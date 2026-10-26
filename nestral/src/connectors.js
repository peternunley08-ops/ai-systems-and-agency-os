'use strict';
/**
 * Nestral — connector registry.
 * A workspace declares a `source`; the registry routes it to a fetcher that
 * returns a normalized snapshot (see shopify.js for the metric shape). This is
 * what makes "connect anything" real — add a file here and it joins the brief.
 * Zero dependencies.
 */
const { fetchStoreSnapshot } = require('./shopify');

const DAY = 864e5;
function hash(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}
function rng(seed){let a=hash(seed);return()=>{a|=0;a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};}

// ---- Stripe connector (real skeleton + seeded mock) ----
async function fetchStripe(ws, opts = {}) {
  const label = ws.label || 'Stripe';
  if (opts.demo || !ws.token || ws.token === 'mock') {
    const r = rng('stripe:' + label);
    const aov = 30 + Math.floor(r() * 120);
    const per = Math.floor(r() * 7);
    const drop = r() < 0.3;
    const m = {
      currency: 'USD',
      ordersToday: Math.round(per * (0.5 + r())), revenueToday: 0,
      orders7d: per * 7, revenue7d: per * 7 * aov,
      ordersPrev7d: Math.round(per * 7 * (drop ? 1.7 : 1)), revenuePrev7d: 0,
      orders30: per * 30, revenue30: per * 30 * aov,
      unfulfilled: 0, pendingPayment: Math.floor(r() * 4),
      outOfStock: 0, lowStock: 0, lastOrderAgeDays: per ? 0 : 5 + Math.floor(r() * 10),
    };
    m.revenueToday = m.ordersToday * aov; m.revenuePrev7d = m.ordersPrev7d * aov;
    return { label, domain: 'stripe', ok: true, mock: true, metrics: m };
  }
  // real: Stripe Balance/Charges API (read-only restricted key)
  try {
    const since = Math.floor((Date.now() - 7 * DAY) / 1000);
    const r = await fetch(`https://api.stripe.com/v1/charges?limit=100&created[gte]=${since}`, {
      headers: { Authorization: 'Bearer ' + ws.token },
    });
    if (!r.ok) throw new Error('HTTP ' + r.status + (r.status === 401 ? ' (bad key)' : ''));
    const j = await r.json();
    const charges = (j.data || []).filter(c => c.paid && !c.refunded);
    const rev = charges.reduce((a, c) => a + (c.amount || 0), 0) / 100;
    return { label, domain: 'stripe', ok: true, mock: false, metrics: {
      currency: (charges[0]?.currency || 'usd').toUpperCase(),
      ordersToday: 0, revenueToday: 0, orders7d: charges.length, revenue7d: rev,
      ordersPrev7d: 0, revenuePrev7d: 0, orders30: 0, revenue30: 0,
      unfulfilled: 0, pendingPayment: 0, outOfStock: 0, lowStock: 0, lastOrderAgeDays: charges.length ? 0 : null,
    } };
  } catch (e) {
    return { label, domain: 'stripe', ok: false, mock: false, error: String(e.message || e) };
  }
}

const REGISTRY = {
  shopify: { label: 'Shopify', fetch: (ws, opts) => fetchStoreSnapshot(ws, opts) },
  stripe:  { label: 'Stripe',  fetch: fetchStripe },
};

function sources() { return Object.keys(REGISTRY); }

async function fetchWorkspace(ws, opts = {}) {
  const src = (ws.source || 'shopify').toLowerCase();
  const c = REGISTRY[src];
  if (!c) return { label: ws.label || ws.domain || src, ok: false, error: `unknown source: ${src}` };
  const snap = await c.fetch(ws, opts);
  snap.source = src;
  return snap;
}

module.exports = { fetchWorkspace, sources, REGISTRY };
