import { expect, test } from '@playwright/test'

test('edits only take effect on generation, and a failed build keeps the previous result', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  const url = '/api/models/base/preview'
  let captures = 0
  await page.route('**' + url, async (route) => {
    captures += 1
    if (captures === 2) {
      await route.fulfill({ status: 500, json: { detail: { message: '模型生成失败，请重试。' } } })
    } else {
      await route.continue()
    }
  })
  await page.goto('/models/base')
  const dimensions = page.getByTestId('model-dimensions')
  const generate = page.getByRole('button', { name: '重新生成', exact: true })
  await expect(dimensions).toHaveText('38 × 38 × 12.5 mm')
  await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
  await page.getByRole('spinbutton', { name: '底板边长' }).fill('42')
  await expect(page.getByText('有未生成的修改')).toBeVisible()
  await expect(dimensions).toHaveText('38 × 38 × 12.5 mm')
  expect(captures).toBe(1)
  await generate.click()
  await expect(page.getByRole('alert')).toHaveText('模型生成失败，请重试。')
  await page.getByText('生成失败', { exact: true }).click()
  await expect(page.locator('details[open]')).toHaveText('生成失败模型生成失败，请重试。')
  await expect(dimensions).toHaveText('38 × 38 × 12.5 mm')
  await expect(page.getByRole('spinbutton', { name: '底板边长' })).toHaveValue('42')
  await generate.click()
  await expect(dimensions).toHaveText('42 × 42 × 12.5 mm')
  expect(captures).toBe(3)

  await page.getByRole('spinbutton', { name: '底板边长' }).fill('34')
  await page.getByRole('spinbutton', { name: '角孔孔距' }).fill('40')
  await generate.click()
  await expect(page.getByRole('spinbutton', { name: '角孔孔距' })).toHaveAttribute('aria-invalid', 'true')
  await expect(dimensions).toHaveText('42 × 42 × 12.5 mm')
  await page.getByRole('button', { name: '恢复默认' }).click()
  await expect(page.getByRole('spinbutton', { name: '底板边长' })).toHaveValue('38')
  await expect(dimensions).toHaveText('42 × 42 × 12.5 mm')
})

test('model navigation preserves results and drafts through browser history', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/models/base')
  await expect(page.getByTestId('model-dimensions')).toHaveText('38 × 38 × 12.5 mm')
  await expect(page).toHaveURL('/models/base')
  const bracket = page.getByRole('link', { name: '支架', exact: true })
  const head = page.getByRole('link', { name: '云台头', exact: true })
  const generate = page.getByRole('button', { name: '重新生成', exact: true })
  await bracket.click()
  await expect(page).toHaveURL('/models/bracket')
  await expect(page.getByTestId('model-dimensions')).toHaveText('40.5 × 37.06 × 46 mm')
  let release = () => {}
  const slowBuild = new Promise<void>((resolve) => { release = resolve })
  await page.route('**/api/models/bracket/preview', async (route) => {
    await slowBuild
    await route.continue()
  })
  await page.getByRole('spinbutton', { name: '定位销伸出量' }).fill('1.5')
  await generate.click()
  await expect(page.getByRole('button', { name: '正在生成…' })).toBeDisabled()
  await head.click()
  await expect(page).toHaveURL('/models/head')
  await expect(page.getByTestId('model-dimensions')).toHaveText('40 × 26 × 38.8 mm')
  const bracketResponse = page.waitForResponse('**/api/models/bracket/preview')
  release()
  await bracketResponse
  await expect(page.getByRole('heading', { name: '云台头', exact: true })).toBeVisible()

  const headResponse = page.waitForResponse('**/api/models/head/preview')
  await page.getByRole('spinbutton', { name: '上耳孔直径' }).fill('2.4')
  await generate.click()
  expect((await (await headResponse).json()).parameters.upper_lug_diameter).toBe(2.4)
  await page.goBack()
  await expect(page).toHaveURL('/models/bracket')
  await expect(bracket).toHaveAttribute('aria-current', 'page')
  await expect(page.getByTestId('model-dimensions')).toHaveText('40 × 37.06 × 46 mm')
  await expect(page.getByRole('spinbutton', { name: '定位销伸出量' })).toHaveValue('1.5')
  await page.goForward()
  await expect(page).toHaveURL('/models/head')
  await expect(head).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('spinbutton', { name: '上耳孔直径' })).toHaveValue('2.4')
})

test('model pages open directly and stay selected on reload', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  const builds: string[] = []
  page.on('request', (request) => {
    if (request.method() === 'POST') builds.push(new URL(request.url()).pathname)
  })
  const models = [
    ['base', '底座'], ['base-servo', '舵盘槽底盘'], ['servo-horn-long', '长短臂舵盘'], ['servo-horn', 'MG90S 十字舵盘'], ['servo-horn-single', '单臂舵盘'], ['sg90s', 'SG90S 舵机'],
    ['bracket', '支架'], ['bracket-print', '打印支架'], ['head-print', '打印云台头'], ['head', '云台头'],
  ]
  for (const [id, name] of models) {
    const path = `/models/${id}`
    const response = await page.goto(path)
    expect(response?.status()).toBe(200)
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
    await expect(page.getByRole('link', { name, exact: true })).toHaveAttribute('href', path)
  }
  await page.getByRole('spinbutton', { name: '上耳孔直径' }).fill('2.4')
  await page.reload()
  await expect(page).toHaveURL('/models/head')
  await expect(page.getByRole('spinbutton', { name: '上耳孔直径' })).toHaveValue('2')
  await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
  expect(builds).toEqual([...models.map(([id]) => id), 'head'].map((id) => `/api/models/${id}/preview`))
})

