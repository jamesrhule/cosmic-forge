# WCAG 2.2 AA Audit Checklist (Tier 5)

Use this as a living per-route checklist. Run automated tools first, then walk through the manual gates.

## Automated

```bash
# In one terminal
bun run dev

# In another
bun x @axe-core/cli http://localhost:3000/ http://localhost:3000/login \
  http://localhost:3000/visualizer http://localhost:3000/pricing \
  http://localhost:3000/status --exit
```

Failures should be added to a `wcag-debt.md` issue list, not silently ignored.

## Manual gates per route

For each route in the app, verify:

### 1. Perceivable
- [ ] All non-text content has a meaningful `alt` (or `alt=""` if decorative).
- [ ] Color contrast ≥ 4.5:1 for normal text, ≥ 3:1 for large text and UI controls (use `npx pa11y` or DevTools).
- [ ] Information is not conveyed by color alone (icons, text, or both).
- [ ] Page works at 200% zoom without horizontal scroll on a 1280-px viewport.

### 2. Operable
- [ ] Every interactive element is reachable with `Tab` in a sensible order.
- [ ] Visible focus indicator on every focusable element (we use `:focus-visible` ring tokens — verify on dark + light).
- [ ] No keyboard trap; `Esc` closes modals, popovers, drawers.
- [ ] Skip-link to `#main` on every page that has nav.
- [ ] Custom controls (sliders, dialogs, menus) match WAI-ARIA Authoring Practices roles + keys.

### 3. Understandable
- [ ] `<html lang>` set (currently hard-coded `en` — switches with `i18next` once integrated app-wide).
- [ ] Form inputs have associated `<label>` or `aria-label`.
- [ ] Error messages are programmatically associated (`aria-describedby`) and reach screen readers (`role="alert"` for live errors).
- [ ] Consistent navigation across routes.

### 4. Robust
- [ ] No duplicate `id`s.
- [ ] Landmarks present: `<header>`, `<nav>`, `<main>`, `<footer>`.
- [ ] Status region for async results (`role="status"` or `aria-live="polite"`).

## Per-route status

| Route             | Last audited | Outcome            | Owner |
|-------------------|--------------|--------------------|-------|
| `/`               | —            | Pending Tier 5     | TBD   |
| `/login`          | —            | Pending Tier 5     | TBD   |
| `/reset-password` | —            | Pending Tier 5     | TBD   |
| `/visualizer`     | —            | Pending Tier 5     | TBD   |
| `/visualizer/:id` | —            | Pending Tier 5     | TBD   |
| `/pricing`        | —            | Pending Tier 5     | TBD   |
| `/status`         | —            | Pending Tier 5     | TBD   |

## CI integration (future)

Add `axe-core` assertions to the Playwright smoke spec in `e2e/smoke.spec.ts` so a regression can never ship green.
