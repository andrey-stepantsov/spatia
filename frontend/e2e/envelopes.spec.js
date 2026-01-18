import { test, expect } from '@playwright/test';

test.describe('Spatial Envelopes', () => {
    test.beforeEach(async ({ page }) => {
        // Mock SSE
        await page.route('/api/events', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: 'event: connected\ndata: {}\n\n'
            });
        });
        await page.route('/api/threads', async route => route.fulfill({ json: [] }));
    });

    test('should render envelopes and detect domain conflict', async ({ page }) => {
        // 1. Mock Data: One "System" envelope, One "Generic" atom
        await page.route('/api/envelopes', async route => {
            await route.fulfill({
                json: [
                    { id: 'env-sys', domain: 'system', x: 100, y: 100, w: 400, h: 400 }
                ]
            });
        });

        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'atom-gen', content: 'Intruder', domain: 'generic', x: 0, y: 0, status: 1 }
                ]
            });
        });

        // Mock Geometry Sync
        await page.route('/api/geometry', async route => route.fulfill({ json: { status: 'ok' } }));

        // 2. Load Page
        await page.goto('/');

        // 3. Verify Elements
        const atom = page.getByText('Intruder');
        await expect(atom).toBeVisible();
        await expect(page.getByText('env-sys (system)')).toBeVisible();

        // 4. Verification: No conflict initially
        await expect(page.locator('.conflict-fold')).toHaveCount(0);

        // 5. Drag Atom into Envelope
        const boxAtom = await atom.boundingBox();
        // Envelope is at 100,100 with w400,h400. Center is 300,300.
        // Drag atom to 300, 300.

        if (boxAtom) {
            await page.mouse.move(boxAtom.x + boxAtom.width / 2, boxAtom.y + boxAtom.height / 2);
            await page.mouse.down();
            await page.mouse.move(300, 300, { steps: 10 });
            await page.mouse.up();
        }

        // 6. Verify Conflict (Domain Mismatch)
        await page.waitForTimeout(1000); // Wait for heartbeat
        await expect(page.locator('.conflict-fold')).toHaveCount(1); // Only atom glows? Or both?
        // Logic says: `return { ...node, ...style }` if conflict.
        // It iterates nodes. Envelopes are skipped in collision check?
        // App.jsx:
        // `if (node.type === 'envelope') return node;`
        // So Envelope does NOT glow.
        // `if (nodeDomain !== envDomain) { hasConflict = true }` for the ATOM.
        // So only the Atom should have .conflict-fold.
        await expect(page.locator('.conflict-fold')).toBeVisible();
        await expect(atom).toHaveClass(/conflict-fold/);
    });

    test('should allow creating new envelope', async ({ page }) => {
        // Mock API
        await page.route('/api/envelopes', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({ json: [] });
            } else if (route.request().method() === 'POST') {
                await route.fulfill({ status: 200, json: { status: 'created' } });
            }
        });
        await page.route('/api/atoms', async route => route.fulfill({ json: [] }));

        await page.goto('/');

        // Mock prompt
        page.on('dialog', dialog => dialog.accept('new-env'));

        // Click Button
        await page.getByRole('button', { name: '+ BOUNDARY' }).click();

        // Ideally we verify the POST request happened
        // Or if we reload, it appears. But here we just mock the POST.
        // We can verify request
        const request = await page.waitForRequest(req => req.url().includes('/api/envelopes') && req.method() === 'POST');
        expect(request).toBeTruthy();
    });
});
