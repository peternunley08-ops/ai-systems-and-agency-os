'use strict';
/**
 * Nestral — delivery. Sends the morning brief to where the operator actually is.
 *   - telegram : real, via the Bot API (needs botToken + chatId)
 *   - webhook  : real, POSTs the brief JSON (e.g. to a Zapier/Make/Apps-Script that emails)
 *   - console/file are handled by the caller (index.js)
 * Honest dry-run: with no creds, returns the composed message so it's testable.
 * Zero dependencies (Node 18+ global fetch).
 */
const { renderText, renderMarkdown } = require('./brief');

async function send(brief, deliver = {}) {
  const results = [];
  const text = renderText(brief);

  // ---- Telegram ----
  const tg = deliver.telegram || {};
  if (tg.enabled) {
    if (!tg.botToken || !tg.chatId) {
      results.push({ channel: 'telegram', ok: false, dryRun: true, reason: 'no botToken/chatId', preview: text.slice(0, 280) });
    } else {
      try {
        const r = await fetch(`https://api.telegram.org/bot${tg.botToken}/sendMessage`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: tg.chatId, text, disable_web_page_preview: true }),
        });
        const j = await r.json().catch(() => ({}));
        results.push({ channel: 'telegram', ok: !!j.ok, reason: j.ok ? 'sent' : (j.description || 'HTTP ' + r.status) });
      } catch (e) { results.push({ channel: 'telegram', ok: false, reason: String(e.message || e) }); }
    }
  }

  // ---- Webhook ----
  const wh = deliver.webhook || {};
  if (wh.enabled) {
    if (!wh.url) {
      results.push({ channel: 'webhook', ok: false, dryRun: true, reason: 'no url' });
    } else {
      try {
        const r = await fetch(wh.url, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brief, markdown: renderMarkdown(brief), text }),
        });
        results.push({ channel: 'webhook', ok: r.ok, reason: r.ok ? 'posted' : 'HTTP ' + r.status });
      } catch (e) { results.push({ channel: 'webhook', ok: false, reason: String(e.message || e) }); }
    }
  }

  // ---- Email (note) ----
  // Native SMTP would add deps; the supported path is webhook → an Apps Script / Zapier that emails.
  // (The Northstar Apps Script pattern fits perfectly.)
  const em = deliver.email || {};
  if (em.enabled) results.push({ channel: 'email', ok: false, reason: 'route via webhook → Apps Script/Zapier (see SETUP)' });

  return results;
}

module.exports = { send };
