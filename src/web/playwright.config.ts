import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8012',
    channel: 'chrome',
    launchOptions: { args: ['--enable-unsafe-swiftshader'] },
  },
  webServer: {
    command: 'poetry run uvicorn argus.web.app:app --host 127.0.0.1 --port 8012',
    cwd: '../..',
    url: 'http://127.0.0.1:8012/',
  },
})
