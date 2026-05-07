# Made By: Kevin Perez, Alex Islas, Dino Rozac

import asyncio
import bcrypt
import aiohttp
from aiohttp import web
import asyncpg
import os
import time
import json
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 9999))

MAX_MSG_PER_MINUTE = 30
LOGIN_ATTEMPT_LIMIT = 5
MAX_HISTORY = 100
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

#data stored
DATABASE_URL = os.environ.get("DATABASE_URL")
db_pool = None

async def db_query(sql, params=None):
    global db_pool
    async with db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *(params or[]))
            return [dict(row) for row in rows]

async def db_execute(sql, params=None):
    global db_pool
    async with db_pool.acquire() as conn:
        result = await conn.execute(sql, *(params or []))
        return {"result": result}

async def initialize_db():
    global db_pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing")
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size = 2, 
                                        max_size = 5, max_inactive_connection_lifetime = 300)
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users 
            (id SERIAL PRIMARY KEY, username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations
            (id VARCHAR(255) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_members
            (conv_id VARCHAR(255), username VARCHAR(255),
            PRIMARY KEY (conv_id, username))""")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages 
            (id SERIAL PRIMARY KEY, conv_id VARCHAR(255),
            sender VARCHAR(255), encrypted_body TEXT NOT NULL,
            iv VARCHAR(255) NOT NULL, is_public BOOLEAN DEFAULT FALSE,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs 
            (id SERIAL PRIMARY KEY, username VARCHAR(255),
            action VARCHAR(255), detail VARCHAR(255), 
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts 
            (username VARCHAR(255) PRIMARY KEY,
            attempts INT DEFAULT 0, 
            last_try TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_pw(pw, stored_hash):
    try:
        return bcrypt.checkpw(pw.encode(), stored_hash.encode())
    except Exception:
        return False

def password_needs(pw):
    if len(pw) < 15:
        return False, "Password Must Have Atleast 15 Characters"
    if not any(c.isupper() for c in pw):
        return False, "Passsword Must Have Atleast 1 Uppercase"
    if not any(c.islower() for c in pw):
        return False, "Passsword Must Have Atleast 1 Lowercase"
    if not any(c.isdigit() for c in pw):
        return False, "Passsword Must Have Atleast 1 Number"
    if not any(not c.isalnum() for c in pw):
        return False, "Passsword Must Have Atleast 1 Special Character"
    return True, ""

def sanitize(text):
    return re.sub(r"<[^>]+>", "", str(text))[:500]

def make_conv_id(a, b):
    return "dm_" + "_".join(sorted([a, b]))

async def db_log(username, action, detail = ""):
    try:
        await db_execute("INSERT INTO logs (username, action, detail) VALUES ($1,$2,$3)",
        [username, action, sanitize(detail)])
    except Exception:
        pass

def ts_to_str(value):
    if value is None:
        return ""
    if hasattr(value, "tzinfo"):
        if value.tzinfo is None:
            value = value.replace(tzinfo = timezone.utc)
        value = value.astimezone(LOCAL_TZ)
        return value.strftime("%H:%M:%S")
    return str(value)

clients = set()
clients_lock = asyncio.Lock()
active_users = {}
typing_users = defaultdict(set)
rate_tracker = defaultdict(list)

def is_rate_limited(username):
    now = time.monotonic()
    rate_tracker[username] = [t for t in rate_tracker[username] if now - t < 60]
    if len(rate_tracker[username]) >= MAX_MSG_PER_MINUTE:
        return True
    rate_tracker[username].append(now)
    return False

async def send_to_ws(ws, payload):
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        pass

async def send_to_user(username, payload):
    async with clients_lock:
        for ws, name in active_users.items():
            if name == username:
                try:
                    await ws.send(json.dumps(payload))
                    return True
                except Exception:
                    return False
    return False

async def broadcast_user_list():
    async with clients_lock:
        names = list(active_users.values())
        payload = json.dumps({"type": "userlist", "names": names})
        for ws in clients:
            try:
                await ws.send(payload)
            except Exception:
                pass

async def broadcast_public(payload, sender_ws = None):
    async with clients_lock:
        data = json.dumps(payload)
        dead = []
        for ws in clients:
            if sender_ws is not None and ws is sender_ws:
                continue
            try:
                await ws.send(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

async def handle_public_msg(ws, username, payload):
    if is_rate_limited(username):
        await send_to_ws(ws, {"type": "error", "msg": "Rate Limit Reached"})
        return
    enc = payload.get("encrypted_body", "")
    iv = payload.get("iv", "")
    if not enc or not iv:
        return
    ts = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
    try:
        await db_execute(
            "INSERT INTO messages (conv_id, sender, encrypted_body, iv, is_public) VALUES ($1,$2,$3,$4,TRUE)",
            [None, username, enc, iv])
    except Exception:
        pass

    await db_log(username, "public_msg")
    typing_users["public"].discard(username)
    entry = {"type": "public_msg", "from": username, "encrypted_body": enc, "iv": iv, "ts": ts}

    async with clients_lock:
        data = json.dumps(entry)
        for ws2 in clients:
            try:
                await ws2.send(data)
            except Exception:
                pass

async def handle_send_msg(ws, username, payload):
    if is_rate_limited(username):
        await send_to_ws(ws, {"type": "error", "msg": "Rate limit reached."})
        return
    conv_id = payload.get("conv_id", "")
    enc = payload.get("encrypted_body", "")
    iv = payload.get("iv", "")
    if not conv_id or not enc or not iv:
        return
    rows = await db_query("SELECT username FROM conversation_members WHERE conv_id=$1", [conv_id])
    members = [r["username"] for r in rows]

    if username not in members:
        await send_to_ws(ws, {"type": "error", "msg": "Not a member of that conversation."})
        return
    ts = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
    try:
        await db_execute(
            "INSERT INTO messages (conv_id,sender,encrypted_body,iv,is_public) VALUES ($1,$2,$3,$4,FALSE)",
            [conv_id, username, enc, iv]
        )
    except Exception:
        pass
    await db_log(username, "dm_msg", f"conv={conv_id}")
    typing_users[conv_id].discard(username)
    entry = {"type": "chat", "conv_id": conv_id, "from": username, "encrypted_body": enc, "iv": iv, "ts": ts}
    for member in members:
        await send_to_user(member, entry)

async def handle_create_conv(ws, username, payload):
    target = payload.get("with", "").strip()
    if not target:
        return

    async with clients_lock:
        online = list(active_users.values())

    if target not in online:
        await send_to_ws(ws, {"type": "error", "msg": f"'{target}' is not online."})
        return

    if target == username:
        await send_to_ws(ws, {"type": "error", "msg": "You can't chat with yourself."})
        return
    conv_id = make_conv_id(username, target)

    await db_execute(
        "INSERT INTO conversations (id) VALUES ($1) ON CONFLICT (id) DO NOTHING",
        [conv_id])

    await db_execute(
        "INSERT INTO conversation_members (conv_id,username) VALUES ($1,$2) ON CONFLICT (conv_id, username) DO NOTHING",
        [conv_id, username])

    await db_execute(
        "INSERT INTO conversation_members (conv_id,username) VALUES ($1,$2) ON CONFLICT (conv_id, username) DO NOTHING",
        [conv_id, target])

    rows = await db_query(
        "SELECT sender,encrypted_body,iv,sent_at FROM messages WHERE conv_id=$1 ORDER BY sent_at DESC LIMIT $2",
        [conv_id, MAX_HISTORY])

    history = [
        {"from": r["sender"], "encrypted_body": r["encrypted_body"], "iv": r["iv"], "ts": ts_to_str(r["sent_at"])}
        for r in reversed(rows)]

    await db_log(username, "create_conv", f"with={target}")
    await send_to_ws(ws, {"type": "new_conv", "conv_id": conv_id, "with": target, "history": history})
    await send_to_user(target, {"type": "new_conv", "conv_id": conv_id, "with": username, "history": history})

async def handle_lookup_user(ws, username, payload):
    query = payload.get("query", "").strip().lower()
    async with clients_lock:
        matches = [n for n in active_users.values() if query in n.lower() and n != username]
    await send_to_ws(ws, {"type": "user_lookup_result", "matches": matches})

async def handle_typing(ws, username, payload):
    conv_id = payload.get("conv_id", "public")
    is_typing = payload.get("typing", False)
    if is_typing:
        typing_users[conv_id].add(username)
    else:
        typing_users[conv_id].discard(username)
    notif = {"type": "typing", "conv_id": conv_id, "users": list(typing_users[conv_id])}
    if conv_id == "public":
        await broadcast_public(notif, sender_ws=ws)
    else:
        rows = await db_query("SELECT username FROM conversation_members WHERE conv_id=$1", [conv_id])
        members = [r["username"] for r in rows]
        for m in members:
            if m != username:
                await send_to_user(m, notif)

async def handle_file(ws, username, payload):
    if is_rate_limited(username):
        await send_to_ws(ws, {"type": "error", "msg": "Rate limit reached."})
        return

    filename = payload.get("name", "file")
    size = payload.get("size", 0)
    url = payload.get("url", "")
    iv = payload.get("iv", "")
    conv_id = payload.get("conv_id")
    blocked = {".exe", ".bat", ".sh", ".ps1", ".cmd", ".msi", ".dll", ".vbs"}

    if os.path.splitext(filename)[1].lower() in blocked:
        await send_to_ws(ws, {"type": "error", "msg": "That file type is blocked."})
        return
    if size > 10 * 1024 * 1024:
        await send_to_ws(ws, {"type": "error", "msg": "File too large (10 MB max)."})
        return
    if not url or not iv:
        await send_to_ws(ws, {"type": "error", "msg": "File missing url or iv."})
        return

    payload["from"] = username
    payload["ts"] = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")

    await db_log(username, "file_send", sanitize(filename))
    if conv_id:
        rows = await db_query("SELECT username FROM conversation_members WHERE conv_id=$1", [conv_id])
        members = [r["username"] for r in rows]
        for m in members:
            await send_to_user(m, payload)
    else:
        await broadcast_public(payload)

# authorization
async def check_lockout(username):
    try:
        rows = await db_query(
            "SELECT attempts, last_try FROM login_attempts WHERE username=$1",
            [username]
        )
        if not rows:
            return False
        last_try = rows[0]["last_try"]
        if last_try is not None:
            if last_try.tzinfo is None:
                last_try = last_try.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_try).total_seconds()
            if elapsed > 900:
                await db_execute("DELETE FROM login_attempts WHERE username=$1", [username])
                return False
        return int(rows[0]["attempts"]) >= LOGIN_ATTEMPT_LIMIT
    except Exception:
        return False

async def record_failed(username):
    try:
        await db_execute("""
            INSERT INTO login_attempts (username,attempts,last_try)
            VALUES ($1,1,CURRENT_TIMESTAMP) ON CONFLICT (username)
            DO UPDATE SET attempts = login_attempts.attempts + 1,
            last_try = CURRENT_TIMESTAMP """, [username])
    except Exception:
        pass

async def clear_failed(username):
    try:
        await db_execute("DELETE FROM login_attempts WHERE username=$1", [username])
    except Exception:
        pass

async def recv_line(ws):
    try:
        msg = await ws.recv()
        return "" if msg is None else str(msg).strip()
    except Exception:
        return ""

# main functions
async def handle_connection(ws):
    username = None
    try:
        while True:
            await send_to_ws(ws, {"type": "auth_prompt", "msg": "Mode? (L=login, R=register):"})
            raw_mode = await recv_line(ws)

            if not raw_mode:
                return
            mode = raw_mode.upper()

            if mode not in ("L", "R"):
                await send_to_ws(ws, {"type": "auth_error", "msg": "Enter L or R."})
                continue
            await send_to_ws(ws, {"type": "auth_prompt", "msg": "Username:"})
            username = await recv_line(ws)

            if not username:
                return
            await send_to_ws(ws, {"type": "auth_prompt", "msg": "Password:"})
            password = await recv_line(ws)

            if not password:
                return

            if mode == "R":
                ok, reason = password_needs(password)
                if not ok:
                    await send_to_ws(ws, {"type": "auth_error", "msg": f"Registration failed: {reason}"})
                    continue
                rows = await db_query("SELECT 1 FROM users WHERE username=$1", [username])
                if rows:
                    await send_to_ws(ws, {"type": "auth_error", "msg": "Username already exists."})
                    continue
                await db_execute(
                    "INSERT INTO users (username,password_hash) VALUES ($1,$2)",
                    [username, hash_pw(password)])

                await db_log(username, "register")
                await send_to_ws(ws, {"type": "auth_ok", "msg": "Registered! You can now log in."})
                continue

            if await check_lockout(username):
                await send_to_ws(ws, {"type": "auth_error", "msg": "Account locked – too many failed attempts."})
                await ws.close(code=4001)
                return

            rows = await db_query(
                "SELECT password_hash FROM users WHERE username=$1", [username])
            ok = bool(rows) and verify_pw(password, rows[0]["password_hash"])
            if not ok:
                await record_failed(username)
                await send_to_ws(ws, {"type": "auth_error", "msg": "Credentials do not match."})
                continue
            await clear_failed(username)
            async with clients_lock:
                already_on = username in active_users.values()

            if already_on:
                await send_to_ws(ws, {"type": "auth_error", "msg": "That account is already logged in."})
                continue

            await db_log(username, "login")
            break

        async with clients_lock:
            clients.add(ws)
            active_users[ws] = username
            print(f"[JOIN] {username} | clients={len(clients)} users={len(active_users)}", flush = True)

        conv_rows = await db_query(
            "SELECT conv_id FROM conversation_members WHERE username=$1", [username])
        
        my_conv_ids = [r["conv_id"] for r in conv_rows]
        my_convs = []

        for cid in my_conv_ids:
            partner_rows = await db_query(
                "SELECT username FROM conversation_members WHERE conv_id=$1 AND username!=$2",
                [cid, username])
            partner = partner_rows[0]["username"] if partner_rows else "?"

            msg_rows = await db_query(
                "SELECT sender,encrypted_body,iv,sent_at FROM messages WHERE conv_id=$1 ORDER BY sent_at DESC LIMIT $2",
                [cid, MAX_HISTORY])

            history = [
                {"from": r["sender"], "encrypted_body": r["encrypted_body"], "iv": r["iv"], "ts": ts_to_str(r["sent_at"])}
                for r in reversed(msg_rows)]

            my_convs.append({"conv_id": cid, "with": partner, "history": history})

        pub_rows = await db_query(
            "SELECT sender,encrypted_body,iv,sent_at FROM messages WHERE is_public=TRUE ORDER BY sent_at DESC LIMIT $1",
            [MAX_HISTORY])
        pub_history = [
            {"from": r["sender"], "encrypted_body": r["encrypted_body"], "iv": r["iv"], "ts": ts_to_str(r["sent_at"])}
            for r in reversed(pub_rows)]

        await send_to_ws(ws, {
            "type": "init",
            "username": username,
            "conversations": my_convs,
            "public_history": pub_history,})

        await broadcast_user_list()
        await broadcast_public({"type": "system", "msg": f"{username} joined."}, sender_ws = ws)

        while True:
            raw = await recv_line(ws)
            if not raw:
                break
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            t = payload.get("type", "")

            if t == "public_msg":
                await handle_public_msg(ws, username, payload)
            elif t == "send_msg":
                await handle_send_msg(ws, username, payload)
            elif t == "create_conv":
                await handle_create_conv(ws, username, payload)
            elif t == "lookup_user":
                await handle_lookup_user(ws, username, payload)
            elif t == "file":
                await handle_file(ws, username, payload)
            elif t == "typing":
                await handle_typing(ws, username, payload)

    except Exception as e:
        import traceback
        print(f"[Connection error] {type(e).__name__}: {e}", flush = True)
        traceback.print_exc()
    finally:
        async with clients_lock:
            clients.discard(ws)
            if ws in active_users:
                del active_users[ws]
            if username:
                print(f"[LEAVE] {username} | clients={len(clients)} users={len(active_users)}", flush = True)
        if username:
            rate_tracker.pop(username, None)
            await db_log(username, "disconnect")
            await broadcast_user_list()
            await broadcast_public({"type": "system", "msg": f"{username} left."})

# aiohttp
class AiohttpWSAdapter:
    def __init__(self, ws):
        self._ws = ws

    async def send(self, data: str):
        await self._ws.send_str(data)

    async def recv(self) -> str:
        msg = await self._ws.receive()

        if msg.type == aiohttp.WSMsgType.TEXT:
            return msg.data
        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSING):
            raise ConnectionError("ws closed")
        return ""

    async def close(self, code=1000):
        await self._ws.close(code=code)


async def ws_handler(request):
    ws = web.WebSocketResponse(max_msg_size = 16 * 1024 * 1024)
    await ws.prepare(request)
    adapter = AiohttpWSAdapter(ws)
    await handle_connection(adapter)
    return ws

async def health_handler(request):
    return web.Response(text="OK")

def handle_exception(loop, context):
        msg = context.get("exception", context["message"])
        print(f"[UNHANDLED] {msg}", flush=True)
        if "exception" in context:
            import traceback
            traceback.print_exception(type(context["exception"]), context["exception"], 
                                       context["exception"].__traceback__)

async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(handle_exception)
    loop.slow_callback_duration = 1.0
    await initialize_db()
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/ws", ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print("SEC SERVER UP")
    while True:
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())