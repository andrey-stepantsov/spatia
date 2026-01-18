import { test, expect } from '@playwright/test';

test.describe('Spatia Comprehensive Demo', () => {

    const timestamp = Date.now();
    const worldName = `demo-${timestamp}`;
    const cloneName = `archive-${timestamp}`;

    test.beforeEach(async ({ page }) => {
        await page.goto('/');

        // Robust dialog handling
        page.on('dialog', async dialog => {
            console.log(`Dialog: ${dialog.type()} - ${dialog.message()}`);
            if (dialog.type() === 'prompt') {
                await dialog.accept(cloneName);
            } else {
                await dialog.accept();
            }
        });
    });

    test('Full Visual Walkthrough', async ({ page }) => {
        test.setTimeout(120000); // 2 minutes for full recording

        // --- 1. WORLD CREATION ---
        const worldButton = page.locator('button:has-text("World")').first();
        await expect(worldButton).toBeVisible();
        await worldButton.click();

        await page.getByText('+ Create New World').click();
        await page.getByPlaceholder('my-new-world').fill(worldName);
        await page.getByRole('button', { name: 'Create World' }).click();
        await expect(worldButton).toContainText(worldName);

        // --- 2. ATOM LIFECYCLE: SHATTER & WITNESS ---
        const ideaPath = `atoms/idea_${timestamp}.md`;
        await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', ideaPath);
        await page.fill('textarea[placeholder="Content (optional)"]', ':intent "My Big Idea" (defun idea ())');
        await page.click('button:has-text("SHATTER ATOM")');

        const ideaNode = page.locator(`.react-flow__node-spatia:has-text("${ideaPath}")`);
        await expect(ideaNode).toBeVisible();
        const ideaDiv = ideaNode.locator('> div');
        await expect(ideaDiv).toHaveClass(/border-blue-500/);

        // Witness
        await ideaNode.locator('button:has-text("Witness")').click();
        await expect(ideaDiv).toHaveClass(/border-green-500/, { timeout: 15000 });

        // --- 3. ATOM LIFECYCLE: SUMMON (AI) ---
        const taskPath = `atoms/task_${timestamp}.md`;
        await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', taskPath);
        await page.fill('textarea[placeholder="Content (optional)"]', 'Describe a plan for this idea.');
        await page.click('button:has-text("SHATTER ATOM")');

        const taskNode = page.locator(`.react-flow__node-spatia:has-text("${taskPath}")`);
        await expect(taskNode).toBeVisible();

        // Summon
        await taskNode.locator('button:has-text("Summon")').click();
        // Just verify it doesn't crash; status update might define completion.
        // We'll trust the button click visual.

        // --- 4. SPATIAL ORGANIZATION (THREADS) ---
        // Drag from Idea (Bottom) to Task (Top)
        // Wait for nodes to be layouted/stable
        await page.waitForTimeout(1000);

        // Manual drag simulation for React Flow
        // Idea (Source) -> Bottom Handle (Last)
        const sourceHandle = ideaNode.locator('.react-flow__handle').last();
        // Task (Target) -> Top Handle (First)
        const targetHandle = taskNode.locator('.react-flow__handle').first();

        // 1. Hover source
        await sourceHandle.hover();
        const sourceBox = await sourceHandle.boundingBox();
        const targetBox = await targetHandle.boundingBox();

        if (sourceBox && targetBox) {
            // Mouse down on source center
            await page.mouse.move(sourceBox.x + sourceBox.width / 2, sourceBox.y + sourceBox.height / 2);
            await page.mouse.down();

            // Move to target center
            await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps: 10 });

            // Mouse up
            await page.mouse.up();
        }

        // Verify edge exists
        await expect(page.locator('.react-flow__edge')).toBeVisible();

        // --- 5. SNAPSHOT ---
        // Ensure menu opening is robust
        const worldsHeader = page.getByText('Available Worlds');
        if (!await worldsHeader.isVisible()) {
            await worldButton.click();
        }
        await expect(worldsHeader).toBeVisible();

        const row = page.locator('.group', { hasText: worldName });
        const meatball = row.locator('button:has-text("⋮")');
        await meatball.click();

        const snapshotBtn = page.locator('button', { hasText: 'Snapshot' });
        await expect(snapshotBtn).toBeVisible();

        // Wait for dialog
        const snapDialogPromise = page.waitForEvent('dialog');
        await snapshotBtn.evaluate(b => b.click());
        await snapDialogPromise; // Handled by global listener (accept)

        // --- 6. CLONE ---
        // Reopen menu
        if (!await worldsHeader.isVisible()) {
            await worldButton.click();
        }
        await meatball.click();

        const cloneBtn = page.getByText('Clone');
        const cloneDialogPromise = page.waitForEvent('dialog'); // Prompt
        await cloneBtn.evaluate(b => b.click());
        await cloneDialogPromise; // Handled by global listener (inputs cloneName)

        // Success alert
        // Wait for potential success alert? Or just verify switching manually?
        // App auto-refreshes list.

        // --- 7. VERIFY CLONE EXISTENCE ---
        if (!await worldsHeader.isVisible()) {
            await worldButton.click();
        }
        await expect(page.locator('.group', { hasText: cloneName })).toBeVisible();

    });

});
