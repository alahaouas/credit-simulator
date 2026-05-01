## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.
## 2026-05-01 - Adding Status Indicators to Fast Compute Tasks
**Learning:** Even though background computations (like loan optimization or sweet spot analysis) may seem almost instantaneous or run in less than a second, wrapping them in a status indicator (`rich.console.status`) significantly improves the perceived responsiveness of CLI applications. Users tend to notice when there isn't feedback during actions that computationally "feel" complex.
**Action:** When working on CLI workflows, proactively identify any synchronous blocking computations or API calls and wrap them with a visual spinner/status indicator, to prevent the UI from feeling stuck, even for small latency tasks.
