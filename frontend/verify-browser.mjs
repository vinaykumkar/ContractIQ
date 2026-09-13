/* Phase 6 browser verification (Playwright, headless).
 * Visits all major routes with console monitoring, then runs the demo story:
 * upload a tiny contract -> analyze -> open workspace -> click a clause ->
 * verify exact evidence highlight -> check findings -> back to history.
 * Writes reports/phase6_browser_verification.json.
 */
import { chromium } from 'playwright'
import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRONTEND = process.env.CIQ_FRONTEND ?? 'http://localhost:5173'
const BACKEND = process.env.CIQ_BACKEND ?? 'http://127.0.0.1:8000'

const TINY = `VERIFICATION SERVICES AGREEMENT

This Verification Services Agreement is made as of March 5, 2025 between
Playwright Industries Inc. and the Tester Group LLC.

1. NON-COMPETE. The Tester Group shall not compete with Playwright
Industries in the verification market for one year.

2. TERMINATION. Either party may terminate this agreement for convenience
upon ten (10) days written notice.

3. GOVERNING LAW. This agreement is governed by the laws of the State of
Ohio.
`

const results = { routes: {}, consoleErrors: [], pageErrors: [], flow: {}, screenshots: [] }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (msg) => {
  if (msg.type() === 'error') results.consoleErrors.push(msg.text().slice(0, 300))
})
page.on('pageerror', (err) => results.pageErrors.push(String(err).slice(0, 300)))

// ---- route sweep ----------------------------------------------------------
for (const route of ['/', '/analyze', '/contracts', '/intelligence']) {
  await page.goto(FRONTEND + route, { waitUntil: 'networkidle' })
  await page.waitForTimeout(700)
  results.routes[route] = {
    title: await page.title(),
    heading: await page.locator('h1').first().textContent().catch(() => null),
  }
  if (route === '/') await page.screenshot({ path: 'shots/overview.png' })
  if (route === '/intelligence') await page.screenshot({ path: 'shots/intelligence.png' })
}
results.screenshots.push('shots/overview.png', 'shots/intelligence.png')

// ---- demo flow ------------------------------------------------------------
const fileInput = page.locator('input[type=file]')
await page.goto(FRONTEND + '/analyze', { waitUntil: 'networkidle' })
await fileInput.setInputFiles({ name: 'verification agreement.txt',
  mimeType: 'text/plain', buffer: Buffer.from(TINY, 'utf-8') })
results.flow.uploaded = true

// wait until analysis completes (done screen) then open the workspace
await page.getByText('Open intelligence report').waitFor({ timeout: 180_000 })
await page.getByText('Open intelligence report').click()
await page.waitForURL(/\/contracts\//, { timeout: 30_000 })
results.flow.workspaceUrl = page.url()
await page.waitForSelector('.ci-doc', { timeout: 30_000 })
await page.waitForTimeout(2500) // let orb/map animations settle
await page.screenshot({ path: 'shots/workspace.png' })
results.screenshots.push('shots/workspace.png')

// risk orb readout
results.flow.riskOrb = await page.locator('[role=img][aria-label^="Overall risk"]').getAttribute('aria-label')

// click a clause card containing "Governing Law" and verify highlight
const governingCard = page.getByText('Governing Law', { exact: true }).first()
await governingCard.click({ force: true }) // node pulses continuously (animation)
await page.waitForTimeout(1200)
const active = await page.locator('[data-active-evidence="true"]').count()
results.flow.governingLawHighlight = active > 0
results.flow.governingLawText = active
  ? await page.locator('[data-active-evidence="true"]').first().textContent()
  : null
await page.screenshot({ path: 'shots/evidence-highlight.png' })
results.screenshots.push('shots/evidence-highlight.png')

// findings visible?
results.flow.findingsCount = await page.locator('text=+').count()

// back to history and reopen
await page.goto(FRONTEND + '/contracts', { waitUntil: 'networkidle' })
await page.waitForTimeout(800)
results.flow.historyCount = await page.locator('a:has-text("verification agreement.txt")').count()
if (results.flow.historyCount > 0) {
  await page.locator('a:has-text("verification agreement.txt")').first().click()
  await page.locator('.ci-doc').or(page.getByText('No completed analysis yet')).waitFor({ timeout: 30_000 })
  results.flow.reopened = true
}
results.flow.consoleErrorCount = results.consoleErrors.length
results.flow.pageErrorCount = results.pageErrors.length

await browser.close()
writeFileSync(resolve(__dirname, '../reports/phase6_browser_verification.json'),
  JSON.stringify(results, null, 2))
console.log(JSON.stringify(results, null, 2))
