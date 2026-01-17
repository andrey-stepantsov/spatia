
import { test, expect } from '@playwright/test';
import axios from 'axios';

test('Workspace Switching and Witness Protocol', async ({ page, request }) => {
    // 1. Navigate to App
    await page.goto('http://localhost:5173');
    await expect(page).toHaveTitle(/Spatia/);

    // 2. Verify Workspace Selector
    // Wait for selector to load
    const wsSelector = page.locator('select');
    await expect(wsSelector).toBeVisible();

    // Note: Switching modifies backend state which might affect other tests potentially, 
    // but we are in e2e. Let's switch to 'default' just to be sure.
    await wsSelector.selectOption('default');

    // 3. Witness Lisp Intent (Blue -> Green)

    // Define a unique path to avoid collisions
    const testPath = `atoms/e2e_intent_${Date.now()}.md`;

    // Shatter Atom (using the UI portal)
    await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', testPath);

    // Content should auto-fill if Hollow toggle is on. 
    // Let's ensure toggle is on? 
    // Or just manually fill content to be safe.
    const lispIntent = ':intent "E2E Test Intent" (defun e2e_test ())';
    await page.fill('textarea[placeholder="Content (optional)"]', lispIntent);

    await page.click('button:has-text("SHATTER ATOM")');

    // Wait for node to appear
    const node = page.locator(`.react-flow__node-spatia:has-text("${testPath}")`);
    await expect(node).toBeVisible({ timeout: 5000 });

    // Verify it is Blue (Hollow) - check class or style
    // Using our heuristic from browser subagent
    const nodeDiv = node.locator('> div');
    await expect(nodeDiv).toHaveClass(/border-blue-500/);

    // Click Witness
    await node.locator('button:has-text("Witness")').click();

    // Wait for transition to Green (Endorsed)
    // This might take a second for backend to process and SSE to update
    await expect(nodeDiv).toHaveClass(/border-green-500/, { timeout: 10000 });

    // 4. Summon Handshake (Just verify button exists and doesn't crash)
    // We can't easily verify backend log without file access from playwright easily (unless we add API for it),
    // but we can check the button interaction.

    // Let's create another one for Summon
    const summonPath = `atoms/e2e_summon_${Date.now()}.md`;
    await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', summonPath);
    await page.fill('textarea[placeholder="Content (optional)"]', lispIntent);
    await page.click('button:has-text("SHATTER ATOM")');

    const summonNode = page.locator(`.react-flow__node-spatia:has-text("${summonPath}")`);
    await expect(summonNode).toBeVisible();

    // Handle confirm dialog
    page.on('dialog', dialog => dialog.accept());

    // Click Summon
    await summonNode.locator('button:has-text("Summon")').click();

    // It stays Blue/Green (depends if we witness it). 
    // If we just Summon, it stays Blue (Status 0) in UI until AI updates it to 1. 
    // (Our mock doesn't auto-update to 1 immediately? Actually backend sets status=1 *after* summon request?)
    // Let's check backend logic: summon_atom sets status=2 then calls run_witness.
    // Wait, summon_atom endpoint logic:
    // 1. Update Content, Status=1 (Claim).
    // 2. Set Status=2 (Witnessing).
    // 3. Background Witness.
    // So it SHOULD go Blue -> Purple -> Green (if Lisp check passes).

    // Let's just verify it doesn't crash.
    await page.waitForTimeout(2000);
});
