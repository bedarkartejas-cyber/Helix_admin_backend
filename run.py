import uvicorn
import logging
from app.core.config import settings

# Configure logging for the startup process
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server_startup")

def main():
    """
    Main entry point for the FastAPI application server.
    Configured for production-grade execution.
    """
    try:
        logger.info("🚀 Starting Store Management Production Server...")
        logger.info(f"🌐 Server will be available at: {settings.FRONTEND_URL}")
        
        # In a production environment, you would typically use:
        # workers: Number of CPU cores * 2 (e.g., workers=4)
        # reload: False (Setting it to True is for development only)
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",        # Listen on all available network interfaces
            port=8000,             # Standard API port
            reload=True,           # Enabled for your development phase; set False in production
            workers=1,             # Standard for development; increase for production
            log_level="info",
            proxy_headers=True,    # Required if running behind Nginx/load balancer
            forwarded_allow_ips="*" # Required if running behind Nginx/load balancer
        )
    except Exception as e:
        logger.error(f"❌ Failed to start the server: {str(e)}")

if __name__ == "__main__":
    main()