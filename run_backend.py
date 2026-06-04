#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Backend Launcher
Properly starts the FastAPI backend with all integrations.
"""

import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Ensure we're in the project root
    os.chdir(Path(__file__).parent)
    
    # Start uvicorn with the FastAPI app
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
