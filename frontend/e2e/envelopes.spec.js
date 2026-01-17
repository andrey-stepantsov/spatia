import { test, expect } from '@playwright/test';

test.describe('Spatial Envelopes & Conflict Fold', () => {
    test.beforeEach(async ({ page }) => {
        // Mock Data
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'doc.md', content: 'Documentation', x: 0, y: 150, status: 1, domain: 'Documentation' },
                    { id: 'firmware.c', content: 'Firmware Code', x: 300, y: 0, status: 1, domain: 'Firmware' }
                ]
            });
        });

        await page.route('/api/threads', async route => {
            await route.fulfill({ json: [] });
        });

        await page.route('/api/envelopes', async route => {
            await route.fulfill({
                json: [
                    // Envelope for Firmware. 
                    // Any non-Firmware node inside this box (x:200, y:-50, w:300, h:300) should trigger conflict.
                    { id: 'env_fw', domain: 'Firmware', x: 200, y: -50, w: 300, h: 300 }
                ]
            });
        });

        // Mock SSE to prevent hang
        await page.route('/api/events', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: 'event: connected\ndata: {}\n\n'
            });
        });

        // Debugging: Log console messages
        page.on('console', msg => console.log(`[Browser Console] ${msg.text()}`));
        page.on('pageerror', err => console.log(`[Browser Error] ${err.message}`));

        await page.goto('/');

        // Wait for canvas to load with explicit increased timeout
        // Also wait for network idle to ensure assets are loaded
        try {
            await page.waitForLoadState('networkidle', { timeout: 10000 });
        } catch (e) {
            console.log("Network idle timeout, proceeding to selector check...");
        }

        await page.waitForSelector('.react-flow', { timeout: 60000 });
    });

    test('should render envelopes', async ({ page }) => {
        // Envelopes are rendered as Background Nodes in our list, or at least in the DOM.
        // We look for the text label.
        const envelopeLabel = page.getByText('env_fw (Firmware)');
        await expect(envelopeLabel).toBeVisible();
    });

    test('should trigger conflict fold when Documentation node enters Firmware Envelope', async ({ page }) => {
        // 1. Locate the "Documentation" node (currently at 0,150 - outside envelope)
        const docNode = page.locator('.react-flow__node-spatia').filter({ hasText: 'Documentation' });

        // Ensure strictly no conflict initially
        await expect(docNode).not.toHaveClass(/conflict-fold/);

        // 2. Drag it into the Envelope (Envelope starts at x:200)
        // We move it to x:250, y:150 (Y stays same)
        /*
        await docNode.dragTo(page.locator('.react-flow__pane'), {
            targetPosition: { x: 300, y: 100 } // approximate screen coords relative to pane might be tricky
        });
        */

        // Alternative: Use mouse actions if dragTo is flaky with canvas
        const box = await docNode.boundingBox();
        if (!box) throw new Error("Node not found");

        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        // Move by +300px X
        await page.mouse.move(box.x + 300 + box.width / 2, box.y + box.height / 2, { steps: 5 });
        await page.mouse.up();

        // 3. Verify visual conflict indication (after 500ms debounce interval)
        // We wait a bit more than 500ms
        await page.waitForTimeout(1000);

        await expect(docNode).toHaveClass(/conflict-fold/);

        // Also check CSS style for red border/box-shadow if class check isn't enough
        const style = await docNode.getAttribute('style');
        expect(style).toContain('border: 2px solid red');
    });

    test('should NOT trigger conflict for matching domain (Firmware node)', async ({ page }) => {
        // Firmware node is already at x:300, inside the envelope (starts x:200, w:300 -> ends x:500)
        // It matches the domain 'Firmware'

        const fwNode = page.locator('.react-flow__node-spatia').filter({ hasText: 'Firmware Code' });

        // Wait for potential conflict check
        await page.waitForTimeout(1000);

        await expect(fwNode).not.toHaveClass(/conflict-fold/);
    });
});
