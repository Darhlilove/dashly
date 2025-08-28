# Product Overview

**dashly** - Dashboard Auto-Designer (Hackathon MVP)

## Core Value Proposition

Users type plain-English questions (e.g., "monthly revenue by region last 12 months") and the app automatically builds interactive dashboards with charts and tables by translating natural language to SQL and executing against datasets.

## Key Features

- Natural language to SQL translation using LLM
- CSV upload and ingestion into DuckDB
- Automatic chart generation (line, bar, pie) based on result shape
- SQL preview and validation (read-only SELECTs only)
- Dashboard configuration persistence as JSON
- Sub-3-minute demo capability

## Target Demo Flow

End-to-end demonstration must complete in under 90 seconds, showcasing the full pipeline from natural language query to rendered dashboard.

## Architecture Approach

- Backend: DuckDB for data storage, LLM integration for NL→SQL translation
- Frontend: Interactive UI with query input and chart rendering
- Data validation: Strict read-only SQL enforcement (no DDL/DML)
