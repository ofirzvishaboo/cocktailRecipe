# 🍹 Cocktail Recipe Manager

A full-stack web application for cocktail recipes, ingredients, and cost management. Built with a FastAPI (Python) backend and a React (Vite) frontend, containerized with Docker.

## ✨ Features

- **Cocktail Management**: Create, read, update, and delete cocktail recipes
- **Ingredient Management**: Manage ingredients used in cocktails
- **Recipe Composition**: Associate ingredients with cocktails and specify quantities (ml)
- **Bottle-based Costing**: Define purchasable bottle SKUs per ingredient (brand + size + price) and compute recipe costs
- **Cocktail Scaler + Costs**: Scale recipes to a target volume and see a per-ingredient + total cost breakdown
- **Modern UI**: Clean, responsive interface with tabbed navigation
- **RESTful API**: Well-structured API with automatic documentation
- **Database**: PostgreSQL database with proper relationships

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** (Async) - SQL toolkit and ORM
- **PostgreSQL** - Relational database
- **Uvicorn** - ASGI server
- **Python 3.12+** - Programming language
- **uv** - Fast Python package manager

### Frontend
- **React 19** - UI library
- **Vite** - Build tool and dev server
- **Axios** - HTTP client
- **ESLint** - Code linting

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## 📋 Prerequisites

- Docker and Docker Compose installed
- (Optional) Node.js 18+ and Python 3.12+ for local development

## 🚀 Quick Start

### Local development (Docker Compose)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cocktailRecipe
   ```

2. **Start all services**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

   This will start:
   - PostgreSQL database on port `5432`
   - FastAPI backend on port `8000`
   - React frontend on port `5173`

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **Stop all services**
   ```bash
   docker compose -f docker-compose.dev.yml down
   ```

   To also remove volumes (database data):
   ```bash
   docker compose -f docker-compose.dev.yml down -v
   ```

## 🌍 Production deployment (Ubuntu + Docker + HTTPS)

### 1) DNS + firewall
- Point your domain `A` record to the server public IP (and optionally `www`).
- Open ports **80** and **443** on the server firewall/security group.

### 2) Configure environment
Copy `env.example` to `.env` on the server and set real values:
- `DOMAIN` (your domain)
- `POSTGRES_PASSWORD` (strong)
- `SECRET` (strong random string)
- `CORS_ORIGINS` (e.g. `https://your-domain.com`)

### 3) Run on the server
```bash
docker compose up -d --build
```

### 4) Verify
- Frontend: `https://your-domain.com`
- API docs: `https://your-domain.com/api/docs`

Notes:
- Production compose does **not** publish Postgres/pgAdmin/API ports directly to the internet (only 80/443 via Caddy).
- The frontend is built and served as static files (no Vite dev server).

## 🏗️ Project Structure

```
cocktailRecipe/
├── backend/                 # FastAPI backend
│   ├── core/               # Core configuration
│   │   └── config.py      # Settings and environment variables
│   ├── db/                 # Database models and setup
│   │   ├── database.py    # Database connection and session
│   │   ├── cocktail_recipe.py
│   │   ├── ingredient.py
│   │   ├── ingredient_brand.py
│   │   └── cocktail_ingredient.py
│   ├── routers/            # API route handlers
│   │   ├── cocktails.py
│   │   ├── ingredients.py
│   │   └── cocktail_ingredient.py
│   ├── schemas/            # Pydantic schemas
│   │   ├── cocktails.py
│   │   ├── ingredient.py
│   │   └── cocktail_ingredient.py
│   ├── main.py            # FastAPI application entry point
│   ├── Dockerfile         # Backend container definition
│   └── pyproject.toml     # Python dependencies
│
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Route pages (Cocktails, Ingredients, Scaler, etc.)
│   │   ├── api.js         # API client configuration (LAN-friendly baseURL)
│   │   ├── App.jsx       # Main application component
│   │   └── main.jsx      # Application entry point
│   ├── Dockerfile        # Frontend container definition
│   └── package.json      # Node.js dependencies
│
└── docker-compose.yml    # Docker Compose configuration
```

## 🔧 Development

