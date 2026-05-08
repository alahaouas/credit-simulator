## 2024-05-18 - Visual Indicators for Fast CLI Tasks
**Learning:** Even when CLI computations (like optimizing or sweet-spot analysis) are fast (e.g. taking less than a second), users perceive the slight pause as the application hanging. Wrapping these steps in a visual status indicator immediately calms this perception.
**Action:** Always wrap non-instantaneous compute tasks in a visual indicator like `rich.console.status` to manage user expectations and prevent the application from feeling frozen.
