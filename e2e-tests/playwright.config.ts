import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: './results/html' }],
    ['junit', { outputFile: './results/junit.xml' }],
    ['json', { outputFile: './results/results.json' }],
    ['list']
  ],
  outputDir: './results/artifacts',
  use: {
    baseURL: process.env.TEST_BASE_URL || 'http://localhost:9900',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
