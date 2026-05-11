## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-04-25 - Add loading spinners for intensive CLI calculations
**Learning:** For interactive CLI tools, computationally intensive tasks like grid-search optimizations and sweet-spot analysis can feel unresponsive to the user. Adding simple micro-interactions like a loading spinner significantly improves perceived responsiveness.
**Action:** Always wrap calculation-heavy or blocking synchronous functions in `rich.console.status` to indicate progress, not just network IO. Keep error-handling try/except outside the `with console.status()` block so error panels render correctly.

## 2024-05-15 - [Manage expectations for instantaneous tasks]
**Learning:** When making UX improvements to the CLI, wrapping non-instantaneous compute tasks (even fast ones taking under a second) in a visual indicator like `rich.console.status` manages user expectations and prevents the application from feeling frozen. Hardcoded UI strings must be avoided to ensure proper localization.
**Action:** Added `status.resolving` and `status.generating_schedule` localized strings to wrap the `resolve` and `build_amortization_schedule` methods.
