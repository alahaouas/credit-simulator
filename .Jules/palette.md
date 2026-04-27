## 2026-04-27 - [Add loading spinner for fast CLI computations]
**Learning:** Even when CLI computations (like grid-search optimizations) are relatively fast (under a second), lacking visual feedback during the pause can make the application feel unresponsive or frozen, leading to poor UX.
**Action:** Always wrap non-instantaneous compute tasks in a visual indicator (like `rich.console.status`) to manage user expectations and make the interface feel deliberately active rather than blocked.
