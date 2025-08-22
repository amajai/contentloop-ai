#!/usr/bin/env python3
"""
Start script for the ContentLoop AI
"""
import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Starting ContentLoop AI...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("🔄 Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )