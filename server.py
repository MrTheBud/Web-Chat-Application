#Made By: Kevin Perez, Alex Islas, Dino Rozac
import asyncio
import ssl
import sqlite3
import hashlib
import websockets
import os

HOST = "0.0.0.0"
PORT = 9999

cert = "cert.pem"
key = "key.pem"

max_clients = 2
login_attempts = 3

clients = set()
clients_lock = asyncio.Lock()


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
    msg = await ws.recv()
    if msg is None:
        return ""
    return str(msg).strip()

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
                    await ws.close(code=4001, reason="Too many failed attempts")
                    return

                continue

            await ws.send("Login Successful!")
            failed_attempts = 0
            break


        # max clients check
        async with clients_lock:
            if len(clients) >= max_clients:
                await ws.send("Server full")
                await ws.close(code=1001, reason="Server full")
                return
            clients.add(ws)

        await broadcast(f"[{username} joined]", sender=ws)

        # chat loop
        while True:
            msg = await recv_line(ws)
            if not msg:
                break
            await broadcast(f"{username}: {msg}")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        try:
            await ws.send(f"Error")
        except Exception:
            pass
    finally:
        async with clients_lock:
            clients.discard(ws)
        if username:
            await broadcast(f"[{username} left]", sender=ws)


async def main():
    initialize_db()

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(cert, key)

    print(f"Listening on wss://{HOST}:{PORT}")
    async with websockets.serve(handle_connection, HOST, PORT, ssl=ssl_ctx):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
