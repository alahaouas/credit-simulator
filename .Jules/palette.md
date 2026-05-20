## 2024-05-19 - Added Spinner for Network Fetch
**Learning:** For terminal applications using `rich`, network requests (like fetching APIs) can cause the UI to hang. Replacing a static `console.print` with `console.status` provides immediate UX improvement with minimal code changes.
**Action:** Always look for long-running synchronous calls (like API or DB requests) and wrap them in a spinner or progress bar to reassure the user that the system hasn't frozen.

## 2024-04-25 - Add loading spinners for intensive CLI calculations
**Learning:** For interactive CLI tools, computationally intensive tasks like grid-search optimizations and sweet-spot analysis can feel unresponsive to the user. Adding simple micro-interactions like a loading spinner significantly improves perceived responsiveness.
**Action:** Always wrap calculation-heavy or blocking synchronous functions in `rich.console.status` to indicate progress, not just network IO. Keep error-handling try/except outside the `with console.status()` block so error panels render correctly.

## 2024-05-15 - [Manage expectations for instantaneous tasks]
**Learning:** When making UX improvements to the CLI, wrapping non-instantaneous compute tasks (even fast ones taking under a second) in a visual indicator like `rich.console.status` manages user expectations and prevents the application from feeling frozen. Hardcoded UI strings must be avoided to ensure proper localization.
**Action:** Added `status.resolving` and `status.generating_schedule` localized strings to wrap the `resolve` and `build_amortization_schedule` methods.

## 2024-05-19 - Group sequential CLI spinners to prevent UI stutter
**Learning:** Sequential calls to `with console.status("...")` cause the spinner to disappear and reappear between tasks, resulting in UI stutter when tasks are fast but not instantaneous.
**Action:** When executing a contiguous chain of synchronous tasks, group them inside a single `with console.status(...) as status:` block and use `status.update("...")` to change the message seamlessly without visual interruptions. Keep error handling robust by using state variables (like `params = None` before the block) to identify which step failed if they raise the same exception type.

## 2024-05-20 - Add confirmation dialogs and helpful empty states
**Learning:** For destructive CLI commands like `rates clear`, a simple confirmation dialog prevents accidental data loss and improves user confidence. Also, empty states (e.g., in `rates list`) should not be dead ends—they should provide users with a clear call-to-action on what command to run next.
**Action:** When creating CLI tools that alter state, add `--yes` flags and `click.confirm()` prompts for destructive actions. Ensure all "empty" states provide actionable guidance.

## 2024-05-20 - Replace text loading states with visual spinners
**Learning:** Using simple text like `...` or `Submitting` for async web operations looks unpolished and can cause slight layout shifts depending on font rendering. An animated SVG spinner provides standard, recognizable feedback that an operation is taking place, making the UI feel smoother and more responsive.
**Action:** When working on async web forms, always use standard visual progress indicators (like an SVG spinner) instead of text fallbacks, and ensure the button layout (e.g. `flex justify-center min-h-`) prevents layout shift when swapping text for the spinner.
