/**
 * Doc section 3 - full axe-core scan (WCAG 2.0/2.1 A + AA) of each use case's key screen.   owner: Member B
 * Results are written to reports/a11y/<label>/axe-<screen>.json (label = before | after).
 * The scan RECORDS violations (it does not fail the build on them); triage is in docs/16_a11y_findings.md.
 */
import fs from 'fs';
import path from 'path';
import AxeBuilder from '@axe-core/playwright';
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

const LABEL = process.env.A11Y_LABEL || 'before';
const OUT = path.resolve(__dirname, '../../../../reports/a11y', LABEL);

const SCREENS = [
  { name: 'hod-approval', user: 'hod_it', url: () => `/requisition/${dbState(SEED.pendingIT).pk}/hod-approval/` },
  { name: 'issue-items', user: 'admin', url: () => `/requisition/${dbState(SEED.authorized).pk}/issue/` },
  { name: 'hod-dashboard', user: 'hod_it', url: () => '/requisition/hod/' },
  { name: 'admin-dashboard', user: 'admin', url: () => '/requisition/admin/' },
  { name: 'login', user: null, url: () => '/login/' },
];

for (const s of SCREENS) {
  test(`AXE ${s.name}`, async ({ page }) => {
    if (s.user) await login(page, s.user);
    await page.goto(s.url());
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze();
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, `axe-${s.name}.json`), JSON.stringify(res, null, 2));
    await page.screenshot({ path: path.join(OUT, `axe-${s.name}.png`), fullPage: true });
    const summary = res.violations.map(v => `${v.id} [${v.impact}] x${v.nodes.length}`);
    console.log(`${s.name}: ${res.violations.length} violation rules -> ${summary.join(', ')}`);
    expect(res.passes.length).toBeGreaterThan(0);   // scan really ran
  });
}
