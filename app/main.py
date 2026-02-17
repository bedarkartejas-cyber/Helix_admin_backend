from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Internal modular imports
from app.core.config import settings
# ADDED: dashboard import here
from app.api import auth, users, products, branches, dashboard

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Store Management System API",
    description="A modular, production-grade backend for multi-branch store management.",
    version="2.1.0",
    docs_url="/docs",      # Swagger UI path
    redoc_url="/redoc"     # ReDoc path
)

# ============ MIDDLEWARE CONFIGURATION ============

# CORS Middleware: Configured to allow any frontend origin as requested
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Set to ["*"] in config.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Production Middleware to track API latency."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ============ ROUTER REGISTRATION ============

# Authentication Module (Login, Signup, OTP, Password Reset)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# User Module (Profile Updates, Admin User Management)
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

# Product Module (Inventory Management)
app.include_router(products.router, prefix="/api/v1/products", tags=["Inventory"])

# Branch Module (Store Settings & Staff Lists)
app.include_router(branches.router, prefix="/api/v1/branch", tags=["Store Management"])

# NEW: Dashboard Module (Statistics & Summary)
# This handles the /api/v1/dashboard/summary endpoint
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

# ============ GLOBAL ERROR HANDLING ============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensures that unhandled errors return a clean JSON response instead of a crash."""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# ============ HEALTH & STATUS ============

@app.get("/health", tags=["System"])
async def health_check():
    """System health check for monitoring tools (like AWS/DigitalOcean)."""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "environment": "production" if not settings.CORS_ORIGINS == ["*"] else "development-standard"
    }

@app.get("/", tags=["System"])
async def root():
    """Root endpoint providing basic API information."""
    return {
        "message": "Store Management API is online",
        "documentation": "/docs",
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    # In production, use workers > 1 for better performance
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)