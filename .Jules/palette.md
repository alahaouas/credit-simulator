## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.
## 2024-05-03 - CLI Compute Visual Feedback
**Learning:** Non-instantaneous compute tasks in CLI applications can make the app feel frozen, leading to a poor user experience. Users need visual feedback to manage expectations.
**Action:** Always wrap compute-heavy operations (like optimization or data analysis) in a visual indicator such as 'rich.console.status' to provide immediate feedback.
