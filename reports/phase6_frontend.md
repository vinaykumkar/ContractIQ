# ContractIQ — Phase 6 Frontend Report

_Generated: 2026-09-02 · Build ✅ · Lint ✅ · 13/13 vitest ✅ · Browser verification: 0 console errors, 0 page errors._

## Design concept — "Fluid Legal Intelligence"

Deep ink/obsidian base (`--color-ink-950…600` tokens) with deliberate accents: warm ivory text, mint/aqua primary actions, coral reserved for HIGH risk, lavender/amber as supporting hues. Signature atmosphere: fixed aurora-mesh background (three drifting radial blobs, `prefers-reduced-motion` aware), subtle SVG film grain, glass surfaces used sparingly (`ci-glass`), serif display/legal typography (system Iowan/Palatino/Georgia stacks — no downloads), mono for metadata. All colors live as design tokens in `src/index.css` (`@theme`) — a light theme is a token swap away; no raw color values in components.

## Pages (React Router)

| Route | Page |
|---|---|
| `/` | Overview: serif hero, gradient CTA, three "statistic islands" (animated counters, **risk constellation** segmented SVG ring, clause counter with level chips), recent activity from the API, beautiful empty state when DB is empty |
| `/analyze` | Upload workflow state machine: idle → dragging (drag-depth tracking) → uploading → analyzing (honest animated 6-stage workflow — labeled process states, **no fake percentages**) → done → error. Live file metadata; errors mapped to friendly messages |
| `/contracts` | History: search, status chips, risk + sort selects, pagination, hover-revealed delete; rich list rows, not an enterprise table |
| `/contracts/:id` | **Analysis workspace** (most important): two-column — document viewer left, intelligence rail right; mobile switches to Document/Intelligence bottom-sheet tabs |
| `/intelligence` | Model info: availability, state (fine-tuned/baseline), device (CPU/CUDA), risk-methodology notice + disclaimer |

## Major components

`AppShell` (floating nav rail with spring `layoutId` active state, engine indicator) · `AuroraBackground` · `RiskOrb` (segmented arc, animated count-up, glow core, accessible `role="img"` aria-label + numeric readout + text level — never color-only) · **`ClauseIntelligenceMap`** (signature SVG: central Contract hub, 15 clause nodes on two organic rings, connections breathe while analyzing, nodes activate by found/risk, keyboard-clickable with aria labels) · `DocumentViewer` · `ClauseCard`/`ClauseFilters` · `EntityPanel`/`RiskFindingsPanel` · `EmptyState`/`ErrorState` (uses backend error codes, never raw JSON).

## API integration

Isolated in `src/services/api.ts`: `VITE_API_BASE_URL` (default `http://127.0.0.1:8000/api`), timeouts via AbortController, multipart upload, structured error-envelope parsing with human-friendly messages per error code (`ApiError.code`), request-id surfaced in error panels. All endpoints of the Phase 5 contract are consumed. Typed interfaces in `src/types/api.ts` — no widespread `any`. State: plain hooks (`useEngineStatus` polling health, `useAsyncData`) — deliberately no Redux/TanStack.

## Evidence highlighting (exact offsets)

`src/lib/evidence.ts` (pure, unit-tested): `segmentParagraphs` splits text into offset-tracked blocks (long paragraphs split on line boundaries); `splitBlockForEvidence` renders only overlapping paragraphs as segmented ranges — active clause = glowing `.ci-evidence` mark, other found clauses dimmed. Clicking a clause card or a map node sets the active clause and smooth-scrolls the document to the exact `[start_char, end_char)` from the backend — no text re-searching. Copy-evidence interaction on cards.

## Responsive behavior

1440/1920: two-column workspace. Tablet: rail compresses. Mobile (390px verified by screenshot): workspace becomes tabs + bottom sheet, nav becomes a bottom pill, stat islands stack. `prefers-reduced-motion` disables aurora drift, count-ups and pulses.

## Tests / build / verification

- **13 vitest tests** (all passing): error-envelope parsing (friendly messages), backend-offline mapping, RiskOrb accessible labels, clause filter logic + chips, evidence segmentation/highlight mapping (offsets preserved, dim/active/clip cases), empty history state, offline intelligence page.
- `npm run build` ✅ (tsc strict + vite, ~135 kB gzip JS) · `npm run lint` ✅ 0 errors/0 warnings.
- **Browser verification (Playwright, real backend + real model)**: all 4 routes render; full demo story executed — upload → analyze (real engine) → workspace → RiskOrb (score 30/LOW, 2 findings) → click "Governing Law" → exact highlight *"This agreement is governed by the laws of the State of Ohio."* → findings visible → history → reopen same analysis. **0 console errors, 0 page errors.** Screenshots in `frontend/shots/`, raw results in `reports/phase6_browser_verification.json`.

## Bugs found and fixed during verification

1. `api.upload` missing `method: 'POST'` → fetch rejected ("GET cannot have body") — uploads silently failed; fixed + covered by error-parsing test.
2. `segmentParagraphs` offset-doubling bug (paragraph starts miscomputed) — fixed + regression test.
3. framer-motion animating SVG `r` attribute emitted `<circle r="undefined">` console errors — replaced with transform-scale animations.

## Performance considerations

Long contracts: single text node per non-overlapping paragraph (no per-character spans), highlight segments computed only for overlapping blocks, memoized segmentation/filters, `layoutId` shared transitions instead of heavy re-animations, no canvas while reading.

## Known limitations

- Analysis is synchronous → the workflow animation is time-paced decoration, honestly labeled; Phase 7 streaming will make it real.
- Light theme not yet implemented (tokens are ready for it).
- `playwright` stays a devDependency (drives `verify-browser.mjs`); not shipped in the app bundle.
- Demo database contains a few Phase-4/6 smoke contracts (deletable via UI).

## Run commands

```
run_frontend.bat        → http://localhost:5173   (installs deps on first run)
run_contractiq.bat      → backend + frontend in two windows
# or manually:
cd frontend && npm install && npm run dev
```
