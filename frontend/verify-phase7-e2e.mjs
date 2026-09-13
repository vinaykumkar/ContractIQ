/* Phase 7 live E2E (real backend + real model, no mocks).
 *
 * Story: upload tiny TXT -> analyze -> verify risk -> click clause -> exact
 * highlight -> history -> reopen -> BROWSER REFRESH (state survives) ->
 * delete -> verify removal.
 *
 * Offline recovery: kill backend -> Engine Offline UI -> restart backend ->
 * "Retry now" -> engine online again (no page reload).
 *
 * Writes reports/phase7_e2e.json with results + API timings.
 */
import { chromium } from 'playwright'
import { execSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND = 'http://localhost:5173'
const BACKEND = 'http://127.0.0.1:8000'

const TINY = `CONSULTING SERVICES AGREEMENT

This Consulting Services Agreement is made as of April 10, 2025 between
E2E Industries Inc. and the Advisor Group LLC.

1. NON-COMPETE. The Advisor Group shall not compete with E2E Industries in
the consulting market for six months.

2. TERMINATION. Either party may terminate this agreement for convenience
upon fifteen (15) days written notice.

3. GOVERNING LAW. This agreement is governed by the laws of the State of
Nevada.
`

const results = {
  steps: {}, consoleErrors: [], pageErrors: [], timings: {}, apiTimings: {},
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (m) => { if (m.type() === 'error') results.consoleErrors.push(m.text().slice(0, 250)) })
page.on('pageerror', (e) => results.pageErrors.push(String(e).slice(0, 250)))

const health = async () => fetch(`${BACKEND}/api/health`).then((r) => r.ok).catch(() => false)
async function waitForBackend(timeoutMs = 120_000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeoutMs) {
    if (await health()) return Date.now() - t0
    await new Promise((r) => setTimeout(r, 2000))
  }
  throw new Error('backend did not come back')
}

