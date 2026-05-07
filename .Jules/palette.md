## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-05-19 - Added Spinner for Computation
**Learning:** Even computation that doesn't involve I/O like network requests can take noticeable time and feel like freezing. Using `rich.console.status` provides a simple way to indicate the application is computing rather than frozen.
**Action:** When implementing CLI commands that perform data analysis or optimizations, wrap non-instantaneous compute tasks in visual indicators like `rich.console.status` to manage user expectations.
