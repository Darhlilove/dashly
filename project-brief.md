PROJECT: Dashboard Auto-Designer (Hackathon MVP)

Elevator pitch:
Users type a plain-English question (e.g. "monthly revenue by region last 12 months") and the app builds an interactive dashboard (chart + table) automatically by translating the question into SQL, executing it against a local demo dataset, and rendering results as a chart. Must be demonstrable in <3 minutes.

MVP Acceptance Criteria:
- User can upload a CSV (or choose a bundled demo CSV).
- Backend ingests CSV into a DuckDB instance and exposes a schema endpoint.
- Frontend UI has a query box: user types a natural-language query and clicks "Generate".
- System translates NL→SQL using an LLM (schema-aware prompt) and returns SQL text.
- System validates SQL (only read-only SELECTs; no DDL/DML), executes on DuckDB, returns rows.
- Frontend renders an appropriate chart (line, bar, pie) based on result shape automatically.
- UI shows the generated SQL preview and allows a single click to "accept" before executing (or revert / edit).
- Save dashboard config as JSON and allow quick re-run.
- Demo path (scripted) runs end-to-end in under 90 seconds.

Non-MVP / Stretch:
- Connectors for BigQuery/Google Sheets
- Multi-chart dashboards, filters, time-picker
- Natural follow-ups (e.g., "now break that down by product")
