This file provides guidance for AGENT AI when working with code in this repository.

## Project Overview
This a project to build an app that enables user to convert markdown format text to PDF.
- This app has simple system that requires users minimum workaround
- Conversion result is easy to look with sophisticated design like Growi.

## Technology Stack

- **Frontend**: React
- **Backend**: FastAPI with Python 3.12+
- **Package Management**: uv for Python, pnpm for Node.js, mise for the entire project across the multiple languages
- **Database**: SQLite (operated by SQLAlchemy)
- **Charts**: ApexCharts
- **Languages**: TypeScript (frontend), Python (backend)
- **Deployment**: Docker Compose
- **Reverse Proxy**: Nginx
- **Environment Variables Integration**: dotenv

### Another Requirements
- The UI needs to be like the screen image below
![alt text](scrshot.png)
- configuration parameter needs to be prepared for proxy server and no proxy settings for when required
- Test-Driven Development needs to be applied.

## Project Structure

## Key Components

## Development Commands

### Backend Setup (uv)

### Frontend Setup (Node.js/pnpm)

## API Endpoints

## Key Architecture Decisions

## Environment Variables

## Development Phases

1. **Phase 1 (MVP)**: Basic project setup, sample data, asset selection, price charts, time range selector
2. **Phase 2**: News integration, chart markers, news panel, responsive design
3. **Phase 3**: Additional asset categories, advanced filtering, export features

## Performance Considerations

- **Chart Rendering**: Limit data points displayed, use ApexCharts' built-in decimation
- **API Optimization**: Implement caching, pagination for news data
- **Database**: Primary key on (timestamp, ric) for price queries (PostgreSQL), Global Secondary Index on timestamp for news queries (DynamoDB)
- **Frontend**: Use Nuxt's built-in performance optimizations, lazy load components

## DynamoDB Table Structure

## Testing Strategy

- **Backend**: Pytest for API endpoints, SQLAlchemy model tests (price data), DynamoDB integration tests (news data)
- **Frontend**: Vitest for component testing, E2E tests for critical user flows
- **Integration**: Test API-frontend integration, database migrations
- **DynamoDB Testing**: Run uv run python test_dynamodb.py in backend directory

## Python Execution

When using Claude Code to execute Python scripts, attach to the Docker container and use uv run:

# Attach to the backend container
docker compose exec backend bash

# Execute Python scripts with uv
uv run script_name.py

# Examples:
uv run test_dynamodb.py
uv run init_db.py
uv run pytest tests/

This ensures the Python environment has access to all dependencies and the correct database connections configured in the Docker environment.
