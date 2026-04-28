## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.
## 2024-05-24 - Loading Indicators for Fast Tasks
**Learning:** Wrapping non-instantaneous compute tasks (even those taking under a second) in a visual indicator like `rich.console.status` manages user expectations and prevents the application from feeling frozen.
**Action:** Always add loading spinners/status indicators for optimization or data processing steps in CLI tools.
