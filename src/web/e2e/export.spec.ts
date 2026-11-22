import { expect, test } from '@playwright/test'

test('exports multiple models and formats using their last successful preview', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/models/base')
  const dimensions = page.getByTestId('model-dimensions')
  const side = page.getByRole('spinbutton', { name: '底板边长' })
  await expect(dimensions).toHaveText('38 × 38 × 12.5 mm')
  await side.fill('42')
  await page.getByRole('button', { name: '重新生成', exact: true }).click()
  await expect(dimensions).toHaveText('42 × 42 × 12.5 mm')
  await side.fill('44')
  await expect(page.getByText('有未生成的修改')).toBeVisible()

  await page.getByRole('button', { name: '导出', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '导出文件' })
  const base = dialog.getByRole('checkbox', { name: '底座', exact: true })
  const head = dialog.getByRole('checkbox', { name: '打印云台头', exact: true })
  await expect(base).toBeChecked()
  await expect(base).toHaveAccessibleDescription('当前预览')
  await expect(head).toHaveAccessibleDescription('默认参数')
  await expect(dialog.getByRole('checkbox', { name: '3MF' })).toBeChecked()
  await head.check()
  await dialog.getByRole('checkbox', { name: 'STEP' }).check()
  await dialog.getByRole('checkbox', { name: 'STL' }).check()
  await expect(dialog.getByRole('status')).toHaveText('6 个文件 · ZIP')

  const request = page.waitForRequest('**/api/exports')
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载', exact: true }).click()
  expect((await request).postDataJSON()).toEqual({
    models: [
      { id: 'base', parameters: { plate_side: 42, plate_thickness: 3.5, corner_hole_pitch: 30, corner_hole_diameter: 2.5, ring_height: 9 } },
      { id: 'head-print' },
    ],
    formats: ['step', '3mf', 'stl'],
  })
  expect((await download).suggestedFilename()).toBe('argus-models.zip')
  await expect(dialog).toBeHidden()
  await expect(side).toHaveValue('44')
  await expect(dimensions).toHaveText('42 × 42 × 12.5 mm')
})

test('keeps options after an export error and retries a direct download on a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 })
  let release = () => {}
  let attempts = 0
  const blocked = new Promise<void>((resolve) => { release = resolve })
  await page.route('**/api/exports', async (route) => {
    attempts += 1
    if (attempts === 1) {
      await blocked
      await route.fulfill({ status: 500, json: { detail: { message: '打印云台头的 STL 导出失败，请重试。' } } })
    } else {
      await route.continue()
    }
  })
  await page.goto('/models/head-print')
  await expect(page.getByTestId('model-dimensions')).toHaveText('40 × 26 × 38.8 mm')
  const open = page.getByRole('button', { name: '导出', exact: true })
  const dialog = page.getByRole('dialog', { name: '导出文件' })
  await open.focus()
  await page.keyboard.press('Enter')
  await expect(dialog).toBeVisible()
  expect(await dialog.evaluate((element) => element.scrollWidth)).toBeLessThanOrEqual(320)
  await page.keyboard.press('Escape')
  await expect(open).toBeFocused()
  await open.click()

  const stl = dialog.getByRole('checkbox', { name: 'STL' })
  const download = dialog.getByRole('button', { name: '下载', exact: true })
  await dialog.getByRole('checkbox', { name: '3MF' }).uncheck()
  await expect(download).toBeDisabled()
  await stl.check()
  await download.click()
  await expect(dialog.getByRole('button', { name: '正在导出…' })).toBeDisabled()
  await expect(stl).toBeDisabled()
  release()
  await expect(dialog.getByRole('alert')).toHaveText('打印云台头的 STL 导出失败，请重试。')
  await expect(stl).toBeChecked()
  await expect(dialog.getByRole('checkbox', { name: '打印云台头', exact: true })).toBeChecked()

  const retry = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '重试下载' }).click()
  expect((await retry).suggestedFilename()).toBe('gimbal_head_print.stl')
  await expect(dialog).toBeHidden()
  await expect(open).toBeFocused()
  expect(attempts).toBe(2)
})
