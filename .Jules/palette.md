## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## $(date +%Y-%m-%d) - Adding console.status Spinners for Python CLI Compute Tasks
**Learning:** For terminal applications built with rich, fast local compute tasks (e.g. numerical grid-search taking ~20ms) can still benefit from `console.status` wrappers. While seemingly instantaneous locally, managing user expectations for any calculation prevents the UI from feeling frozen, especially if it scales poorly with inputs. The status spinner offers immediate feedback that computation is happening.
**Action:** Always look for and wrap core processing functions (like optimization or data building) with a loading indicator in CLI tools, even if they run quickly.
