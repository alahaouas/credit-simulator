## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2026-05-04 - Adding Spinners for Fast Local Compute
**Learning:** In terminal applications, even fast local compute tasks (like simulation optimization which might take < 1s) can make the UI feel unresponsive. Wrapping these operations in visual indicators like `rich.console.status` significantly improves perceived performance and manages user expectations, preventing the application from feeling frozen.
**Action:** Always wrap non-instantaneous compute tasks in a visual loading indicator, not just network or disk I/O tasks.
