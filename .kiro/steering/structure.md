# Project Structure

## Current Organization

This is an early-stage hackathon MVP project with minimal initial structure:

```
dashly/
├── .git/                 # Git version control
├── .kiro/               # Kiro AI assistant configuration
│   └── steering/        # AI guidance documents
├── .vscode/             # VSCode project settings
├── README.md            # Project documentation
└── project-brief.md     # Detailed project requirements
```

## Recommended Structure (To Be Implemented)

Based on the MVP requirements, the project should evolve into:

```
dashly/
├── backend/             # API server and data processing
│   ├── src/
│   │   ├── api/         # REST API endpoints
│   │   ├── db/          # DuckDB integration
│   │   ├── llm/         # LLM integration for NL→SQL
│   │   └── validation/  # SQL validation logic
│   └── data/            # Demo CSV files
├── frontend/            # Web UI application
│   ├── src/
│   │   ├── components/  # React/Vue components
│   │   ├── charts/      # Chart rendering logic
│   │   └── api/         # Frontend API client
│   └── public/          # Static assets
├── shared/              # Common types and utilities
└── docs/                # Additional documentation
```

## File Naming Conventions

- Use kebab-case for directories and files
- Component files should be PascalCase if using React/Vue
- Configuration files in JSON format for dashboard persistence
- Demo CSV files should have descriptive names (e.g., `sales-data-2023.csv`)

## Key Principles

- **Rapid Prototyping**: Prioritize working functionality over perfect architecture
- **Demo-Ready**: All code should support the 90-second demo requirement
- **Separation of Concerns**: Clear boundaries between data processing, API, and UI layers
