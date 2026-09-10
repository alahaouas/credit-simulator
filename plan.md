1. **Fix `focus-visible` classes on bordered links**: In `web/app/page.tsx`, remove the `dark:focus-visible:ring-gray-500` class from the "History" and "Sign In" bordered links (lines 44 and 51), and ensure they match the repo standard: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900`. Use `replace_with_git_merge_diff` for the edits.
2. **Verify Frontend**: Execute `cd web && pnpm run lint` to verify code quality, and `pnpm run test:e2e` to ensure the E2E tests still pass.
3. **Pre-commit**: Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
4. **Submit PR**: Call the submit tool to update the PR on the branch `palette-page-links-focus`.
