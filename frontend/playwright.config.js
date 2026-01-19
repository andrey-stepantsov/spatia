import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    fullyParallel: false, // Run tests serially to prevent database conflicts
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1, // Single worker to ensure test isolation
    reporter: 'html',
    use: {
        baseURL: process.env.BASE_URL || 'http://localhost:5173',
        trace: 'on-first-retry',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    webServer: process.env.SKIP_WEBSERVER ? undefined : {
        command: 'cd .. && PYTHONPATH=. /Users/stepants/dev/spatia/.venv/bin/python3 -m uvicorn backend.main:app --port 8000 & sleep 5 && npm run dev',
        url: process.env.BASE_URL || 'http://localhost:5173',
        reuseExistingServer: true,
    },
});
