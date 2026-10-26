'use strict';
/**
 * Nestral — core: load config, gather every workspace's snapshot in parallel.
 * A "workspace" is anything you connect (a store, a Stripe account, …) and is
 * routed to the right connector by its `source`. Zero dependencies.
 */
const fs = require('fs');
const path = require('path');
const { fetchWorkspace } = require('./connectors');

const ROOT = path.join(__dirname, '..');
const CONFIG_FILE = path.join(ROOT, 'nestral.config.json');
const EXAMPLE_FILE = path.join(ROOT, 'nestral.config.example.json');

function loadConfig() {
  for (const f of [CONFIG_FILE, EXAMPLE_FILE]) {
    if (fs.existsSync(f)) {
      const cfg = JSON.parse(fs.readFileSync(f, 'utf8'));
      cfg.__source = path.basename(f);
      cfg.__isExample = f.endsWith('example.json');
      return normalize(cfg);
    }
  }
  return normalize({ demo: true, workspaces: [], __source: '(none)', __isExample: true });
}

// Accept both new `workspaces` and legacy `stores`; fill demo flock if empty.
function normalize(cfg) {
  let ws = cfg.workspaces || cfg.stores || [];
  if (!ws.length) { ws = DEMO_WORKSPACES; cfg.__usingDemo = true; }
  cfg.workspaces = ws.map((w) => ({ source: w.source || 'shopify', ...w }));
  cfg.deliver = cfg.deliver || {};
  cfg.schedule = cfg.schedule || { time: '06:30' };
  return cfg;
}

function saveConfig(cfg) {
  const out = {
    demo: !!cfg.demo,
    schedule: cfg.schedule || { time: '06:30' },
    deliver: cfg.deliver || {},
    workspaces: (cfg.workspaces || []).map(({ source, label, domain, token }) => ({ source, label, domain, token })),
  };
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(out, null, 2));
  return out;
}

async function gather(cfg) {
  const demo = cfg.demo || cfg.__isExample || cfg.__usingDemo;
  return Promise.all((cfg.workspaces || []).map((w) => fetchWorkspace(w, { demo })));
}

// Pete's real brands — the demo portfolio, so the first run feels real.
const DEMO_WORKSPACES = [
  { source: 'shopify', label: 'Cariven', domain: 'cariven.myshopify.com', token: 'mock' },
  { source: 'shopify', label: 'Cinderlux', domain: 'cinderlux.myshopify.com', token: 'mock' },
  { source: 'shopify', label: 'Lunthera', domain: 'lunthera.myshopify.com', token: 'mock' },
  { source: 'shopify', label: 'Vertabliss', domain: 'vertabliss.myshopify.com', token: 'mock' },
  { source: 'shopify', label: 'Northstar Paws', domain: 'northstar-paws.myshopify.com', token: 'mock' },
  { source: 'stripe', label: 'Payments (Stripe)', token: 'mock' },
];

module.exports = { loadConfig, saveConfig, gather, normalize, ROOT, CONFIG_FILE, DEMO_WORKSPACES };
