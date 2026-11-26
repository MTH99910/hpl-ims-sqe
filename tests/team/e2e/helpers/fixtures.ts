import { test as base, expect, Page } from '@playwright/test';
import { execFileSync } from 'child_process';
import path from 'path';

const ROOT = path.resolve(__dirname, '../../../..');
const PY = path.join(ROOT, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const DB = path.join(__dirname, 'db_state.py');
export const PASSWORD = 'Test@12345';

export type ReqState = {
  pk: number; number: string; status: string; hod_approver: string | null; issuer: string | null;
  rejection_reason: string | null; sent_back_reason: string | null; notes: string | null;
  lines: { code: string; requested: number; issued: number; stock: number }[];
  outward: { code: string; change: number; balance_after: number }[];
  notifications: string[];
};

/** Persisted state of a seeded requisition (found by its unique purpose) - used for postconditions. */
export function dbState(purpose: string): ReqState {
  return JSON.parse(execFileSync(PY, [DB, 'state', purpose], { cwd: ROOT }).toString());
}

export function resetDb() {
  execFileSync(PY, [DB, 'reset'], { cwd: ROOT });
}

export async function login(page: Page, username: string) {
  await page.goto('/login/');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in|login/i }).click();
  await expect(page).not.toHaveURL(/\/login\//);
}

export async function logout(page: Page) {
  await page.goto('/logout/');
}

/** Every test starts from the same seeded data. */
export const test = base.extend<{ fresh: void }>({
  fresh: [async ({}, use) => { resetDb(); await use(); }, { auto: true }],
});
export { expect };

// Seeded requisitions (scripts/team/seed_team.py) - unique purposes
export const SEED = {
  pendingIT: 'Pens for new IT interns batch',            // ST001 x4, user_it_1
  pendingIT2: 'Server room supplies restock',            // ST001 x6 + HK002 x10
  pendingHR: 'Pens for HR onboarding desk',              // HR department
  authorized: 'Pens for IT helpdesk counter',            // ST001 x4 (stock 10)
  authorizedMulti: 'Lab cleaning and stationery',        // ST001 x3 + HK002 x5
  authorizedPaper: 'Printer paper for IT reports',       // ST002 x1 (stock 1)
  authorizedShort: 'Paper bulk order for training',      // ST002 x3 but stock 1
  issued: 'Gloves already issued earlier',
};