test('unknown model URLs show a recovery link', async ({ page }) => {
  await page.goto('/models/missing')
  await expect(page.getByRole('status')).toHaveText('找不到此零件。')
  await page.getByRole('link', { name: '返回底座' }).click()
  await expect(page).toHaveURL('/models/base-split')
  await expect(page.getByRole('heading', { name: '分体底座', exact: true })).toBeVisible()
})

test('the split base and assembly share the generated horn and connection', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  const initialPreview = page.waitForResponse('**/api/models/base-split/preview')
  await page.goto('/')
  await expect(page).toHaveURL('/models/base-split')
  expect((await initialPreview).ok()).toBe(true)
  await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
  const profile = page.getByRole('combobox', { name: '舵盘型号' })
  const connection = page.getByRole('combobox', { name: '连接方式' })
  const snapClearance = page.getByRole('spinbutton', { name: '卡扣单边间隙' })
  const bolt = page.getByRole('spinbutton', { name: 'M3 螺栓长度' })
  const thickness = page.getByRole('spinbutton', { name: '下层板厚' })
  await expect(profile).toHaveValue('1')
  await expect(connection).toHaveValue('0')
  await expect(snapClearance).toHaveValue('0.25')
  await expect(bolt).toHaveCount(0)
  await expect(thickness).toHaveValue('6.2')
  await page.getByRole('button', { name: '下座', exact: true }).click()
  await expect(page.getByTestId('model-dimensions')).toHaveText('42 × 42 × 6.2 mm')
  await profile.selectOption({ label: '等臂十字舵盘' })
  await connection.selectOption({ label: 'M3 热熔螺母' })
  await expect(bolt).toHaveValue('6')
  await expect(snapClearance).toHaveCount(0)
  await expect(thickness).toHaveValue('5.65')
  await expect(page.getByText('有未生成的修改')).toBeVisible()
  const preview = page.waitForResponse('**/api/models/base-split/preview')
  await page.getByRole('button', { name: '重新生成', exact: true }).click()
  const generated = await (await preview).json()
  expect(generated.parameters).toMatchObject({ horn_profile: 0, connection: 1 })
  expect(generated.parts.filter(({ id }: { id: string }) => id.startsWith('m3_'))).toHaveLength(8)
  await expect(page.getByTestId('model-dimensions')).toHaveText('42 × 42 × 5.65 mm')

  await page.getByRole('button', { name: '导出', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: '导出文件' })
  await expect(dialog.getByRole('checkbox', { name: '下座' })).toBeChecked()
  await expect(dialog.getByRole('checkbox', { name: '上盖' })).not.toBeChecked()
  await dialog.getByRole('button', { name: '取消' }).click()

  await page.getByRole('link', { name: '整机装配', exact: true }).click()
  await expect(page).toHaveURL('/models/gimbal-assembly')
  await expect(profile).toHaveValue('0')
  await expect(connection).toHaveValue('1')
  await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
  await page.getByRole('button', { name: '导出', exact: true }).click()
  dialog = page.getByRole('dialog', { name: '导出文件' })
  await expect(dialog.getByRole('checkbox', { name: 'STEP' })).toBeChecked()
  await expect(dialog.getByRole('checkbox', { name: '3MF' })).toHaveCount(0)
  const request = page.waitForRequest('**/api/exports')
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: '下载', exact: true }).click()
  expect((await request).postDataJSON().models[0].parameters).toMatchObject({ horn_profile: 0, connection: 1 })
  expect((await download).suggestedFilename()).toBe('argus_gimbal_assembly.step')
})

for (const width of [320, 520, 768, 1280]) {
  test('workbench fits viewport at ' + width + 'px', async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await expect(page.getByRole('button', { name: '顶视' })).toBeEnabled()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    if (width < 1024) {
      const canvas = page.getByLabel('分体底座模型', { exact: true })
      expect(await canvas.evaluate((element) => element.clientHeight)).toBeGreaterThan(450)
      const open = page.getByRole('button', { name: '参数', exact: true })
      await open.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('dialog')).toBeVisible()
      await expect(page.getByRole('spinbutton', { name: '底板边长' })).toBeVisible()
      await expect(page.getByRole('combobox', { name: '舵盘型号' })).toHaveValue('1')
      await page.keyboard.press('Escape')
      await expect(open).toBeFocused()
    } else {
      const top = page.getByRole('button', { name: '顶视' })
      await top.focus()
      await page.keyboard.press('Enter')
      await expect(top).toHaveAttribute('aria-pressed', 'true')
    }
  })
}
