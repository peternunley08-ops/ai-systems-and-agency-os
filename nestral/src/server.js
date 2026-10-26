'use strict';
/**
 * Nestral — local cockpit server. Zero dependencies. Node 18+.
 *   GET  /              dashboard
 *   GET  /api/brief     today's brief (totals, stores, topActions)
 *   GET  /api/history   last 14 days of totals (sparkline)
 *   GET  /api/ask?q=    ask your portfolio a question
 *   GET  /api/config    sanitized config (no secrets) + available sources
 *   POST /api/config    { action: addWorkspace|removeWorkspace|setDeliver|setSchedule|setDemo, ... }
 *   GET  /health
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { loadConfig, saveConfig, gather, normalize, CONFIG_FILE } = require('./nestral');
const { buildBrief } = require('./brief');
const { ask } = require('./ask');
const { sources } = require('./connectors');
const history = require('./history');

const PORT = process.env.NESTRAL_PORT ? Number(process.env.NESTRAL_PORT) : 7711;
const HOST = '127.0.0.1';
const PAGE = path.join(__dirname, '..', 'public', 'index.html');

let cache = { at: 0, data: null };
async function snapshot() {
  if (cache.data && Date.now() - cache.at < 60000) return cache.data;
  const brief = buildBrief(await gather(loadConfig()));
  cache = { at: Date.now(), data: brief };
  return brief;
}
const bust = () => (cache = { at: 0, data: null });

function send(res, code, b, type) {
  res.writeHead(code, { 'Content-Type': type, 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' });
  res.end(b);
}
const json = (res, code, obj) => send(res, code, JSON.stringify(obj), 'application/json');
function body(req) { return new Promise((r) => { let d = ''; req.on('data', (c) => (d += c)); req.on('end', () => { try { r(JSON.parse(d || '{}')); } catch { r({}); } }); }); }

function sanitizeConfig(cfg) {
  return {
    demo: !!cfg.demo, usingDemo: !!cfg.__usingDemo, schedule: cfg.schedule || { time: '06:30' },
    sources: sources(),
    workspaces: (cfg.workspaces || []).map((w) => ({ source: w.source, label: w.label, domain: w.domain || '', hasToken: !!(w.token && w.token !== 'mock'), mock: w.token === 'mock' })),
    deliver: {
      telegram: { enabled: !!cfg.deliver?.telegram?.enabled, hasToken: !!cfg.deliver?.telegram?.botToken, chatId: cfg.deliver?.telegram?.chatId || '' },
      webhook: { enabled: !!cfg.deliver?.webhook?.enabled, url: cfg.deliver?.webhook?.url || '' },
      email: { enabled: !!cfg.deliver?.email?.enabled, to: cfg.deliver?.email?.to || '' },
    },
  };
}

async function handleConfigPost(b) {
  let cfg = fs.existsSync(CONFIG_FILE) ? normalize(JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))) : normalize(loadConfig());
  if (cfg.__usingDemo && b.action === 'addWorkspace') cfg.workspaces = []; // first real add replaces the demo flock
  switch (b.action) {
    case 'addWorkspace': {
      const w = b.workspace || {};
      if (!w.label) throw new Error('label required');
      cfg.workspaces = (cfg.workspaces || []).filter((x) => x.label !== w.label);
      cfg.workspaces.push({ source: w.source || 'shopify', label: w.label, domain: w.domain || '', token: w.token || 'mock' });
      cfg.demo = false; break;
    }
    case 'removeWorkspace':
      cfg.workspaces = (cfg.workspaces || []).filter((x) => x.label !== b.label); break;
    case 'setDeliver':
      cfg.deliver = { ...cfg.deliver, ...b.deliver }; break;
    case 'setSchedule':
      cfg.schedule = { ...cfg.schedule, ...b.schedule }; break;
    case 'setDemo':
      cfg.demo = !!b.demo; break;
    default: throw new Error('unknown action: ' + b.action);
  }
  saveConfig(cfg); bust();
  return sanitizeConfig(loadConfig());
}

function start() {
  const server = http.createServer(async (req, res) => {
    try {
      const u = new URL(req.url, `http://${req.headers.host}`);
      const p = u.pathname;
      if (req.method === 'OPTIONS') return send(res, 204, '', 'text/plain');
      if (p === '/health') return send(res, 200, 'ok', 'text/plain');
      if (p === '/api/brief') return json(res, 200, await snapshot());
      if (p === '/api/history') return json(res, 200, history.read(14));
      if (p === '/api/ask') return json(res, 200, ask(u.searchParams.get('q') || '', await snapshot()));
      if (p === '/api/config' && req.method === 'GET') return json(res, 200, sanitizeConfig(loadConfig()));
      if (p === '/api/config' && req.method === 'POST') { try { return json(res, 200, await handleConfigPost(await body(req))); } catch (e) { return json(res, 400, { error: String(e.message || e) }); } }
      if (p === '/' || p === '/index.html') return send(res, 200, fs.readFileSync(PAGE, 'utf8'), 'text/html; charset=utf-8');
      return json(res, 404, { error: 'not found' });
    } catch (e) { return json(res, 500, { error: String(e.message || e) }); }
  });
  server.listen(PORT, HOST, () => {
    console.log(`\n  🪺 Nestral cockpit running`);
    console.log(`  → http://localhost:${PORT}\n  Leave this window open. Close it to stop.\n`);
  });
  return server;
}

module.exports = { start, snapshot, PORT };
