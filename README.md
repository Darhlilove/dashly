# Dashly - Dashboard Auto-Designer

A hackathon MVP that converts natural language queries into interactive dashboards with automatic chart generation.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Git

### Setup & Run

1. **Clone and setup the project:**

```bash
git clone <repository-url>
cd dashly
```

2. **Backend setup:**

```bash
cd backend
pip install -r requirements.txt
python data/generate_demo_data.py  # Generate demo database
cd ..
```

3. **Frontend setup:**

```bash
cd frontend
npm install
cd ..
```

4. **Start both services:**

```bash
# Terminal 1 - Backend
cd backend && python -m uvicorn src.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```

5. **Access the application:**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🏗️ Project Structure

```
dashly/
├── frontend/          # React + TypeScript + Tailwind UI
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/           # FastAPI + DuckDB + LLM integration
│   ├── src/
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── data/              # Demo CSV files and DuckDB database
│   ├── generate_demo_data.py
│   ├── sales_data.csv
│   └── dashly.db
└── infra/             # GitHub Actions CI/CD
    └── .github/workflows/
```

## 🎯 Demo Flow (90 seconds)

1. **Upload/Load Data** - Demo CSV files are pre-loaded
2. **Natural Language Query** - "monthly revenue by region last 12 months"
3. **SQL Generation** - LLM converts to SQL query
4. **Data Execution** - Query runs against DuckDB
5. **Chart Generation** - Automatic chart type selection and rendering
6. **Dashboard Display** - Interactive charts with data tables

## 🛠️ Technology Stack

- **Frontend**: Vite + React + TypeScript + Tailwind CSS + Recharts
- **Backend**: FastAPI + Python + DuckDB + OpenAI API
- **Data**: CSV ingestion, DuckDB analytics database
- **Charts**: Automatic selection (line, bar, pie charts)
- **Deployment**: GitHub Actions CI/CD pipeline

## 📊 Features

- ✅ Natural language to SQL translation
- ✅ CSV upload and DuckDB ingestion
- ✅ Automatic chart type detection
- ✅ Interactive dashboard rendering
- ✅ SQL query preview and validation
- ✅ Dashboard configuration persistence
- ✅ Read-only SQL enforcement (security)

## 🔧 Development

### Backend Development

```bash
cd backend
pip install -e ".[dev]"  # Install with dev dependencies
pytest tests/            # Run tests
black src/               # Format code
```

### Frontend Development

```bash
cd frontend
npm run dev              # Development server
npm run build            # Production build
npm run lint             # Lint code
```

### Database Management

```bash
cd data
python generate_demo_data.py  # Regenerate demo data
```

## 🚀 Deployment

The project includes GitHub Actions workflows for:

- Automated testing (backend + frontend)
- Code quality checks
- Build verification
- Deployment pipeline (ready for cloud deployment)

## 📝 API Endpoints

- `GET /` - Health check
- `POST /api/query` - Process natural language query
- `GET /api/tables` - List available database tables
- `GET /docs` - Interactive API documentation

## 🎨 UI Components

- Query input with natural language processing
- SQL preview with syntax highlighting
- Dynamic chart rendering (Recharts)
- Responsive dashboard layout
- Loading states and error handling
