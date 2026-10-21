# Headcount and WIP indicator redesign

The layout uses compact icons with hover-only explanatory text:

- **WIP:** amber package badge with the current quantity. The large dotted WIP halos and speech-bubble pointers are removed.
- **Coverage:** a small coverage ring with a check, shortfall mark, or neutral mark. Hover for assigned/required FTE, staffing gaps and assigned names. These remain staffing-plan values, not a claim of instantaneous operator availability.
- **Operators:** person icons; nearby operators group into one marker with a count. When they are at a station with coverage enabled, their marker and coverage badge share one compact strip. Hover for identity and state details.
- Operator names, HC labels and FTE descriptions are not painted on the canvas. Quantities stay visible. Hover tooltips hide on exit, Escape, editing, scrolling or document changes; they never print.
- Badge placement reserves space around stations, names and equipment. Displaced badges use thin leader lines that start outside station-label bounds. Per-person travel lines are removed from the operator layer; the dedicated Spaghetti overlay remains available.
- Headcount Setup retains independent operator/coverage toggles. Existing scenario fields and staffing calculations are unchanged. Layout Print has an explicit operator-indicator layer and preserves the live visibility settings after previewing.

## Browser checks

The indicator suite checks grouped operators, exact staffing values, hidden labels and real hover events, spacing on a twelve-station layout, maximum display sizes, zoom, import, moving path markers, print pixels/layers, scenario round-trip and exact simulation-history agreement with the previous release.

Install `tests/requirements.txt` and run:

```sh
CHROMIUM_PATH=/usr/bin/chromium python tests/headcount_indicators.py
```

The suite serves the checked-out HTML on an ephemeral local port. It uses the original released Git commit as its numerical baseline and writes screenshots/results under the ignored `test-results/indicators/` directory. `SIMULATOR_HTML`, `BASELINE_HTML` and `INDICATOR_RESULTS` can override the input and output paths.

Desktop Chromium is the validated browser. Native OS dialogs and other browser engines are not covered by these tests.
