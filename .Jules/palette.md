## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2026-04-30 - Added Loader for CLI Computation
**Learning:** Just like network requests, heavy mathematical computations (e.g. loan optimizations and sweet-spot analysis) can pause the terminal application and make it seem frozen. Wrapping these operations in a `rich.console.status` provides immediate feedback to users that calculations are running.
**Action:** Use visual indicators for non-instantaneous compute tasks even if they are CPU-bound and complete within a second or two, as it manages expectations and provides visual reassurance.
