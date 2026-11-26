/**
 * Doc section 4 - access decisions verified through the real UI/HTTP (Playwright).   owner: Member A
 * Each check records role, action, expected, observed and evidence (screenshot + HTTP status +
 * persisted state) into reports/security/access_matrix.json.
 *
 * Expected results come from the README's separation of duties (test basis assumption A1):
 * only HODs approve (own department only), only Admins issue.
 */
import fs from 'fs';
import path from 'path';
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

const OUT = path.resolve(__dirname, '../../../../reports/security');
const results: any[] = [];

type Check = { id: string; role: string; action: string; expected: 'allow' | 'deny'; purpose: string;
               url: (pk: number) => string; defect?: string; };

const CHECKS: Check[] = [
  { id: 'SEC-01', role: 'hod_it', action: 'Open approval screen of own-department pending requisition', expected: 'allow',
    purpose: SEED.pendingIT, url: pk => `/requisition/${pk}/hod-approval/` },
  { id: 'SEC-02', role: 'hod_it', action: 'Open approval screen of another department\'s requisition', expected: 'deny',
    purpose: SEED.pendingHR, url: pk => `/requisition/${pk}/hod-approval/` },
  { id: 'SEC-03', role: 'hod_it', action: 'Open the Issue Items screen of an authorized requisition', expected: 'deny',
    purpose: SEED.authorized, url: pk => `/requisition/${pk}/issue/`, defect: 'F3' },
  { id: 'SEC-04', role: 'admin', action: 'Open the Issue Items screen of an authorized requisition', expected: 'allow',
    purpose: SEED.authorized, url: pk => `/requisition/${pk}/issue/` },
  { id: 'SEC-05', role: 'admin', action: 'Open the HOD approval screen of a pending requisition', expected: 'deny',
    purpose: SEED.pendingIT, url: pk => `/requisition/${pk}/hod-approval/`, defect: 'F4' },
  { id: 'SEC-06', role: 'user_it_1', action: 'Open the Issue Items screen (initiator)', expected: 'deny',
    purpose: SEED.authorized, url: pk => `/requisition/${pk}/issue/`, defect: 'F3' },
  { id: 'SEC-07', role: 'anonymous', action: 'Open the Issue Items screen without logging in', expected: 'deny',
    purpose: SEED.authorized, url: pk => `/requisition/${pk}/issue/` },
];

test.describe('Access matrix (HOD vs Admin)', () => {
  for (const c of CHECKS) {
    test(`${c.id} ${c.role}: ${c.action} -> expected ${c.expected}`, async ({ page }, info) => {
      if (c.defect) test.fail(true, `${c.defect}: access is granted although the role must be denied`);
      const req = dbState(c.purpose);
      if (c.role !== 'anonymous') await login(page, c.role);
      const resp = await page.goto(c.url(req.pk));
      const status = resp!.status();
      const onLogin = /\/login\//.test(page.url());
      const observed = status === 200 && !onLogin ? 'allow' : 'deny';
      const shot = path.join(OUT, `${c.id}.png`);
      fs.mkdirSync(OUT, { recursive: true });
      await page.screenshot({ path: shot, fullPage: true });
      await info.attach(`${c.id} evidence`, { path: shot, contentType: 'image/png' });
      results.push({ id: c.id, role: c.role, action: c.action, expected: c.expected, observed,
                     http_status: status, final_url: page.url().replace(/^https?:\/\/[^/]+/, ''),
                     evidence: `reports/security/${c.id}.png`, defect: c.defect ?? null,
                     verdict: observed === c.expected ? 'PASS' : 'FAIL' });
      expect(observed).toBe(c.expected);
    });
  }

  test('SEC-08 hod_it actually issues stock through the unprotected view (impact of F3)', async ({ page }) => {
    test.fail(true, 'F3: an HOD can complete an issue');
    const before = dbState(SEED.authorized);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/issue/`);
    if (await page.getByRole('spinbutton').count()) {
      await page.getByRole('spinbutton').first().fill('3');
      await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
    }
    const after = dbState(SEED.authorized);
    results.push({ id: 'SEC-08', role: 'hod_it', action: 'Submit an issue of 3 units', expected: 'deny',
                   observed: after.status === 'issued' ? 'allow' : 'deny', http_status: null,
                   final_url: page.url().replace(/^https?:\/\/[^/]+/, ''), evidence: `DB: status=${after.status}, issuer=${after.issuer}, stock=${after.lines[0].stock}`,
                   defect: 'F3', verdict: after.status === 'issued' ? 'FAIL' : 'PASS' });
    expect(after.status).toBe('authorized');
  });

  test.afterAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, 'access_matrix.json'), JSON.stringify(results, null, 2));
  });
});
