## 2026-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2026-04-25 - Add loading spinners for intensive CLI calculations
**Learning:** For interactive CLI tools, computationally intensive tasks like grid-search optimizations and sweet-spot analysis can feel unresponsive to the user. Adding simple micro-interactions like a loading spinner significantly improves perceived responsiveness.
**Action:** Always wrap calculation-heavy or blocking synchronous functions in `rich.console.status` to indicate progress, not just network IO. Keep error-handling try/except outside the `with console.status()` block so error panels render correctly.

## 2026-05-15 - [Manage expectations for instantaneous tasks]
**Learning:** When making UX improvements to the CLI, wrapping non-instantaneous compute tasks (even fast ones taking under a second) in a visual indicator like `rich.console.status` manages user expectations and prevents the application from feeling frozen. Hardcoded UI strings must be avoided to ensure proper localization.
**Action:** Added `status.resolving` and `status.generating_schedule` localized strings to wrap the `resolve` and `build_amortization_schedule` methods.

## 2026-05-19 - Group sequential CLI spinners to prevent UI stutter
**Learning:** Sequential calls to `with console.status("...")` cause the spinner to disappear and reappear between tasks, resulting in UI stutter when tasks are fast but not instantaneous.
**Action:** When executing a contiguous chain of synchronous tasks, group them inside a single `with console.status(...) as status:` block and use `status.update("...")` to change the message seamlessly without visual interruptions. Keep error handling robust by using state variables (like `params = None` before the block) to identify which step failed if they raise the same exception type.

## 2026-05-20 - Add confirmation dialogs and helpful empty states
**Learning:** For destructive CLI commands like `rates clear`, a simple confirmation dialog prevents accidental data loss and improves user confidence. Also, empty states (e.g., in `rates list`) should not be dead ends—they should provide users with a clear call-to-action on what command to run next.
**Action:** When creating CLI tools that alter state, add `--yes` flags and `click.confirm()` prompts for destructive actions. Ensure all "empty" states provide actionable guidance.

## 2026-05-20 - Replace text loading states with visual spinners
**Learning:** Using simple text like `...` or `Submitting` for async web operations looks unpolished and can cause slight layout shifts depending on font rendering. An animated SVG spinner provides standard, recognizable feedback that an operation is taking place, making the UI feel smoother and more responsive.
**Action:** When working on async web forms, always use standard visual progress indicators (like an SVG spinner) instead of text fallbacks, and ensure the button layout (e.g. `flex justify-center min-h-`) prevents layout shift when swapping text for the spinner.

## 2026-05-24 - Add focus visible styles to interactive elements
**Learning:** Many interactive elements (like icon buttons or toggles) lack explicit focus indicators, making keyboard navigation difficult for visually impaired users.
**Action:** Always add explicit `focus-visible` utility classes (e.g., `focus-visible:ring-2`) to all interactive elements to ensure clear keyboard accessibility.

## 2026-05-23 - Add missing input associations in complex forms
**Learning:** In complex interactive UI panels (like advanced settings, overrides, or custom what-if scenarios), secondary inputs often miss proper label associations (`id` + `htmlFor`), breaking accessibility for screen readers and reducing click targets.
**Action:** Always verify that every input element inside a form or configuration panel has a unique `id` explicitly associated with an `htmlFor` attribute on its corresponding label, even if the element is deeply nested or part of an optional override menu.

## 2026-05-25 - Add aria-labels alongside visual loading spinners
**Learning:** When replacing text loading states with visual spinners to avoid layout shift, the `svg` alone is not announced by screen readers (especially since it often has `aria-hidden="true"`). This causes a regression in accessibility during async operations.
**Action:** Always add an explicit dynamic `aria-label` to the button itself (e.g., `aria-label={loading ? t('aria.loading') : defaultText}`) when swapping text for a loading spinner.

## 2026-05-26 - Add ARIA label and prevent layout shift for dynamic buttons
**Learning:** When replacing text with a visual loading spinner in a button (like "Refresh live rate"), adding dynamic `aria-label` is crucial for accessibility. Setting minimum width (`min-w-`) and height (`min-h-`) classes along with flex centering prevents layout shifts when the content changes from text to the narrower SVG.
**Action:** Use fixed-minimum dimensions and dynamic `aria-label` on buttons when substituting their inner text with status indicators (like Spinners).

## 2026-05-28 - Add browser confirmation dialog for destructive actions
**Learning:** Users can accidentally click the "Delete" button when managing their history or settings. Relying on an immediate destructive action without confirmation is a poor UX choice that leads to frustration.
**Action:** Wrap all destructive frontend API calls in `window.confirm()` dialogs with localized strings so users have a chance to cancel accidental clicks before the state is irreversibly altered.

