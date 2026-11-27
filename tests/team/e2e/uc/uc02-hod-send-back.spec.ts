/**
 * UC-02  HOD sends a requisition back for revision (WF1 alternative outcome)   owner: Member B
 * Preconditions: requisition pending_hod from the HOD's department; HOD logged in.
 * Postconditions (success): status sent_back with comments + timestamp, initiator notified.
 *                (failure):  status still pending_hod, nothing recorded.
 */
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

test.describe('UC-02 HOD sends back a requisition', () => {
  test('UC-02 main: send back with comments', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.getByRole('row', { name: new RegExp(before.number) }).getByRole('link', { name: 'Review' }).click();
    await page.locator('#action_sent_back').check();
    await expect(page.getByLabel(/Comments for Revision/)).toBeVisible();
    await page.getByLabel(/Comments for Revision/).fill('Add the cost centre code');
    await page.getByRole('button', { name: 'Submit Decision' }).click();
    await expect(page.getByRole('alert')).toContainText(`Requisition ${before.number} has been sent back for revision.`);
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('sent_back');
    expect(after.sent_back_reason).toBe('Add the cost centre code');
    expect(after.notifications).toEqual(['user_it_1:requisition_sent_back']);
  });

  test('UC-02 A1: reject with a reason instead', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);
    await page.locator('#action_rejected').check();
    await page.getByLabel(/Reason for Rejection/).fill('Pens are already in stock in the department');
    await page.getByRole('button', { name: 'Submit Decision' }).click();
    await expect(page.getByRole('alert')).toContainText('has been rejected');
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('rejected');
    expect(after.rejection_reason).toBe('Pens are already in stock in the department');
    expect(after.notifications).toEqual(['user_it_1:requisition_rejected']);
  });

  test('UC-02 A2: change the decision from Authorize to Send back before submitting', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);
    await page.locator('#action_authorized').check();
    await expect(page.getByLabel(/Comments for Revision/)).toBeHidden();
    await page.locator('#action_sent_back').check();
    await page.getByLabel(/Comments for Revision/).fill('Quantity looks too high');
    await page.getByRole('button', { name: 'Submit Decision' }).click();
    await expect(page.getByRole('alert')).toContainText('sent back for revision');
    expect(dbState(SEED.pendingIT).status).toBe('sent_back');
  });

  test('UC-02 E1: send back without comments is blocked', async ({ page }) => {
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);
    await page.locator('#action_sent_back').check();
    await page.getByRole('button', { name: 'Submit Decision' }).click();
    const comments = page.getByLabel(/Comments for Revision/);
    expect(await comments.evaluate((el: HTMLTextAreaElement) => el.validity.valueMissing)).toBe(true);
    await expect(page).toHaveURL(new RegExp(`/requisition/${before.pk}/hod-approval/`));
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('pending_hod');
    expect(after.notifications).toEqual([]);
  });

  test('UC-02 E2: reject without a reason is refused by the server', async ({ page }) => {
    test.fail(true, 'F20: the server error is rendered inside the hidden reason section - the user cannot see it');
    const before = dbState(SEED.pendingIT);
    await login(page, 'hod_it');
    await page.goto(`/requisition/${before.pk}/hod-approval/`);
    await page.locator('#action_rejected').check();
    // remove the browser-side 'required' so the SERVER rule (BR-2b) is exercised
    await page.getByLabel(/Reason for Rejection/).evaluate((el: HTMLTextAreaElement) => { el.required = false; });
    await page.getByRole('button', { name: 'Submit Decision' }).click();
    const after = dbState(SEED.pendingIT);
    expect(after.status).toBe('pending_hod');                                       // rule enforced
    expect(after.rejection_reason).toBeNull();
    await expect(page.getByText('Rejection reason is required.')).toBeAttached();   // message is in the page...
    await expect(page.getByText('Rejection reason is required.')).toBeVisible();    // ...but must be visible (F20)
  });
});
