# Dev: Alex Islas

# A simple WebSocket server using the websockets library

import asyncio
import websockets
import json
import ssl
import hashlib
import time

class ChatServer:
    def __init__(self):
        self.clients = {}  # websocket: {username, last_heartbeat}
        self.users = {
            # In production, make sure to use proper password hashing (bcrypt, argon2)!!!
            "alice": hashlib.sha256("password123".encode()).hexdigest(),
            "bob": hashlib.sha256("securepwd".encode()).hexdigest(),
            "charlie": hashlib.sha256("mypassword".encode()).hexdigest()
        }