## 2026-06-01 - [Accessible Table Sorting Headers]
**Learning:** Found a common accessibility anti-pattern where an `onClick` event is attached directly to a `<th>` element to handle table sorting. This prevents keyboard users from focusing and activating the header, and lacks the necessary `aria-sort` state for screen readers.
**Action:** When implementing sortable columns, always wrap the header's contents in a native `<button>` to restore natural keyboard navigation, and add `aria-sort="ascending|descending|none"` to the wrapping `<th>` to accurately announce the sort state.

## 2026-06-02 - [Native details and summary accessibility]
**Learning:** Found a common accessibility anti-pattern where `aria-expanded` and `aria-controls` are manually added to native `<summary>` elements. Native HTML `<details>` and `<summary>` elements automatically handle their own expanded/collapsed states for screen readers, and modifying them is considered an accessibility anti-pattern that can confuse assistive technologies.
**Action:** Do not manually add `aria-expanded` or `aria-controls` to native HTML `<details>` and `<summary>` elements. Rely on the browser's built-in accessibility features for these tags.

## 2026-06-03 - [Replace text loading state with visual spinner in refresh button]
**Learning:** Found an accessibility and UX issue in the rates table refresh button where clicking refresh simply changes the text to 'Refreshing...'. This can cause layout shifts and lacks proper ARIA labels. Adding an animated SVG spinner with a dynamic `aria-label` improves accessibility and perceived responsiveness, while enforcing min-width and min-height on the button prevents layout jumps.
**Action:** Always replace basic text loading states with visual SVG spinners, add dynamic `aria-label` for screen readers, and enforce structural boundaries (e.g. `min-w`, `min-h`) on buttons to prevent layout shift during loading states.

## 2026-06-09 - [Replace text loading state with visual spinner in load more button]
**Learning:** Replacing text loading states (e.g. 'Loading...') with visual spinners in pagination/load more buttons prevents layout shift and provides standard, recognizable feedback. Dynamic `aria-label` ensures screen reader compatibility, and using `inline-flex` alongside `min-h` and `min-w` maintains the button's layout within centered parent containers.
**Action:** Always replace basic text loading states with visual SVG spinners, add dynamic `aria-label` for screen readers, and enforce structural boundaries (e.g. `inline-flex`, `min-w`, `min-h`) on pagination/load more buttons to prevent layout shift during async operations.

## 2026-06-10 - [Improve accessibility of form elements and visual loading feedback]
**Learning:** Text-based loading states inside buttons can cause slight visual layout shifts during state transitions and lack proper screen reader communication without dynamic `aria-label` attributes. Additionally, inputs that miss their matching `htmlFor` attributes on corresponding `<label>` tags break form accessibility for screen-reader users, and missing `focus-visible` states make keyboard navigation impossible.
**Action:** When adding micro-UX enhancements to forms, always replace text loading states with an SVG spinner and use `aria-label` for screen reader communication. Also, always verify `id` and `htmlFor` matches on input-label pairs, and add `focus-visible:ring-2` to buttons to ensure full accessibility support.

## 2026-06-22 - [Apply focus-visible and spinner patterns to all panels consistently]
**Learning:** Focus-visible fixes and loading spinner patterns applied to one component must be audited across all sibling components. EarlyRepaymentPanel, OpportunityCostPanel, and RefinancingBreakEvenPanel all shared the same underlined toggle button pattern without focus-visible, and WhatIfPanel had a text loading state that needed the spinner treatment.
**Action:** After any accessibility or UX improvement to a single panel component, grep for identical className patterns across all panel components and apply the fix uniformly. Never assume a change to one panel covers the rest.

## 2026-06-25 - [Apply focus-visible pattern to auth page button]
**Learning:** The Auth page's primary submit button lacked `focus-visible` styles, making keyboard navigation difficult. It's critical to ensure all form buttons consistently implement the application's focus states (`focus-visible:ring-2 focus-visible:ring-offset-2 ...`).
**Action:** Added proper `focus-visible` utility classes to the auth form button and will remember to audit standalone pages (like auth) when applying global accessibility patterns.

## 2026-07-04 - [Apply focus-visible and loading states to inline secondary actions]
**Learning:** Secondary or inline action flows (like generating/revoking share tokens in history lists) often miss standard UX patterns applied to primary forms, leading to layout shifts during async operations and poor keyboard accessibility.
**Action:** When auditing list or table views, specifically check inline expansion panels (like share or edit flows) to ensure buttons use layout constraints (`min-w`, `min-h`), visual SVG spinners with `aria-label` for loading states, and explicit `focus-visible` classes for keyboard navigation.

