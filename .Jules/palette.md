## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-05-19 - Wrapping compute tasks in visual indicators
**Learning:** Even though internal tasks like solving simulations can be fast, they can sometimes cause momentary application hangs. For interactive terminal applications using `rich`, it's a good practice to wrap even small and fast operations with `console.status` to ensure continuous UI updates and give the users immediate visual reassurance that the process is ongoing.
**Action:** Always wrap optimization or computation-heavy tasks with a visual feedback indicator, such as `console.status`, to enhance UX and keep applications from feeling unresponsive.
