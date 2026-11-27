/**
 * Doc section 3 - automated usability task tests (one per workflow).            owner: Member B
 *
 * UX-01 (WF1) keyboard only: reach the decision controls with Tab, choose with the arrow keys /
 *       Space (native radio-group behaviour), and submit with Enter; assert the confirmation.
 * UX-02 (WF2) submit a value the business rule rejects (BR-1), check the error tells the user
 *       what to correct, correct it, and confirm success.
 */
import { test, expect, login, dbState, SEED } from '../helpers/fixtures';

async function focusedId(page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    return el ? (el.id || el.getAttribute('name') || el.tagName.toLowerCase()) : null;
  });
}

test('UX-01 WF1 keyboard-only authorization: focus order and keyboard submit', async ({ page }) => {
  const before = dbState(SEED.pendingIT);
  await login(page, 'hod_it');
  await page.goto(`/requisition/${before.pk}/hod-approval/`);

  // 1) Keyboard-select a decision: focus the first radio and press Space. Submit is DISABLED until a
  //    decision is chosen, so it is not a tab stop before this (observed in the DOM).
  await page.locator('#action_authorized').focus();
  await page.keyboard.press('Space');
  await expect(page.locator('#action_authorized')).toBeChecked();
  await expect(page.locator('#submitBtn')).toBeEnabled();

  // 2) Walk forward with Tab only and record the focus order.
  const order: string[] = [await focusedId(page)];
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press('Tab');
    order.push(await focusedId(page));
  }
  // Expected: radio group (one tab stop) -> Additional Notes -> Cancel link -> Submit button.
  expect(order).toEqual(['action_authorized', 'id_notes', 'a', 'submitBtn']);

  // Shift+Tab back to the radio group (keyboard only), then the arrow keys move inside the group
  // (native behaviour) and must keep the form consistent.
  for (let i = 0; i < 3; i++) await page.keyboard.press('Shift+Tab');
  expect(await focusedId(page)).toBe('action_authorized');
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#action_sent_back')).toBeChecked();
  await expect(page.locator('#sendBackReasonField')).toBeVisible();
  await page.keyboard.press('ArrowLeft');
  await expect(page.locator('#action_authorized')).toBeChecked();

  // 3) Reach Submit with Tab from the radio group again and press Enter.
  for (let i = 0; i < 3; i++) await page.keyboard.press('Tab');
  expect(await focusedId(page)).toBe('submitBtn');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('alert')).toContainText(`Requisition ${before.number} has been approved.`);
  expect(dbState(SEED.pendingIT).status).toBe('authorized');
});

test('UX-02 WF2 rule rejection explains the fix, corrected value succeeds', async ({ page }) => {
  const before = dbState(SEED.authorized);          // requested 4, stock 10
  await login(page, 'admin');
  await page.goto(`/requisition/${before.pk}/issue/`);
  const qty = page.getByRole('spinbutton').first();

  await qty.fill('7');                               // violates BR-1: more than requested
  await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
  const error = page.getByRole('alert');
  await expect(error).toContainText('Cannot issue more than requested (4).');   // says what the limit is
  expect(dbState(SEED.authorized).status).toBe('authorized');                  // nothing saved

  await page.getByRole('spinbutton').first().fill('3');                        // corrected value
  await page.getByRole('button', { name: /Issue Items & Complete/ }).click();
  await expect(page.getByRole('alert')).toContainText(`Items issued for requisition ${before.number}`);
  const after = dbState(SEED.authorized);
  expect(after.status).toBe('issued');
  expect(after.lines[0]).toMatchObject({ issued: 3, stock: 7 });
});
