// Test-only harness in ignored cache; actual Leaflet/Vue, API and tile fixtures intercepted by Playwright.
const fs = require('node:fs')
const path = require('node:path')
const net = require('node:net')
const { spawn } = require('node:child_process')
const { pathToFileURL } = require('node:url')
const assert = require('node:assert/strict')
const root = path.resolve(__dirname, '../../..')
const frontend = path.join(root, 'frontend')
const output = path.join(root, 'specs/011-gps-ban-do/artifacts/phase3')
const cache = path.join(frontend, 'node_modules/.cache/spec011-phase3-fixture')
const { chromium } = require(path.join(frontend, 'node_modules/.cache/spec009-browser/node_modules/playwright/test'))

async function main() {
  fs.mkdirSync(output, { recursive: true })
  fs.mkdirSync(cache, { recursive: true })
  fs.copyFileSync(path.join(__dirname, 'phase3-harness.html'), path.join(cache, 'index.html'))
  const { build } = await import(pathToFileURL(path.join(frontend, 'node_modules/vite/dist/node/index.js')).href)
  await build({ root: frontend, configFile: path.join(frontend, 'vite.config.js'), base: './',
    build: { outDir: path.join(frontend, 'node_modules/.cache/spec011-phase3-fixture-build'), emptyOutDir: false,
      rollupOptions: { input: path.join(cache, 'index.html') } } })
  await new Promise((resolve, reject) => {
    const probe = net.createServer()
    probe.once('error', reject)
    probe.listen(5180, '127.0.0.1', () => probe.close(resolve))
  })
  const log = fs.openSync(path.join(output, 'vite.log'), 'w')
  const vite = spawn(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5180', '--strictPort'],
    { cwd: frontend, windowsHide: true, stdio: ['ignore', log, log] })
  let browser
  try {
    for (let i = 0; i < 100; i++) {
      if (vite.exitCode !== null) throw new Error('Vite fixture không khởi động')
      try { if ((await fetch('http://127.0.0.1:5180')).ok) break } catch {}
      await new Promise((resolve) => setTimeout(resolve, 100))
    }
    browser = await chromium.launch({ channel: 'chrome', headless: true })
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
      geolocation: { latitude: 21.028511, longitude: 105.804817, accuracy: 12 }, permissions: ['geolocation'] })
    const page = await context.newPage()
    const errors = [], warnings = [], posts = []
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => { if (message.text().includes('[Vue warn]')) warnings.push(message.text()) })
    let scenario = 'fresh', tileError = false, shipment = 1
    const tile = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#f4f7fc"/><path d="M0 128H256M128 0V256" stroke="#d5dfec"/></svg>'
    await page.route('https://tile.openstreetmap.org/**', (route) => tileError ? route.abort('failed') :
      route.fulfill({ status: 200, contentType: 'image/svg+xml', body: tile }))
    await page.route('**/api/v1/**', async (route) => {
      const request = route.request()
      if (request.url().includes('/locations/')) {
        posts.push(request.postDataJSON())
        return route.fulfill({ json: { stored: true }, status: 201 })
      }
      if (request.url().includes('/dispatch/tasks/')) return route.fulfill({ json: { id: 1, status: 'ACTIVE' } })
      if (scenario === 'network') return route.abort('failed')
      if (scenario === 'ended') return route.fulfill({ json: { task: null, location: null } })
      return route.fulfill({ json: { task: { id: shipment, type: 'DELIVERY' }, location: scenario === 'empty' ? null : {
        // Tile lỗi dùng vùng khác để không tái sử dụng ảnh đã ở memory cache của Chrome.
        lat: tileError ? 21.128511 : 21.028511, lng: tileError ? 105.904817 : 105.804817, accuracy: 12,
        recorded_at: new Date(Date.now() - (scenario === 'stale' ? 360000 : 1000)).toISOString(),
        received_at: new Date().toISOString(), stale: scenario === 'stale',
      } } })
    })
    const url = 'http://127.0.0.1:5180/node_modules/.cache/spec011-phase3-fixture/index.html'
    await page.goto(url)
    await page.locator('.leaflet-interactive').waitFor()
    assert.ok(await page.locator('.leaflet-control-attribution').getByRole('link', { name: 'OpenStreetMap' }).isVisible())
    const shot = async (name) => {
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 })
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Tràn ngang')
        await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: true, animations: 'disabled' })
      }
    }
    await shot('map-fresh')
    scenario = 'stale'; shipment++
    await page.evaluate((id) => window.fixture.setShipment(id), shipment)
    await page.getByText('Vị trí đã cũ', { exact: false }).waitFor()
    await shot('map-stale')
    scenario = 'empty'; shipment++
    await page.evaluate((id) => window.fixture.setShipment(id), shipment)
    await page.getByText('Chưa có vị trí được chia sẻ.').waitFor()
    assert.equal(await page.locator('.leaflet-interactive').count(), 0)
    scenario = 'fresh'; tileError = true; shipment++
    await page.evaluate((id) => window.fixture.setShipment(id), shipment)
    await page.getByText('Chưa tải được nền bản đồ.', { exact: false }).waitFor()
    await shot('map-tile-error')
    tileError = false
    await page.getByRole('button', { name: 'Tải lại bản đồ' }).click()
    await page.locator('.leaflet-tile-loaded').first().waitFor()
    scenario = 'network'; shipment++
    await page.evaluate((id) => window.fixture.setShipment(id), shipment)
    await page.getByText('Không kết nối được máy chủ.', { exact: false }).waitFor()
    scenario = 'fresh'
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click()
    await page.locator('.leaflet-interactive').waitFor()
    scenario = 'ended'; shipment++
    await page.evaluate((id) => window.fixture.setShipment(id), shipment)
    await page.getByText('Không còn nhiệm vụ mở để theo dõi vị trí.').waitFor()
    assert.equal(await page.locator('.leaflet-interactive').count(), 0)
    await page.goto(url + '?sharing')
    await page.getByRole('button', { name: 'Bật chia sẻ' }).click()
    await page.getByTestId('sharing-state').filter({ hasText: 'sharing' }).waitFor()
    assert.equal(posts.length, 1)
    assert.equal(posts[0].lat, 21.028511)
    assert.ok(Date.now() - Date.parse(posts[0].recorded_at) < 120000)
    await page.evaluate(() => window.fixture.closeTask())
    await page.getByTestId('sharing-state').filter({ hasText: 'stopped' }).waitFor()
    assert.deepEqual(errors, [])
    assert.deepEqual(warnings, [])
    console.log('PASS real Leaflet: marker/attribution, stale/empty/ended, tile/API errors + retry, 6 screenshots 1440/390; no horizontal overflow')
    console.log('PASS real browser geolocation: explicit start, original timestamp POST, closed task stops; 0 Vue warnings / 0 page errors')
    console.log('API/tile fixtures only; no real backend flow or external tile downloads claimed.')
  } finally {
    await browser?.close()
    if (vite.exitCode === null) {
      vite.kill()
      await new Promise((resolve) => vite.once('exit', resolve))
    }
    fs.closeSync(log)
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
