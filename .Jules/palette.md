## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-05-20 - Added Spinner for Computationally Heavy Tasks
**Learning:** For terminal applications using `rich`, non-instantaneous compute tasks (like running simulations and optimizations) can cause the UI to hang, making the application feel frozen. Replacing an empty wait time with a visual indicator like `console.status` provides immediate UX improvement by managing user expectations.
**Action:** Always wrap non-instantaneous compute tasks in a visual indicator like `rich.console.status` to reassure the user that the system hasn't frozen and is working.