### Backend Development

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   Create a `.env` file in the `backend` directory:
   ```env
   DATABASE_USER=user
   DATABASE_PASSWORD=password
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=cocktaildb
   ```

4. **Run the development server**
   ```bash
   uv run uvicorn main:app --reload
   ```

### Frontend Development

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up API URL (optional)**
   The frontend will auto-detect the backend host as `http://<current-hostname>:8000` for LAN access.
   If you want to override it, create a `.env` file:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

4. **Run the development server**
   ```bash
   npm run dev
   ```

## 📡 API Endpoints

### Cocktail Recipes
- `GET /cocktail-recipes/` - Get all cocktail recipes
- `GET /cocktail-recipes/{cocktail_id}` - Get a specific cocktail recipe
- `POST /cocktail-recipes/` - Create a new cocktail recipe
- `PUT /cocktail-recipes/{cocktail_id}` - Update a cocktail recipe
- `DELETE /cocktail-recipes/{cocktail_id}` - Delete a cocktail recipe
- `GET /cocktail-recipes/{cocktail_id}/cost` - Compute per-ingredient + total cost (based on selected bottle brands)

### Ingredients
- `GET /ingredients/` - Get all ingredients
- `GET /ingredients/{ingredient_id}` - Get a specific ingredient
- `POST /ingredients/` - Create a new ingredient
- `PUT /ingredients/{ingredient_id}` - Update an ingredient
- `DELETE /ingredients/{ingredient_id}` - Delete an ingredient
- `GET /ingredients/{ingredient_id}/brands` - List bottle SKUs for an ingredient
- `POST /ingredients/{ingredient_id}/brands` - Create bottle SKU for an ingredient
- `PUT /ingredients/brands/{brand_id}` - Update bottle SKU (superuser)
- `DELETE /ingredients/brands/{brand_id}` - Delete bottle SKU (superuser)

### Cocktail Ingredients
- `GET /cocktail-ingredients/` - Get all cocktail-ingredient associations
- Additional endpoints for managing relationships

For detailed API documentation, visit http://localhost:8000/docs when the backend is running.

## 🗄️ Database Schema

The application uses these main tables:

- **cocktail_recipes**: Stores cocktail recipe information
- **ingredients**: Stores ingredient information
- **cocktail_ingredients**: Junction table linking cocktails to ingredients with quantities (ml)
- **ingredient_brands**: Bottle SKUs per ingredient (brand name + bottle size ml + bottle price)

## 🔐 Environment Variables

### Backend
- `DATABASE_USER` - PostgreSQL username (default: `user`)
- `DATABASE_PASSWORD` - PostgreSQL password (default: `password`)
- `DATABASE_HOST` - Database host (default: `localhost`)
- `DATABASE_PORT` - Database port (default: `5432`)
- `DATABASE_NAME` - Database name (default: `cocktaildb`)
- `DATABASE_ECHO` - Enable SQL query logging (default: `False`)

### Frontend
- `VITE_API_URL` - Backend API URL (optional). If not set (or set to localhost), the frontend defaults to `http://<current-hostname>:8000` for LAN access.

## 🐳 Docker Services

The `docker-compose.yml` defines three services:

1. **postgres**: PostgreSQL 16 database
2. **api**: FastAPI backend with hot-reload
3. **frontend**: React frontend with Vite dev server

All services are configured with volume mounts for development, allowing code changes to be reflected immediately.

## 📝 Scripts

### Frontend
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🐛 Troubleshooting

### Database connection issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check database logs: `docker-compose logs postgres`

### Port conflicts
- If ports 5432, 8000, or 5173 are in use, modify them in `docker-compose.yml`

### Frontend can't connect to backend
- If accessing from another device (LAN), do NOT use `localhost` for `VITE_API_URL` in the browser.
  The app defaults to `http://<current-hostname>:8000` to work on LAN.
- Check that the backend service is running: `docker-compose logs api`

### Volume mounting issues
- Ensure file permissions are correct
- On Windows, verify Docker Desktop file sharing settings

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vite.dev/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

Made with ❤️ for cocktail enthusiasts

