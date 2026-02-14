#Made By: Kevin Perez, Alex Islas, Dino Rozac
import time
import tkinter as tk
import threading
import ssl
from websocket import WebSocketApp  # pip install websocket-client

#IPv4 Only change needed to be made by client
HOST = "192.168.110.1"
PORT = 9999
WSS_URL = f"wss://{HOST}:{PORT}"

ping_int = 20
ping_out = 10
reconnect_delay = 2.0
send_rate = 1.0

ws_app = None
connected = False
auto_reconnect = True
ws_thread = None
last_send_time = 0.0

def chat_insert(text: str):
    chat.configure(state="normal")
    chat.insert("end", text + "\n")
    chat.configure(state="disabled")
    chat.see("end")

def on_message(ws, message):
    root.after(0, chat_insert, str(message))

def on_open(ws):
    global connected
    connected = True
    root.after(0, chat_insert, "[Connected]")

def on_close(ws, code, reason):
    global connected, auto_reconnect
    connected = False

def on_error(ws, error):
    root.after(0, chat_insert, f"[Error]")

def connect_to_server():
    global ws_app

    sslopt = {"cert_reqs": ssl.CERT_NONE}

    while auto_reconnect:
        if connected:
            time.sleep(1)
            continue

        try:
            ws_app = WebSocketApp(
                WSS_URL,
                on_open=on_open,
                on_message=on_message,
                on_close=on_close,
                on_error=on_error,
            )

            ws_app.run_forever(
                sslopt=sslopt,
                ping_interval=ping_int,
                ping_timeout=ping_out,
            )

        except Exception as e:
            root.after(0, chat_insert, f"[Reconnect error]")

        time.sleep(reconnect_delay)

def start_connection():
    global ws_thread, auto_reconnect

    auto_reconnect = True

    if connected:
        chat_insert("[Already connected]")
        return

    if ws_thread and ws_thread.is_alive():
        chat_insert("[Connecting...]")
        return

    ws_thread = threading.Thread(target=connect_to_server, daemon=True)
    ws_thread.start()
    chat_insert("[Connecting...]")

def disconnect():
    global connected, ws_app, auto_reconnect

    auto_reconnect = False
    connected = False

    try:
        if ws_app:
            ws_app.close()
    except Exception:
        pass

    ws_app = None
    chat_insert("[Disconnected]")

def send_message(event=None):
    global last_send_time

    msg = entry.get().strip()
    if not msg:
        return

    if not connected or ws_app is None:
        chat_insert("[Not connected]")
        return

    now = time.monotonic()
    if now - last_send_time < send_rate:
        chat_insert("Wait a second.")
        return

    last_send_time = now
    entry.delete(0, "end")

    try:
        ws_app.send(msg)
    except Exception as e:
        chat_insert(f"[Send failed] {e}")

def clear_chat():
    chat.configure(state="normal")
    chat.delete("1.0", "end")
    chat.configure(state="disabled")

def close():
    global connected
    connected = False
    try:
        if ws_app:
            ws_app.close()
    except Exception:
        pass
    root.destroy()

#Gui
root = tk.Tk()
root.title("SecChat")
root.geometry("950x550")
root.configure(bg="black")

title = tk.Label(root, text="SecChat", font=("Times New Roman", 36), bg="black", fg="green")
title.place(relx=1.0, x=-100, y=15, anchor="ne")

chat = tk.Text(
    root,
    wrap="word",
    font=("Times New Roman", 14),
    bg="black",
    fg="white",
    insertbackground="white",
)
chat.configure(state="disabled")
chat.place(x=10, y=10, relwidth=0.60, relheight=0.80)

entry = tk.Entry(root, font=("Times New Roman", 16), width=50, bg="gray15", fg="white", insertbackground="white")
entry.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-10)

send_btn = tk.Button(root, text="Send", padx=20, pady=10, bg="green", fg="black", command=send_message)
send_btn.place(relx=1.0, rely=1.0, anchor="se", x=-275, y=-10)

clear_btn = tk.Button(root, text="Clear", padx=20, pady=10, bg="green", fg="black", command=clear_chat)
clear_btn.place(relx=1.0, rely=1.0, anchor="se", x=-150, y=-10)

close_btn = tk.Button(root, text="Close", padx=20, pady=10, bg="green", fg="black", command=close)
close_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

disc_btn = tk.Button(root, text="Disconnect", padx=20, pady=10, bg="green", fg="black", command=disconnect)
disc_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-60)

conn_btn = tk.Button(root, text="Connect", padx=20, pady=10, bg="green", fg="black", command=start_connection)
conn_btn.place(relx=1.0, rely=1.0, anchor="se", x=-135, y=-60)

root.bind("<Return>", send_message)

ws_thread = threading.Thread(target=connect_to_server, daemon=True)
ws_thread.start()

root.mainloop()
