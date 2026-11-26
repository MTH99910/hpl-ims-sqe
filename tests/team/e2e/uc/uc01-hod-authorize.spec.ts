/**
 * UC-01  HOD authorizes a pending requisition (WF1)            owner: Member A
 * Preconditions: requisition pending_hod from the HOD's department; HOD logged in; ST001 stock 10.
 * Postconditions (success): status authorized, hod_approver = HOD, initiator + every Admin notified,
 *                           stock unchanged.  (failure): status still pending_hod, no notifications.
 */
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

async function authorize(page, notes?: string) {
  await page.locator('#action_authorized').check();
  if (notes) await page.getByLabel('Additional Notes').fill(notes);
  await page.getByRole('button', { name: 'Submit Decision' }).click();
}

test.describe('UC-01 HOD authorizes a requisition', () => {
  test('UC-01 main: authorize from the HOD dashboard', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await expect(page).toHaveURL(/\/requisition\/hod\//);
    const row = page.getByRole('row', { name: new RegExp(before.number) });
    await row.getByRole('link', { name: 'Review' }).click();
    await authorize(page);
    await expect(page.getByRole('alert')).toContainText(`Requisition ${before.number} has been approved.`);
    // left the pending queue (it now appears only under 'recent approvals', without a Review action)
    await expect(page.getByRole('row', { name: new RegExp(before.number) }).getByRole('link', { name: 'Review' })).toHaveCount(0);
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('authorized');
    expect(after.hod_approver).toBe('hod_it');
    expect(after.lines[0].stock).toBe(10);                                                   // stock untouched
    expect(after.notifications).toEqual(['admin2:requisition_approved', 'admin:requisition_approved',
                                         'user_it_1:requisition_approved']);
  });

  test('UC-01 A1: authorize with notes for the Admin', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);
    await authorize(page, 'Urgent - interns start Monday');
    await expect(page.getByRole('alert')).toContainText('has been approved');
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('authorized');
    expect(after.notes).toBe('Urgent - interns start Monday');
  });

  test('UC-01 A2: reach the approval screen from the requisition detail page', async ({ page }) => {
    const before = dbState(SEED.pendingIT2);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/`);
    await page.getByRole('link', { name: 'Review & Approve' }).click();
    await expect(page.getByText('ST001')).toBeVisible();
    await expect(page.getByText('HK002')).toBeVisible();                                     // both lines shown
    await authorize(page);
    await expect(page.getByRole('alert')).toContainText('has been approved');
    expect(dbState(SEED.pendingIT2).status).toBe('authorized');
  });

  test('UC-01 E1: requisition of another department is not available', async ({ page }) => {
    const hr = dbState(SEED.pendingHR);
    await login(page, 'hod_it');
    await expect(page.getByRole('row', { name: new RegExp(hr.number) })).toHaveCount(0);
    const resp = await page.goto(`/requisition/${hr.pk}/hod-approval/`);
    expect(resp!.status()).toBe(404);
    const after = dbState(SEED.pendingHR);
    expect(after.status).toBe('pending_hod');
    expect(after.notifications).toEqual([]);
  });

  test('UC-01 E2: requisition already decided in another tab cannot be authorized', async ({ page, context }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);           // tab 1 opens the form
    const tab2 = await context.newPage();                                 // tab 2 sends it back first
    await tab2.goto(`/requisition/${before.pk}/hod-approval/`);
    await tab2.locator('#action_sent_back').check();
    await tab2.getByLabel(/Comments for Revision/).fill('Please add the cost centre');
    await tab2.getByRole('button', { name: 'Submit Decision' }).click();
    await expect(tab2.getByRole('alert')).toContainText('sent back for revision');
    await page.locator('#action_authorized').check();                           // tab 1 now tries to authorize
    const [resp] = await Promise.all([page.waitForResponse(/hod-approval/), page.getByRole('button', { name: 'Submit Decision' }).click()]);
    expect(resp.status()).toBe(404);
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('sent_back');                               // the first decision stands
    expect(after.notifications).toEqual(['user_it_1:requisition_sent_back']);
  });
});
