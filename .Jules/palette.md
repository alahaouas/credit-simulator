## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2026-05-10 - Added Loading Spinners for CPU-Bound Compute Tasks
**Learning:** UX issues in terminal apps aren't just limited to network fetching; local CPU-bound computations (like large optimization calculations or sweet-spot analysis) can also create noticeable pauses that make the app feel unresponsive. Users benefit from immediate visual feedback via `rich.console.status` for these tasks as well.
**Action:** Extend the use of `rich.console.status` to local data crunching operations when there is any chance of a perceptible delay.
