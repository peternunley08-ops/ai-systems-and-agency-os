#!/usr/bin/env node
'use strict';
/**
 * Nestral — CLI
 *   node index.js brief [--send]   build today's brief, save it, (optionally) deliver it
 *   node index.js ask "best week?" ask your portfolio a question
 *   node index.js serve            launch the cockpit (http://localhost:7711)
 *   node index.js watch [--now]    run as a daemon: deliver the brief every day at schedule.time
 * Zero dependencies. Node 18+.
 */
const fs = require('fs');
const path = require('path');
const { loadConfig, gather, ROOT } = require('./src/nestral');
const { buildBrief, renderMarkdown, renderText } = require('./src/brief');
const history = require('./src/history');
const { send } = require('./src/deliver');
const { ask } = require('./src/ask');

async function makeBrief() {
  const cfg = loadConfig();
  const brief = buildBrief(await gather(cfg));
  brief.__cfg = cfg;
  return brief;
}

async function cmdBrief(args) {
  const brief = await makeBrief();
  if (args.includes('--json')) { console.log(JSON.stringify(brief, null, 2)); return; }
  console.log('\n' + renderText(brief) + '\n');
  const dir = path.join(ROOT, 'briefs'); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${brief.date}.md`), renderMarkdown(brief));
  history.record(brief);
  console.log(`  saved → briefs/${brief.date}.md`);
  if (args.includes('--send')) {
    const res = await send(brief, brief.__cfg.deliver);
    if (!res.length) console.log('  (no delivery channels enabled — see nestral.config.json → deliver)');
    for (const r of res) console.log(`  ${r.channel}: ${r.ok ? '✓ ' + r.reason : (r.dryRun ? 'dry-run — ' + r.reason : '✗ ' + r.reason)}`);
  }
  if (brief.anyMock) console.log('  (demo data — add real workspaces in nestral.config.json to go live)');
}

async function cmdAsk(args) {
  const q = args.filter((a) => !a.startsWith('--')).join(' ');
  const brief = await makeBrief();
  console.log('\n  ' + ask(q, brief).answer + '\n');
}

function msUntil(hhmm) {
  const [h, m] = String(hhmm || '06:30').split(':').map(Number);
  const now = new Date(); const next = new Date(now);
  next.setHours(h || 0, m || 0, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next - now;
}

async function runScheduled() {
  const brief = await makeBrief();
  history.record(brief);
  const dir = path.join(ROOT, 'briefs'); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${brief.date}.md`), renderMarkdown(brief));
  const res = await send(brief, brief.__cfg.deliver);
  const stamp = new Date().toLocaleString();
  console.log(`[${stamp}] brief sent: ${res.map((r) => r.channel + (r.ok ? '✓' : '✗')).join(' ') || '(no channels)'}`);
}

async function cmdWatch(args) {
  const cfg = loadConfig();
  const time = (cfg.schedule && cfg.schedule.time) || '06:30';
  console.log(`\n  🪺 Nestral watch — daily brief at ${time}`);
  if (args.includes('--now')) { console.log('  running once now…'); await runScheduled(); }
  const loop = () => {
    const wait = msUntil(time);
    console.log(`  next brief in ${Math.round(wait / 60000)} min (${new Date(Date.now() + wait).toLocaleString()})`);
    setTimeout(async () => { try { await runScheduled(); } catch (e) { console.error('  brief failed:', e.message); } loop(); }, wait);
  };
  loop();
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2);
  if (cmd === 'serve') return require('./src/server').start();
  if (cmd === 'ask') return cmdAsk(args);
  if (cmd === 'watch') return cmdWatch(args);
  if (cmd === 'brief' || !cmd) return cmdBrief(args || []);
  console.log('Usage: node index.js [brief [--send] | ask "<q>" | serve | watch [--now]]');
}
main().catch((e) => { console.error('Nestral error:', e.message); process.exit(1); });
