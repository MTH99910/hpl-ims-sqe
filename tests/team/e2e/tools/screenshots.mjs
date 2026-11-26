// Evidence screenshots of tools that have no automated test report of their own.
//   cd tests/team/e2e && node tools/screenshots.mjs sonar|github [prUrls...]
import { chromium } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const OUT = path.join(ROOT, 'reports/screenshots');
const what = process.argv[2] || 'sonar';
const browser = await chromium.launch({ channel: 'chromium' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const shot = async (name, url, waitText) => {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  if (waitText) await page.getByText(waitText).first().waitFor({ timeout: 30000 });
  for (const t of ['Dismiss', 'Overall Code']) { const b = page.getByText(t, { exact: true }).first(); if (await b.isVisible().catch(() => false)) { await b.click(); await page.waitForTimeout(800); } }
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT, name), fullPage: true });
  console.log('saved', name);
};
if (what === 'sonar') {
  await page.goto('http://localhost:9000/sessions/new');
  await page.fill('input[name="login"], #login-input', 'admin');
  await page.fill('input[name="password"], #password-input', process.env.SONAR_PASS);
  await page.keyboard.press('Enter');
  await page.waitForURL(u => !u.pathname.includes('sessions'), { timeout: 30000 });
  await shot('sonar-baseline-dashboard.png', 'http://localhost:9000/dashboard?id=hpl-ims-baseline');
  await shot('sonar-current-dashboard.png', 'http://localhost:9000/dashboard?id=hpl-ims-sqe');
  await shot('sonar-baseline-issues.png', 'http://localhost:9000/project/issues?id=hpl-ims-baseline&resolved=false');
  await shot('sonar-current-measures-complexity.png', 'http://localhost:9000/component_measures?id=hpl-ims-sqe&metric=complexity&view=list');
  await shot('sonar-function-complexity-clean_quantity_issued.png', 'http://localhost:9000/project/issues?id=hpl-ims-sqe&rules=python%3AFunctionComplexity&files=requisition%2Fforms.py&resolved=true');
} else {
  await shot('github-issues.png', 'https://github.com/MTH99910/hpl-ims-sqe/issues?q=is%3Aissue');
  await shot('github-actions-runs.png', 'https://github.com/MTH99910/hpl-ims-sqe/actions');
  for (const [i, u] of process.argv.slice(3).entries()) await shot(`github-extra-${i + 1}.png`, u);
}
await browser.close();