## 2026-07-08 - [Add aria-expanded and aria-controls to custom panel toggle buttons]
**Learning:** Custom UI panels that toggle visibility using a standard `<button>` lack ARIA state, making it impossible for screen reader users to know the panel state or what content the button controls. Use React's `useId()` hook (not hardcoded strings) to generate collision-safe IDs when the component may render multiple times on the same page.
**Action:** Always add `aria-expanded={boolean}` and `aria-controls={contentId}` to toggle buttons with `const contentId = useId()`, and add `id={contentId}` to the target container. When replacing text loading states in non-button elements, use an SVG spinner with `aria-live="polite"` and `aria-busy="true"` on the wrapper.

## 2026-07-16 - [Add focus-visible pattern to dynamic state toggles]
**Learning:** Dynamic toggle buttons (like metric selectors that map over an array of states) can easily omit the global `focus-visible` classes if the base string isn't careful, breaking keyboard navigation for those interactive elements.
**Action:** Always verify that mapped or dynamic buttons still include the standard `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2` classes in their shared className base.

## 2026-07-26 - [Replace hardcoded aria-label strings with localized keys]
**Learning:** Hardcoding aria-label strings like "Close" in UI components creates accessibility issues for non-English users, as screen readers announce the English word regardless of the application's current locale.
**Action:** Always avoid hardcoded UI strings in aria-labels. Create and use existing localization utilities (e.g., `aria-label={t('your.key')}`) and add new localized keys to the appropriate translation dictionaries (e.g., `web/lib/i18n.tsx`) to ensure proper localization.

## 2026-08-01 - Add screen-reader-only labels to visually implicit inputs
**Learning:** When an input field's purpose is visually implied by its layout but lacks a visible text label (e.g., inline forms, search bars, or API key generators), explicitly provide an accessible name for screen readers. Simply adding a placeholder is not sufficient for accessibility standards.
**Action:** Always provide an accessible name for inputs by adding a `<label>` with Tailwind's `sr-only` class, correctly mapped to the input via `htmlFor` and `id`, ensuring screen reader support without disrupting the visual design.

## 2026-08-01 - [Add browser confirmation dialog for share token revocation]
**Learning:** Found a missing confirmation dialog on the "Revoke Link" button in the history list. Destructive actions on secondary workflows (like share panels) are easily missed and should follow the same pattern as primary deletes. Without confirmation, users might accidentally invalidate active sharing links.
**Action:** When implementing destructive frontend actions (like revoking tokens or deleting items), always wrap the API calls in `window.confirm()` dialogs with localized text to prevent accidental data loss and improve user experience. Update corresponding Playwright tests with a dialog handler (e.g. `page.once('dialog', dialog => dialog.accept())`) before the trigger action.

## 2026-08-01 - [Apply focus-visible to inline secondary actions consistently]
**Learning:** Inline secondary actions like "Cancel" or "Copy" in list or settings pages often miss the global `focus-visible` classes during initial development, making them inaccessible to keyboard users.
**Action:** Always verify every button in secondary flows (like edit menus, settings lists) includes standard `focus-visible:outline-none focus-visible:ring-2` styles.

## 2026-08-05 - Add explicit labels to list selection checkboxes
**Learning:** While `aria-label` on checkboxes works for basic accessibility, explicit `<label>` elements with `htmlFor` matching the input's `id` provide the most robust support across all screen readers. When checkboxes are used in list items (like for multi-selection) without visible text labels, wrapping or preceding them with a screen-reader-only (`sr-only`) label improves accessibility without affecting layout.
**Action:** Always provide an explicit `<label className="sr-only">` properly mapped via `htmlFor` and `id` for standalone selection checkboxes in lists, even if an `aria-label` is present, to ensure maximum compatibility.

## 2026-08-09 - A `<label>` with no control is invisible to assistive tech
**Learning:** Sweeping the whole `web/` tree for the checkbox-label pattern surfaced two variants the per-component pass missed. A group heading written as `<label>` with neither `htmlFor` nor a wrapped control (the currency-display radios in `preferences/page.tsx`) is announced by nothing — the radios had no group name at all. And an `sr-only` label is still user-facing copy: `auth/page.tsx` shipped a hardcoded English `Email` that never switched to FR.
**Action:** When a heading labels a *set* of controls rather than one, use a `<span id>` plus `role="radiogroup" aria-labelledby` (or `<fieldset>`/`<legend>`) — never a bare `<label>`. Give each option an `id` and point the wrapping `<label>` at it with `htmlFor`. Run every `sr-only` label through `t()` like any other string.

## 2026-08-16 - Add aria-live and prevent layout shift for transient text changes
**Learning:** When a button's text changes temporarily to indicate a transient state (like "Copy" to "Copied!"), screen readers will not announce the change unless `aria-live="polite"` is used. Furthermore, changing string lengths can cause jarring layout shifts if the button lacks structural boundaries.
**Action:** Always add `aria-live="polite"` to buttons that swap text for transient feedback, and apply a minimum width (e.g., `min-w-[90px]`) to ensure the layout remains stable regardless of the text length.
