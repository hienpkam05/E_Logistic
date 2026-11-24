const { chromium, expect } = require('../../../frontend/node_modules/.cache/spec009-browser/node_modules/playwright/test')
const fs = require('node:fs')
const path = require('node:path')
const data = JSON.parse(fs.readFileSync(0, 'utf8'))

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const failures = []
  const contexts = []
  const base = 'http://127.0.0.1:5180'
  async function login(username) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    contexts.push(context)
    const page = await context.newPage()
    page.on('pageerror', e => failures.push(e.message))
    page.on('console', msg => { if (/\[Vue.*warn/i.test(msg.text())) failures.push(msg.text()) })
    await page.goto(base + '/login')
    await page.getByLabel('Tên đăng nhập', { exact: false }).fill(username)
    await page.getByLabel('Mật khẩu', { exact: false }).fill(data.password)
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
    await page.waitForURL(url => !url.pathname.includes('login'))
    return page
  }
  async function search(page, code) {
    await page.getByLabel('Mã vận đơn hoặc mã yêu cầu', { exact: false }).fill(code)
    await page.getByRole('button', { name: 'Tra cứu', exact: true }).click()
    await expect(page.getByText('Đang tra cứu vận đơn…')).toHaveCount(0)
  }
  async function shot(page, name) {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 })
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      await page.screenshot({ path: path.join(data.output, `${name}-${width}.png`), fullPage: true, animations: 'disabled' })
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`Overflow ${name}/${width}`)
    }
  }
  try {
    const shop = await login(data.shop)
    await shop.goto(base + '/tracking')
    await expect(shop.locator('#tracking-title')).toBeVisible()
    await search(shop, ' ' + data.code.toLowerCase() + ' ')
    await expect(shop.locator('#lookup-result-title')).toHaveText(data.code)
    await shot(shop, 'shop-result')
    await shop.getByRole('link', { name: 'Lịch sử vận chuyển', exact: true }).click()
    await expect(shop.locator('#shipment-history .events__item').first()).toBeVisible()
    await expect(shop.locator('#shipment-history')).toContainText('Lần giao 2')
    await expect(shop.locator('#shipment-history')).toContainText('Đổi Shipper')
    await expect(shop.locator('#shipment-history')).toContainText('Lần lấy 1')
    const inView = await shop.locator('#shipment-history').evaluate(el => {
      const top = el.getBoundingClientRect().top
      return top >= 68 && top < innerHeight
    })
    if (!inView) throw new Error('History hash did not scroll into view')
    await shop.getByLabel('Thứ tự lịch sử').selectOption('created_at')
    await expect(shop.locator('#shipment-history .events__item').first()).toContainText('Tạo yêu cầu')
    await shot(shop, 'shop-history')
    await shop.goto(base + '/tracking')
    await search(shop, data.foreign)
    await expect(shop.getByRole('heading', { name: 'Không tìm thấy vận đơn phù hợp', exact: true })).toBeVisible()
    await expect(shop.locator('#lookup-result-title')).toHaveCount(0)
    await shot(shop, 'shop-not-found')
    await search(shop, data.request)
    await expect(shop.locator('#lookup-result-title')).toHaveText(data.request)
    await shop.getByRole('link', { name: 'Lịch sử vận chuyển', exact: true }).click()
    await expect(shop.getByText('Chưa phát sinh vận chuyển', { exact: false })).toBeVisible()
    await shop.goto(base + '/tracking?code=' + data.code)
    await expect(shop.locator('#lookup-result-title')).toHaveText(data.code)
    await shop.route('**/api/v1/shipments/lookup/**', route => route.abort())
    await search(shop, data.request)
    await expect(shop.getByRole('button', { name: 'Thử lại', exact: true })).toBeVisible()
    await expect(shop.getByLabel('Mã vận đơn hoặc mã yêu cầu', { exact: false })).toHaveValue(data.request)
    await shop.unroute('**/api/v1/shipments/lookup/**')
    await shop.getByRole('button', { name: 'Thử lại', exact: true }).click()
    await expect(shop.locator('#lookup-result-title')).toHaveText(data.request)
    console.log('PASS Shop: own code, request code, foreign 404, history labels/order/hash, URL restore and network retry')

    const staff = await login(data.admin)
    await staff.goto(base + '/tracking?code=' + data.foreign)
    await expect(staff.locator('#lookup-result-title')).toHaveText(data.foreign)
    await expect(staff.locator('dt').filter({ hasText: /^Shop$/ })).toBeVisible()
    await expect(staff.getByRole('link', { name: 'Xem chi tiết', exact: true })).toHaveAttribute('href', /staff\/shipments/)
    await shot(staff, 'staff-result')
    const shipper = await login(data.shipper)
    await shipper.goto(base + '/tracking')
    await shipper.waitForURL('**/shipper')
    await expect(shipper.getByRole('link', { name: 'Tra cứu vận đơn', exact: true })).toHaveCount(0)
    if (failures.length) throw new Error(JSON.stringify(failures))
    console.log('PASS staff all shops / Shipper route denied / 8 screenshots / zero Vue warnings or page errors')
  } finally {
    await Promise.all(contexts.map(c => c.close()))
    await browser.close()
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
