## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-04-25 - Add loading spinners for intensive CLI calculations
**Learning:** For interactive CLI tools, computationally intensive but non-blocking tasks like grid-search optimizations and sweet-spot analysis (which may not be strictly asynchronous but take noticeable milliseconds) can feel unresponsive to the user. Adding simple micro-interactions like a loading spinner significantly improves perceived responsiveness and reduces perceived latency.
**Action:** Always wrap calculation-heavy or blocking synchronous functions in `rich.console.status` (or equivalent loaders) to indicate progress to the user, not just network IO like `fetch_rate`.
