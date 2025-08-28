# Technology Stack

## Core Technologies

- **Database**: DuckDB (local, in-process analytics database)
- **LLM Integration**: For natural language to SQL translation
- **Data Format**: CSV ingestion and processing
- **Configuration**: JSON for dashboard persistence

## Architecture Components

- **Backend**: API server with DuckDB integration and LLM connectivity
- **Frontend**: Interactive web UI with chart rendering capabilities
- **Data Pipeline**: CSV → DuckDB → SQL execution → Chart rendering

## Chart Libraries

Support for automatic chart type selection:

- Line charts (time series data)
- Bar charts (categorical comparisons)
- Pie charts (proportional data)

## Security & Validation

- **SQL Validation**: Strict enforcement of read-only SELECT statements
- **Query Restrictions**: No DDL (Data Definition Language) or DML (Data Manipulation Language) operations
- **Schema Awareness**: LLM prompts must include database schema context

## Development Environment

- **IDE Configuration**: Kiro MCP integration enabled
- **Project Type**: Hackathon MVP (rapid prototyping focus)

## Performance Requirements

- Demo execution: Complete end-to-end flow in under 90 seconds
- Query response: Fast enough for interactive use during demonstrations
