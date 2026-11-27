// Lighthouse (accessibility, best-practices, SEO) on each use case's key screen, WHILE LOGGED IN.
// Login script: Playwright logs in through the real login form in a Chromium started with a
// remote-debugging port; Lighthouse then audits pages in that same browser (same session cookie).
//
//   node a11y/lighthouse.mjs <label>        (label = before | after)   needs the E2E server on :8010
import { chromium } from '@playwright/test';
import lighthouse from 'lighthouse';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, '../../../..');
const LABEL = process.argv[2] || 'before';
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8010';
const OUT = path.join(ROOT, 'reports/a11y', LABEL);
const PORT = 9333;
const PY = path.join(ROOT, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const DB = path.join(here, '../helpers/db_state.py');
const pk = purpose => JSON.parse(execFileSync(PY, [DB, 'state', purpose], { cwd: ROOT }).toString()).pk;

execFileSync(PY, [DB, 'reset'], { cwd: ROOT });
const SCREENS = [
  { name: 'hod-approval', user: 'hod_it', url: `/requisition/${pk('Pens for new IT interns batch')}/hod-approval/` },   // UC-01, UC-02
  { name: 'issue-items', user: 'admin', url: `/requisition/${pk('Pens for IT helpdesk counter')}/issue/` },            // UC-03, UC-04
];

fs.mkdirSync(OUT, { recursive: true });
const summary = [];
for (const s of SCREENS) {
  // persistent (default) context: Lighthouse opens its tab in the same profile, so it shares the session
  const profile = fs.mkdtempSync(path.join(ROOT, 'reports/tmp/lh-profile-'));
  const browser = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
                                                                     args: [`--remote-debugging-port=${PORT}`] });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto(`${BASE}/login/`);
  await page.fill('#username', s.user);
  await page.fill('#password', 'Test@12345');
  await page.click('button[type=submit]');
  await page.waitForURL(u => !u.pathname.startsWith('/login'));
  const result = await lighthouse(`${BASE}${s.url}`, {
    port: PORT, output: ['html', 'json'], logLevel: 'error', disableStorageReset: true,
    onlyCategories: ['accessibility', 'best-practices', 'seo'], formFactor: 'desktop',
    screenEmulation: { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false },
  });
  const [html, json] = result.report;
  fs.writeFileSync(path.join(OUT, `lighthouse-${s.name}.html`), html);
  fs.writeFileSync(path.join(OUT, `lighthouse-${s.name}.json`), json);
  const lhr = result.lhr;
  const failed = Object.values(lhr.audits).filter(a => a.score !== null && a.score < 1 && a.scoreDisplayMode !== 'notApplicable' && a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'manual');
  const row = { screen: s.name, url: s.url, finalUrl: lhr.finalDisplayedUrl,
    accessibility: Math.round(lhr.categories.accessibility.score * 100),
    bestPractices: Math.round(lhr.categories['best-practices'].score * 100),
    seo: Math.round(lhr.categories.seo.score * 100),
    failedAudits: failed.map(a => a.id) };
  if (lhr.finalDisplayedUrl.includes('/login/')) throw new Error(`not logged in - audited ${lhr.finalDisplayedUrl}`);
  summary.push(row);
  console.log(JSON.stringify(row));
  await browser.close();
}
fs.writeFileSync(path.join(OUT, 'lighthouse-summary.json'), JSON.stringify(summary, null, 2));
