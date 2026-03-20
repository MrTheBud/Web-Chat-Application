import asyncio
import ssl
import sqlite3
import hashlib
import websockets
import os
import time
from datetime import datetime

HOST = "0.0.0.0" # Change to server's IP address or use "localhost" for local testing
PORT = 9999 # Must match the port used in client.py

cert = "cert.pem" # Make sure to generate cert.pem and key.pem using openssl for secure communication.
key = "key.pem"

max_clients = 10
login_attempts = 5

clients = set()
clients_lock = asyncio.Lock()

#===============
active_users = {} # websocket -> username mapping for tracking who's who
#===============

SESSION_ID = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # Unique session ID for this server run, used in logs
CURRENT_LOG_FILE = f"logs/session_{SESSION_ID}.txt" # Log file for this session

#=====================+
def setup_server_folders():
    # Ensure logs directory exists for storing chat logs
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create a new log file for this session with a header
    with open(CURRENT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Chat Session Started: {SESSION_ID}\n")

async def write_to_log(username , message):
    # Append messages to the current session log file with timestamps
    timestamp = datetime.now().strftime("%H:%M:%S") # Log only the time for easier reading
    with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f: # Open in append mode to add messages to the log
        f.write(f"[{timestamp}] {username}: {message}\n")
#=====================+

#=============================
async def broadcast_user_list(): # Dynamic user selection. Sends current name to everyone
    async with clients_lock:
        # Get all the user names that are authenticated and connected
        names = [name for name in active_users.values()]
        user_list_payload = "USERLIST:" + ",".join(names)

        # Broadcast the user list to all clients
        for ws in clients:
            try:
                await ws.send(user_list_payload)
            except:
                pass
#===============================

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

#Stronger Password Requirements
def password_needs(pw: str):
    if len(pw) < 15 :
        return False, "Password Must be at least 15 Characters"

    has_upper = any(c.isupper() for c in pw)
    has_lower = any(c.islower() for c in pw)
    has_num = any(c.isdigit() for c in pw)
    has_special = any(not c.isalnum() for c in pw)

    if not has_upper:
        return False, "Password must include atleast 1 uppercase letter"
    if not has_lower:
        return False, "Password must include atleast 1 lowercase letter"
    if not has_num:
        return False, "Password must include atleast 1 number"
    if not has_special:
        return False, "Password must include atleast 1 special character"

    return True,""

async def broadcast(message: str, sender=None):
    async with clients_lock:
        dead = []
        for ws in clients:
            if sender is not None and ws is sender:
                continue
            try:
                await ws.send(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            clients.discard(ws)

async def recv_line(ws) -> str:
    try:
        msg = await ws.recv()
        if msg is None:
            return ""
        return str(msg).strip()
    except:
        return ""

#Creates Db for User/Pass passwords are hashed in DB
def initialize_db():
    if os.path.exists("secchat.db"):
        return

    conn = sqlite3.connect("secchat.db")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

async def handle_connection(ws):
    failed_attempts = 0
    username = None

    try:
        while True:
            await ws.send("Mode? (L=login, R=register): ")
            mode = (await recv_line(ws)).upper()

            if mode not in ("L", "R"):
                await ws.send("That's NOT L or R.")
                continue

            await ws.send("Username: ")
            username = await recv_line(ws)

            await ws.send("Password: ")
            password = await recv_line(ws)
            pw_hash = hash_pw(password)

            conn = sqlite3.connect("secchat.db")
            cur = conn.cursor()
            
            #Register
            if mode == "R":
                ok_pass, reason = password_needs(password)
                if not ok_pass:
                    await ws.send(f"Registration Failed: {reason}")
                    conn.close()
                    continue

                cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
                if cur.fetchone():
                    await ws.send("Register Failed: username already exists.")
                    conn.close()
                    continue

                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, pw_hash))
                conn.commit()
                conn.close()

                await ws.send("Register Successful!")
                continue

            #Login
            cur.execute("SELECT 1 FROM users WHERE username = ? AND password = ?", (username, pw_hash))
            ok = cur.fetchone() is not None
            conn.close()

            if not ok:
                failed_attempts += 1
                await ws.send(f"Login Failed. Try Again!")

                if failed_attempts >= login_attempts:
                    await ws.send("Too many failed attempts.")
                    await ws.close(code=4001)
                    return

                continue

            # Login Successful
            await ws.send("Login Successful!")
            failed_attempts = 0
            break

        # Check max clients and add to lists ONLY ONCE after successful login
        async with clients_lock:
            if len(clients) >= max_clients:
                await ws.send("Server full")
                await ws.close(code=1001)
                return
            clients.add(ws)
            active_users[ws] = username 

        await broadcast_user_list() 
        await broadcast(f"[{username} joined]", sender=ws)

        # chat loop
        while True:
            msg = await recv_line(ws)
            if not msg:
                break
#=================================================================
            # Filtering out raw data from the text logs, want log files sent, not actual file data.
            if msg.startswith("FILE:"):
                await write_to_log(username, f"[Sent a file]") # Log file sends with the filename   
            else: 
                await write_to_log(username, msg) # Log all messages to a file for later review
#==================================================================
            if msg.startswith("/msg "):
                parts = msg.split(" ", 2)
                if len(parts) >= 3:
                    target_user = parts[1]
                    private_content = parts[2]

                    # Find target websocket
                    found = False
                    for client_ws, name in active_users.items():
                        if name == target_user:
                            await client_ws.send(f"[PM from {username}] {private_content}")
                            await ws.send(f"[PM to {target_user}] {private_content}")
                            found = True
                            break
                    if not found:
                        await ws.send(f"User {target_user} not found.")
                continue

            await broadcast(f"{username}: {msg}")

    except Exception:
        pass
    finally:
        async with clients_lock:
            clients.discard(ws)
            if ws in active_users:
                del active_users[ws]
        if username:
            await broadcast_user_list() # update user list for everyone when someone leaves
            await broadcast(f"[{username} left]", sender=ws)

async def main():
    initialize_db()
    setup_server_folders()

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(cert, key)

    print(f"Listening on wss://{HOST}:{PORT}")
    async with websockets.serve(handle_connection, HOST, PORT, ssl=ssl_ctx):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())