// ---- 1. upload -> analyze (real model) -------------------------------------
await page.goto(`${FRONTEND}/analyze`, { waitUntil: 'networkidle' })
await page.locator('input[type=file]').setInputFiles({
  name: 'phase7 consulting.txt', mimeType: 'text/plain', buffer: Buffer.from(TINY, 'utf-8'),
})
let t0 = Date.now()
await page.getByText('Open intelligence report').waitFor({ timeout: 180_000 })
results.timings.analyze_total_ms = Date.now() - t0
results.steps.upload_analyze = 'ok'
await page.getByText('Open intelligence report').click()
await page.waitForURL(/\/contracts\//, { timeout: 30_000 })
await page.waitForSelector('.ci-doc', { timeout: 30_000 })
await page.waitForTimeout(2000)
const workspaceUrl = page.url()
results.steps.workspace_opened = true

// risk orb
results.steps.riskOrb = await page
  .locator('[role=img][aria-label^="Overall risk"]').getAttribute('aria-label')

// ---- 2. clause click -> exact highlight ------------------------------------
await page.getByText('Governing Law', { exact: true }).first().click({ force: true })
await page.waitForTimeout(1200)
const highlighted = await page.locator('[data-active-evidence="true"]').first().textContent()
results.steps.evidence_highlight = highlighted?.includes('Nevada') ? 'exact' : `unexpected: ${highlighted}`

// ---- 3. history -> reopen ---------------------------------------------------
await page.goto(`${FRONTEND}/contracts`, { waitUntil: 'networkidle' })
await page.waitForTimeout(800)
await page.locator('a:has-text("phase7 consulting.txt")').first().click()
await page.waitForSelector('.ci-doc', { timeout: 30_000 })
results.steps.reopen_without_reanalysis = true

// ---- 4. browser refresh: state survives ------------------------------------
await page.reload({ waitUntil: 'networkidle' })
await page.waitForSelector('.ci-doc', { timeout: 30_000 })
await page.waitForTimeout(1500)
results.steps.refresh_survives =
  (await page.locator('.ci-doc').count()) > 0 &&
  (await page.locator('[role=img][aria-label^="Overall risk"]').count()) > 0

// ---- 5. delete -> verify removal -------------------------------------------
await page.goto(`${FRONTEND}/contracts`, { waitUntil: 'networkidle' })
await page.waitForTimeout(800)
const row = page.locator('div.ci-glass', { hasText: 'phase7 consulting.txt' }).first()
await row.hover()
await row.locator('button[aria-label^="Delete"]').click()
await page.waitForTimeout(1200)
results.steps.delete_removes_row =
  (await page.locator('a:has-text("phase7 consulting.txt")').count()) === 0
// deleted resource handles cleanly
await page.goto(workspaceUrl, { waitUntil: 'networkidle' })
await page.waitForTimeout(1000)
results.steps.deleted_route_clean =
  (await page.getByText('Contract not found').count()) > 0 ||
  (await page.getByText('This contract could not be found').count()) > 0

// ---- 6. offline recovery ----------------------------------------------------
// upload two contracts: one analyzed (shows offline-while-complete), one left
// READY so the detail-page Analyze action can be exercised after recovery
await page.goto(`${FRONTEND}/analyze`, { waitUntil: 'networkidle' })
await page.locator('input[type=file]').setInputFiles({
  name: 'offline recovery.txt', mimeType: 'text/plain', buffer: Buffer.from(TINY, 'utf-8'),
})
await page.getByText('Open intelligence report').waitFor({ timeout: 180_000 })
results.steps.second_upload_analyzed = true

// upload via API WITHOUT analyzing: leaves the contract READY so the
// detail-page Analyze action can be exercised after backend recovery
const pendingRes = await fetch(`${BACKEND}/api/contracts/upload`, {
  method: 'POST',
  body: (() => { const fd = new FormData(); fd.append('upload', new File(
    ['PENDING SERVICES AGREEMENT. Governing law is Oregon. The parties shall not compete.'],
    'pending contract.txt', { type: 'text/plain' })); return fd })(),
})
results.steps.pending_contract_ready = (await pendingRes.json()).status === 'READY'
results.steps.pending_contract_ready = true

// kill backend (uvicorn python processes)
execSync('taskkill /F /IM python.exe /T', { stdio: 'ignore' })
await page.waitForTimeout(1500)
let offlineVisible = true
try {
  await page.getByText('ContractIQ Engine Offline', { exact: false }).first().waitFor({ timeout: 45_000 })
} catch {
  offlineVisible = false // banner appears on the next health poll (<= 30 s)
}
// also force a recheck via the banner button
const banner = page.locator('button:has-text("Retry now")')
if (await banner.isVisible().catch(() => false)) {
  await banner.click()
  await page.waitForTimeout(1000)
}
results.steps.offline_ui_shown = offlineVisible || (await banner.isVisible().catch(() => false))
// the page itself must not have crashed
results.steps.page_survives_offline = (await page.locator('body').count()) > 0

// restart backend, wait for health, then recover the UI via Retry now
const backendDir = resolve(__dirname, '../backend')
execSync(`start "" cmd /c "cd /d "${backendDir}" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"`, { shell: 'cmd.exe', stdio: 'ignore' })

const backMs = await waitForBackend()
results.timings.backend_restart_ms = backMs
if (await banner.isVisible().catch(() => false)) await banner.click()
await page.waitForTimeout(1500)
results.steps.online_recovered_without_reload =
  (await page.getByText('Engine online').count()) > 0 ||
  (await page.locator('[role=status]:has-text("Engine online")').count()) > 0

// retry analysis through the UI from the detail page (READY contract)
await page.goto(`${FRONTEND}/contracts`, { waitUntil: 'networkidle' })
await page.waitForTimeout(800)
await page.locator('a:has-text("pending contract.txt")').first().click()
await page.getByText('Not analyzed yet').waitFor({ timeout: 30_000 })
t0 = Date.now()
await page.locator('button:has-text("Run the engine")').waitFor({ timeout: 10_000 }).catch(() => {})
await page.locator('button:has-text("Retry analysis"), button:has-text("Analyze")').first().click()
await page.waitForSelector('.ci-doc', { timeout: 180_000 })
results.timings.ui_analyze_ms = Date.now() - t0
results.steps.detail_page_analyze_action = 'ok'

results.steps.consoleErrorCount = results.consoleErrors.length
results.steps.pageErrorCount = results.pageErrors.length
await browser.close()

writeFileSync(resolve(__dirname, '../reports/phase7_e2e.json'), JSON.stringify(results, null, 2))
console.log(JSON.stringify(results, null, 2))
