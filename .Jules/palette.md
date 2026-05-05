## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-05-19 - Added Spinner for Fast Compute Tasks
**Learning:** In interactive CLI applications, even relatively fast compute tasks (like complex mathematical optimizations or grid searches taking <1s) can make the application feel temporarily unresponsive or "frozen", especially during repeated interactive updates. Wrapping these operations in a visual indicator like `rich.console.status` significantly improves perceived performance and manages user expectations by confirming that the application is actively processing the request.
**Action:** Always wrap non-instantaneous compute tasks (even those that feel "fast enough" to developers) in a loading state to ensure the interface feels responsive and alive, especially in a tight interactive loop.
