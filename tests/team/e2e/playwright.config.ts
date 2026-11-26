import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const ROOT = path.resolve(__dirname, '../../..');
const E2E_DB = path.join(ROOT, 'tests/team/data/e2e.sqlite3');
const PORT = Number(process.env.E2E_PORT || 8010);

export default defineConfig({
  testDir: '.',
  testMatch: ['uc/**/*.spec.ts', 'usability/**/*.spec.ts', 'security/**/*.spec.ts', 'a11y/**/*.spec.ts'],
  fullyParallel: false,
  workers: 1,                       // one shared SQLite DB: tests run serially and reset it first
  retries: 0,
  timeout: 30_000,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '../../../reports/playwright' }],
             ['junit', { outputFile: '../../../reports/tmp/junit-e2e.xml' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    ...devices['Desktop Chrome'],
    channel: 'chromium',             // full Chromium build in new headless mode
    screenshot: 'on',
    trace: 'retain-on-failure',
    proxy: process.env.ZAP_PROXY ? { server: process.env.ZAP_PROXY, bypass: '<-loopback>' } : undefined,
    launchOptions: process.env.ZAP_PROXY ? { args: ['--proxy-bypass-list=<-loopback>'] } : undefined,
    ignoreHTTPSErrors: true,
  },
  globalSetup: require.resolve('./helpers/global-setup'),
  webServer: {
    command: `${ROOT}/.venv/bin/python ${ROOT}/manage.py runserver 127.0.0.1:${PORT} --noreload`,
    cwd: ROOT,
    url: `http://127.0.0.1:${PORT}/login/`,
    reuseExistingServer: !process.env.CI,
    env: { DJANGO_SETTINGS_MODULE: 'tests.team.settings_test', TEAM_DB: E2E_DB, FAST_HASH: '1' },
    timeout: 60_000,
  },
});
