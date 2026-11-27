/**
 * UC-04  Admin issues a partial quantity (WF2, FR-09)                 owner: Member B
 * Preconditions: requisition authorized; Admin logged in.
 * Postconditions (success): status issued; each line's issued quantity and stock reduced by exactly
 *     that amount; outward transactions only for lines issued > 0.  (failure): nothing changes.
 */
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

const submit = (page) => page.getByRole('button', { name: /Issue Items & Complete/ }).click();

test.describe('UC-04 Admin issues a partial quantity', () => {
  test('UC-04 main: issue less than requested on a line', async ({ page }) => {
    const before = dbState(SEED.authorized);                       // ST001 requested 4, stock 10
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    await page.getByRole('spinbutton').first().fill('2');
    await submit(page);
    await expect(page.getByRole('alert')).toContainText(`Items issued for requisition ${before.number}`);
    await page.goto(`/requisition/${before.pk}/`);
    await expect(page.getByRole('row', { name: /ST001/ })).toContainText('Partial');   // line status badge
    const after = dbState(SEED.authorized);
    expect(after.status).toBe('issued');
    expect(after.lines[0]).toMatchObject({ issued: 2, stock: 8 });
    expect(after.outward).toEqual([{ code: 'ST001', change: -2, balance_after: 8 }]);
  });

  test('UC-04 A1: issue 0 on one line and a partial amount on the other', async ({ page }) => {
    const before = dbState(SEED.authorizedMulti);                  // ST001 x3, HK002 x5
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    await page.getByRole('row', { name: /ST001/ }).getByRole('spinbutton').fill('0');
    await page.getByRole('row', { name: /HK002/ }).getByRole('spinbutton').fill('4');
    await submit(page);
    await expect(page.getByRole('alert')).toContainText('Items issued');
    const after = dbState(SEED.authorizedMulti);
    expect(after.lines.map(l => [l.code, l.issued, l.stock])).toEqual([['ST001', 0, 10], ['HK002', 4, 46]]);
    expect(after.outward).toEqual([{ code: 'HK002', change: -4, balance_after: 46 }]);   // none for the 0 line
  });

  test('UC-04 A2: stock is lower than requested - issue exactly the available stock', async ({ page }) => {
    const before = dbState(SEED.authorizedShort);                  // ST002 requested 3, stock 1
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    await page.getByRole('spinbutton').first().fill('1');
    await submit(page);
    await expect(page.getByRole('alert')).toContainText('Items issued');
    const after = dbState(SEED.authorizedShort);
    expect(after.lines[0]).toMatchObject({ issued: 1, stock: 0 });
    await page.goto('/inventory/');
    await expect(page.getByRole('row', { name: /ST002/ })).toContainText('Out of Stock');
  });

  test('UC-04 E1: more than requested is refused with the limit in the message', async ({ page }) => {
    const before = dbState(SEED.authorized);
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    await page.getByRole('spinbutton').first().fill('5');
    await submit(page);
    await expect(page.getByRole('alert')).toContainText('Cannot issue more than requested (4).');
    const after = dbState(SEED.authorized);
    expect(after.status).toBe('authorized');
    expect(after.lines[0]).toMatchObject({ issued: 0, stock: 10 });
  });

  test('UC-04 E2: a negative quantity is blocked', async ({ page }) => {
    const before = dbState(SEED.authorized);
    await login(page, 'admin');
    await page.goto(`/requisition/${before.pk}/issue/`);
    const qty = page.getByRole('spinbutton').first();
    await qty.fill('-1');
    await submit(page);
    expect(await qty.evaluate((el: HTMLInputElement) => el.validity.rangeUnderflow)).toBe(true);
    const after = dbState(SEED.authorized);
    expect(after.status).toBe('authorized');
    expect(after.outward).toEqual([]);
  });
});
