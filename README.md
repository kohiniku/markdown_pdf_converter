# Markdown to PDF Converter

A modern web application that converts Markdown text to PDF documents with a clean, professional design. Built with React frontend and FastAPI backend.

## Features

- **Markdown to PDF Conversion**: Convert any Markdown content to a professionally formatted PDF
- **File Upload**: Drag & drop or browse to upload `.md` files
- **Custom Styling**: Add custom CSS to personalize your PDF output
- **Dark Theme**: Modern dark UI design following the specified design tokens
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Preview**: See conversion tips and help in the interface

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for Python
- **Python 3.12+**: Latest Python features and performance
- **WeasyPrint**: HTML/CSS to PDF conversion engine
- **SQLAlchemy**: SQL toolkit and ORM
- **SQLite**: Lightweight database for conversion history
- **uv**: Fast Python package installer and resolver

### Frontend
- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Beautiful, customizable icons
- **PNPM**: Fast, disk space efficient package manager

### Infrastructure
- **Docker Compose**: Container orchestration
- **Nginx**: Reverse proxy and load balancer
- **Environment Variables**: Configuration management

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.12+ (for local development)

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd markdown-pdf-converter
```

2. ルート `.env` にポートを定義（初期値はありません）:
```bash
cp .env.example .env
# 必須（例）:
# BACKEND_INTERNAL_PORT=8000
# BACKEND_HOST_PORT=8000
# FRONTEND_INTERNAL_PORT=3000
# FRONTEND_HOST_PORT=3000
# NGINX_HTTP_PORT=80
# NGINX_HTTPS_PORT=443
# NGINX_INTERNAL_HTTP_PORT=80
```

3. Start all services:
```bash
docker-compose up --build
```

4. Access the application (ports are defined in your `.env`)

### Local Development

#### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install uv (if not already installed):
```bash
pip install uv
```

3. Install dependencies:
```bash
uv pip install -e .
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

#### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install pnpm (if not already installed):
```bash
npm install -g pnpm
```

3. Install dependencies:
```bash
pnpm install
```

4. Start the development server:
```bash
pnpm start
```

## API Endpoints

### POST /convert
Convert Markdown content to PDF.

**Request Body (Form Data):**
- `markdown_content`: The Markdown text to convert
- `filename` (optional): Custom filename for the PDF
- `css_styles` (optional): Custom CSS for styling

**Response:**
```json
{
  "success": true,
  "message": "PDF generated successfully",
  "file_id": "unique-id",
  "filename": "document.pdf",
  "download_url": "/download/unique-id_document.pdf"
}
```

### POST /upload-convert
Upload a Markdown file and convert it to PDF.

**Request Body (Multipart):**
- `file`: Markdown file (.md)
- `css_styles` (optional): Custom CSS for styling

### GET /download/{filename}
Download a generated PDF file.

### GET /health
Health check endpoint.

## Testing

### Backend Tests
```bash
cd backend
uv run pytest
```

### Frontend Tests
```bash
cd frontend
pnpm test
```

### Run All Tests
```bash
# Backend
docker-compose exec backend uv run pytest

# Frontend
docker-compose exec frontend pnpm test
```

## Project Structure

```
markdown-pdf-converter/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # Main FastAPI application
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # Database setup
│   │   └── models.py          # SQLAlchemy models
│   ├── tests/                 # Backend tests
│   ├── Dockerfile
│   ├── pyproject.toml         # Python dependencies
│   └── .env.example           # Environment variables template
├── frontend/                  # React frontend
│   ├── public/
│   ├── src/
│   │   ├── App.tsx            # Main React component
│   │   ├── App.css            # Component styles
│   │   ├── index.tsx          # React entry point
│   │   ├── index.css          # Global styles
│   │   └── App.test.tsx       # Component tests
│   ├── Dockerfile
│   ├── package.json           # Node.js dependencies
│   ├── tailwind.config.js     # Tailwind configuration
│   └── tsconfig.json          # TypeScript configuration
├── nginx/
│   └── nginx.conf.template    # Nginx configuration (env-templated)
├── docker-compose.yml         # Container orchestration
├── .gitignore
├── AGENTS.md                  # Development guidelines
├── DESIGN.md                  # Design specifications
└── README.md                  # This file
```

## Environment Variables

### Centralized Ports (project root `.env`)
全てのポートは `.env` で必須指定（初期値なし）。

```env
# Backend (FastAPI/Uvicorn)
# BACKEND_INTERNAL_PORT=
# BACKEND_HOST_PORT=

# Frontend (React dev server)
# FRONTEND_INTERNAL_PORT=
# FRONTEND_HOST_PORT=

# Nginx (host-published ports)
# NGINX_HTTP_PORT=
# NGINX_HTTPS_PORT=

# Nginx (inside container)
# NGINX_INTERNAL_HTTP_PORT=
```

Compose は `PORT=$BACKEND_INTERNAL_PORT` と `PORT=$FRONTEND_INTERNAL_PORT` を各コンテナに渡します。未設定の場合は起動時にエラーとなります。

### Backend app settings
Backend 設定は環境変数から読み込みます（ポートは `.env` 必須）。Docker なしで単体起動する場合のみ `backend/.env` を使ってください。

```env
DATABASE_URL=sqlite:///./app.db
DEBUG=true
HOST=0.0.0.0
# CORS_ORIGINS は backend/.env で設定（例: ["http://localhost:3000"]）
UPLOAD_DIR=uploads
OUTPUT_DIR=output
MAX_FILE_SIZE=10485760
PDF_ENGINE=weasyprint
PDF_TIMEOUT=30
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Design System

The application follows a dark theme design system with:

- **Colors**: Dark background (#0B1020), surface (#11162A), primary blue (#4F8DF7)
- **Typography**: Inter font family, 14px base size
- **Spacing**: 4px scale (4, 8, 12, 16, 24, 32, 48)
- **Border Radius**: 14px default
- **Components**: Cards, buttons, inputs with consistent styling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

1. **WeasyPrint installation fails**: Ensure system dependencies are installed
2. **Port conflicts**: Change ports in the root `.env` (see Centralized Ports)
3. **Permission issues**: Ensure Docker has proper permissions
4. **File upload fails**: Check MAX_FILE_SIZE setting

### Docker Issues

```bash
# Rebuild containers
docker-compose down
docker-compose up --build

# View logs
docker-compose logs backend
docker-compose logs frontend

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Development Mode

For development with hot reload:
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend  
cd frontend && pnpm start
```
