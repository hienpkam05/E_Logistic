const fs = require('node:fs')
const path = require('node:path')
const root = path.resolve(__dirname, '../../..')
const { chromium, expect: baseExpect } = require(path.join(root, 'frontend/node_modules/.cache/spec009-browser/node_modules/playwright/test'))
const expect = baseExpect.configure({ timeout: 25000 })
const data = JSON.parse(fs.readFileSync(0, 'utf8'))
const base = 'http://127.0.0.1:5180'
const tile = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#f4f7fc"/><path d="M0 128H256M128 0V256" stroke="#d5dfec"/></svg>'

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const errors = [], warnings = [], posts = []
  async function login(username, latitude = 21.028511) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
      geolocation: { latitude, longitude: 105.804817, accuracy: 12 }, permissions: ['geolocation'] })
    // Tile fixture độc lập; mọi API vẫn đi qua session/CSRF thật tới Django.
    await context.route('https://tile.openstreetmap.org/**', (route) => route.fulfill({ status: 200, contentType: 'image/svg+xml', body: tile }))
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (msg) => { if (msg.text().includes('[Vue warn]')) warnings.push(msg.text()) })
    page.on('request', (request) => { if (request.method() === 'POST' && request.url().endsWith('/locations/')) posts.push(request.postDataJSON()) })
    await page.goto(base + '/login')
    await page.getByLabel('Tên đăng nhập', { exact: false }).fill(username)
    await page.getByLabel('Mật khẩu', { exact: false }).fill(data.password)
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
    await page.waitForURL((url) => !url.pathname.includes('login'))
    return page
  }
  const api = (page, method, url, body) => page.evaluate(async ({ method, url, body }) => {
    const csrf = document.cookie.split('; ').find((part) => part.startsWith('csrftoken='))?.slice('csrftoken='.length)
    const response = await fetch('/api/v1' + url, { method, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrf || '') },
      body: body === undefined ? undefined : JSON.stringify(body) })
    const result = await response.json()
    if (!response.ok) throw new Error(JSON.stringify({ status: response.status, result }))
    return result
  }, { method, url, body })
  async function shot(page, name) {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 })
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`Tràn ngang ${name}/${width}`)
      await page.screenshot({ path: path.join(data.output, `${name}-${width}.png`), fullPage: true, animations: 'disabled' })
    }
  }
  const directions = async (page, destination) => {
    const link = page.getByRole('link', { name: 'Chỉ đường bằng Google Maps (mở tab mới)' })
    await expect(link).toBeVisible()
    const url = new URL(await link.getAttribute('href'))
    expect([...url.searchParams.keys()]).toEqual(['api', 'destination'])
    expect(url.searchParams.get('destination')).toBe(destination)
  }
  try {
    const shipper = await login(data.shipper)
    const shop = await login(data.shop)
    const staff = await login(data.admin)
    await shipper.goto(base + `/shipper/tasks/${data.pickup}`)
    await directions(shipper, '12 Hàng Bạc, Phường Thử')
    await expect(shipper.getByText('Shop của đơn và Nhân viên xem được điểm gần nhất.', { exact: false })).toBeVisible()
    expect(posts).toHaveLength(0)
    await shop.goto(base + `/shop/shipments/${data.pickupShipment}`)
    await expect(shop.getByText('Chưa có vị trí được chia sẻ.')).toBeVisible()
    await shipper.getByRole('button', { name: 'Bật chia sẻ vị trí', exact: true }).click()
    await expect(shipper.getByText('Đang chia sẻ vị trí', { exact: true })).toBeVisible()
    expect(posts).toHaveLength(1)
    expect(posts[0].lat).toBe(21.028511)
    await shot(shipper, 'shipper-sharing')
    await shop.reload()
    await expect(shop.locator('.leaflet-interactive')).toHaveCount(1)
    await expect(shop.getByText('Tọa độ: 21.028511', { exact: false })).toBeVisible()
    await shot(shop, 'shop-location')
    await staff.goto(base + `/staff/shipments/${data.pickupShipment}`)
    await expect(staff.locator('.leaflet-interactive')).toHaveCount(1)
    await shot(staff, 'staff-location')
    await shipper.getByRole('button', { name: 'Đã lấy hàng', exact: true }).click()
    await shipper.getByRole('button', { name: 'Tôi đã nhận đủ hàng', exact: true }).click()
    await expect(shipper.locator('.location-sharing')).toHaveCount(0)
    await expect(shop.locator('.live-map')).toBeHidden()
    expect((await api(shop, 'GET', `/shipments/${data.pickupShipment}/location/`)).location).toBeNull()
    await shop.goto(base + `/shop/shipments/${data.foreign}`)
    await expect(shop.getByRole('heading', { name: 'Không tìm thấy vận đơn' })).toBeVisible()
    await staff.goto(base + `/staff/shipments/${data.foreign}`)
    await expect(staff.getByText('Chưa có vị trí được chia sẻ.')).toBeVisible()
    await shipper.goto(base + `/shipper/tasks/${data.returning}`)
    await directions(shipper, data.hub)
    await shipper.goto(base + `/shipper/tasks/${data.delivery}`)
    await directions(shipper, '5 Đội Cấn, Phường Thử')
    await shipper.getByRole('button', { name: 'Bật chia sẻ vị trí', exact: true }).click()
    await expect(shipper.getByText('Đang chia sẻ vị trí', { exact: true })).toBeVisible()
    let shipment = await api(staff, 'GET', `/shipments/${data.deliveryShipment}/`)
    await api(staff, 'POST', `/shipments/${data.deliveryShipment}/swap-shipper/`,
      { shipper_id: data.otherId, reason: 'Kiểm GPS đổi người', updated_at: shipment.updated_at })
    await expect(shipper.getByText('Đưa hàng về để bàn giao', { exact: true })).toBeVisible()
    await directions(shipper, data.hub)
    await expect(shipper.locator('.cod-card')).toHaveCount(0)
    await shot(shipper, 'shipper-swap')
    await shop.goto(base + `/shop/shipments/${data.deliveryShipment}`)
    await expect(shop.locator('.leaflet-interactive')).toHaveCount(1)
    shipment = await api(staff, 'GET', `/shipments/${data.deliveryShipment}/`)
    await api(staff, 'POST', `/shipments/${data.deliveryShipment}/confirm-swap-handover/`,
      { handed_over: true, discrepancy_note: '', updated_at: shipment.updated_at })
    await expect(shipper.locator('.location-sharing')).toHaveCount(0)
    await expect(shipper.getByRole('link', { name: 'Chỉ đường bằng Google Maps (mở tab mới)' })).toHaveCount(0)
    await expect(shop.getByText('Chưa có vị trí được chia sẻ.')).toBeVisible()
    const state = await api(shop, 'GET', `/shipments/${data.deliveryShipment}/location/`)
    expect(state.location).toBeNull()
    expect(state.task.id).not.toBe(data.delivery)
    const newShipper = await login(data.other, 21.038511)
    await newShipper.goto(base + `/shipper/tasks/${state.task.id}`)
    await newShipper.getByRole('button', { name: 'Bật chia sẻ vị trí', exact: true }).click()
    await expect(newShipper.getByText('Đang chia sẻ vị trí', { exact: true })).toBeVisible()
    await shop.reload()
    await expect(shop.getByText('Tọa độ: 21.038511', { exact: false })).toBeVisible()
    await shot(shop, 'shop-new-shipper')
    await newShipper.getByRole('button', { name: 'Tắt chia sẻ vị trí', exact: true }).click()
    await expect(newShipper.getByText('Đã dừng chia sẻ vị trí', { exact: true })).toBeVisible()
    expect(errors).toEqual([])
    expect(warnings).toEqual([])
    console.log('PASS actual app/session/CSRF/PostgreSQL: explicit sharing -> saved GPS -> Shop/NV Leaflet; closed task stops and hides old point')
    console.log('PASS pickup/delivery/return/swap directions; pending handover health update -> hub, confirmed replacement stops old sharing, new task starts empty then shows new owner point')
    console.log('PASS Shop foreign order denied; 10 screenshots 1440/390, no horizontal overflow; 0 Vue warnings / 0 page errors')
    console.log('Only tiles and geolocation emulated; all business APIs real. Google Maps URL verified without external navigation.')
  } finally { await browser.close() }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
