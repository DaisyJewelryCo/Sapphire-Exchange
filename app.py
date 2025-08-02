"""
Sapphire Exchange - Main Application Entry Point

This module launches the PyQt5-based desktop application for Sapphire Exchange.
"""
import sys
import asyncio
from PyQt5.QtWidgets import QApplication

from main_window import MainWindow

# Enable asyncio event loop for PyQt5
from qasync import QEventLoop, asyncSlot, asyncClose

import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from .models import User, Item, Auction
from .database import db
from .nano_utils import NanoWallet, verify_message

# Initialize FastAPI app
app = FastAPI(
    title="Sapphire Exchange",
    description="Decentralized Auction Platform using Nano and Arweave",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Models
class UserCreate(BaseModel):
    username: str
    public_key: str
    signature: str  # Signature of the username with the user's private key

class ItemCreate(BaseModel):
    name: str
    description: str
    starting_price: float = 0.0
    duration_hours: float = 24.0
    metadata: dict = {}

class BidRequest(BaseModel):
    amount: float
    bidder_public_key: str
    signature: str  # Signature of (auction_id:amount) with the bidder's private key

class AuthToken(BaseModel):
    token: str

# Utility functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get the current user from the token."""
    token = credentials.credentials
    # In a real app, verify the JWT token
    # For now, we'll just use the public key as the token
    user = await db.get_user(token)
    if not user:
        raise HTTPException(
    
    # Set up asyncio event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Run the application
    with loop:
        sys.exit(loop.run_forever())

                        # Mark auction as settled
                        auction.settled = True
                        auction.winner_public_key = auction.current_bidder
                        await db.store(auction)
                    
                    # If no bids, return the item to the seller
                    elif auction.current_bid is None:
                        auction.is_active = False
                        auction.settled = True
                        await db.store(auction)
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Error in settle_auctions: {e}")
            await asyncio.sleep(60)  # Wait before retrying

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup."""
    asyncio.create_task(settle_auctions())

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    # Create the Qt Application
    app = QApplication(sys.argv)
    
    # Set up asyncio event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Run the application
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()
