/**
 * UC-03  Admin issues an authorized requisition in full (WF2)        owner: Member A
 * Preconditions: requisition authorized; Admin logged in; enough stock.
 * Postconditions (success): status issued, issuer = Admin, stock reduced by the issued quantity,
 *     one outward transaction per issued line, initiator notified.
 *   (failure): status still authorized, stock unchanged, no transaction.
 *
 * Defect F13: issuing the PRE-FILLED quantities (the normal path) marks the requisition issued
 * but deducts no stock and records no transaction. Flows that keep the defaults are therefore
 * marked test.fail(...) - Playwright reports them as passing only while they fail, and turns
 * red as soon as F13 is fixed (the marker must then be removed in the fix PR).
 */
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

test.describe('UC-03 Admin issues a requisition in full', () => {
  test('UC-03 main: issue the pre-filled quantities from the Admin dashboard', async ({ page }) => {
    test.fail(true, 'F13: unchanged pre-filled quantity is not saved - no stock deduction');
    const before = dbState(SEED.authorized);
    await login(page, 'admin');
    await expect(page).toHaveURL(/\/requisition\/admin\//);
    await page.getByRole('row', { name: new RegExp(before.number) }).getByRole('link', { name: 'Issue Items' }).click();
    await expect(page.getByRole('spinbutton').first()).toHaveValue('4');              // FR-08 default
    await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
    await expect(page.getByRole('alert')).toContainText(`Items issued for requisition ${before.number}`);
    const after = dbState(SEED.authorized);
    expect(after.status).toBe('issued');
    expect(after.issuer).toBe('admin');
    expect(after.lines[0].stock).toBe(6);                                             // fails on baseline (F13)
    expect(after.outward).toEqual([{ code: 'ST001', change: -4, balance_after: 6 }]);
  });

  test('UC-03 A1: open the issue screen from the requisition detail page', async ({ page }) => {
    test.fail(true, 'F13: unchanged pre-filled quantity is not saved - no stock deduction');
    const before = dbState(SEED.authorizedPaper);
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/`);
    await page.getByRole('link', { name: 'Issue Items' }).click();
    await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
    await expect(page.getByRole('alert')).toContainText('Items issued');
    const after = dbState(SEED.authorizedPaper);
    expect(after.status).toBe('issued');
    expect(after.lines[0].stock).toBe(0);
  });

  test('UC-03 A2: multi-line requisition issued in one submit (quantities typed)', async ({ page }) => {
    const before = dbState(SEED.authorizedMulti);                  // ST001 x3, HK002 x5
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    // rows are listed in Item order (housekeeping before stationery) - locate each line by its code
    await page.getByRole('row', { name: /ST001/ }).getByRole('spinbutton').fill('2');
    await page.getByRole('row', { name: /HK002/ }).getByRole('spinbutton').fill('4');
    await page.getByPlaceholder('Notes (optional)').first().fill('Full issue, both lines');
    await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
    await expect(page.getByRole('alert')).toContainText('Items issued');
    const after = dbState(SEED.authorizedMulti);
    expect(after.status).toBe('issued');
    expect(after.lines.map(l => [l.code, l.issued])).toEqual([['ST001', 2], ['HK002', 4]]);
    expect(after.outward).toHaveLength(after.lines.filter(l => l.issued > 0).length);
    expect(after.notifications).toEqual(['user_it_1:requisition_issued']);
  });

  test('UC-03 E1: quantity above stock is refused and nothing is saved', async ({ page }) => {
    const before = dbState(SEED.authorizedShort);                  // ST002 requested 3, stock 1
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
    await expect(page.getByRole('alert')).toContainText('Insufficient stock. Available: 1, Requested: 3.');
    const after = dbState(SEED.authorizedShort);
    expect(after.status).toBe('authorized');
    expect(after.lines[0].stock).toBe(1);
    expect(after.outward).toEqual([]);
  });

  test('UC-03 E2: requisition already issued in another tab returns not found', async ({ page, context }) => {
    const before = dbState(SEED.authorizedMulti);
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    const tab2 = await context.newPage();
    await tab2.goto(`/requisition/${before.pk}/issue/`);
    await tab2.getByRole('row', { name: /ST001/ }).getByRole('spinbutton').fill('2');
    await tab2.getByRole('button', { name: /Issue Items & Complete/ }).click();
    await expect(tab2.getByRole('alert')).toContainText('Items issued');
    await page.getByRole('row', { name: /ST001/ }).getByRole('spinbutton').fill('2');
    const [resp] = await Promise.all([page.waitForResponse(/\/issue\//), page.getByRole('button', { name: /Issue Items & Complete/ }).click()]);
    expect(resp.status()).toBe(404);
    const after = dbState(SEED.authorizedMulti);
    expect(after.outward).toHaveLength(1);                         // no duplicate posting
    expect(after.lines.find(l => l.code === 'ST001')!.stock).toBe(8);
  });
});
