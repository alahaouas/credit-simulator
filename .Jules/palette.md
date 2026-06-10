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
