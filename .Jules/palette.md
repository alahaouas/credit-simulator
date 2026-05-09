## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-05-24 - Loading states for local computation
**Learning:** Even fast, local computational tasks (like loan optimization or sweet-spot analysis) can cause the CLI to feel frozen if not wrapped in a visual loading indicator. Users lack confidence when the UI hangs without feedback.
**Action:** Always wrap non-instantaneous compute tasks in `rich.console.status` to manage user expectations and ensure the application feels responsive.
