#Made By: Kevin Perez, Alex Islas, Dino Rozac

# NOTES: TO FIX: 
# function update_sidebar() not showing users

import time
import tkinter as tk
from tkinter import simpledialog, filedialog # For input dialogs, file selection, and message boxes
import threading
import ssl
from websocket import WebSocketApp  # pip install websocket-client
import base64

#IPv4 Only change needed to be made by client
HOST = "localhost" # Change to server's IP address or use "localhost" for local testing
PORT = 9999 # Must match the port used in server.py
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

#=========================================================================
def switch_chat(target_name):
    entry.delete(0, "end")
    entry.insert(0, f"/msg {target_name} ")
    entry.focus()
    chat_insert(f"--- Private Chat with {target_name} ---")

def on_message(ws, message):
    msg = str(message)
    print(f"DEBUG: Server sent -> {msg}") # Look at your terminal to see this!
    
    if msg.startswith("USERLIST:"):
        raw_names = msg.replace("USERLIST:", "")
        # If raw_names is empty, we get [''], so we filter that out
        name_list = [n for n in raw_names.split(",") if n]
        root.after(0, update_sidebar, name_list)
    else: 
        root.after(0, chat_insert, msg)

def update_sidebar(names):
    # Clear old buttons
    for widget in sidebar.winfo_children(): 
        if isinstance(widget, tk.Button):
            widget.destroy()

    # Re-create buttons
    for name in names: 
        btn = tk.Button(
            sidebar,
            text=name,
            bg="gray25", 
            fg="white",
            font=("Arial", 10, "bold"),
            command=lambda n=name: switch_chat(n)
        )
        btn.pack(fill="x", padx=5, pady=2)
    
    # Forces the GUI to redraw immediately
    sidebar.update()

# Emoji Picker Popup Logic
def open_emoji_menu():
    # Create a popup window (Toplevel)
    emoji_window = tk.Toplevel(root)
    emoji_window.title("Emojis")
    emoji_window.geometry("150x200")
    emoji_window.overrideredirect(True) # Removes window borders for a clean look
    emoji_window.configure(bg="gray15")

    # Position the popup right above the emoji button
    x = emoji_btn.winfo_rootx()
    y = emoji_btn.winfo_rooty() - 210
    emoji_window.geometry(f"+{x}+{y}")

    # List of Emojis
    emojis = ["😀", "😂", "🚀", "🔥", "👍", "🔒", "✅", "👀", "💻", "💡"]
    
    # Grid them out inside the popup
    r, c = 0, 0
    for e in emojis:
        ebtn = tk.Button(emoji_window, text=e, font=("Arial", 12), bg="gray25", fg="white", 
                         relief="flat", command=lambda char=e: [entry.insert(tk.INSERT, char), emoji_window.destroy()])
        ebtn.grid(row=r, column=c, padx=5, pady=5)
        c += 1
        if c > 2: # 3 emojis per row
            c = 0; r += 1
    
    # Close popup if user clicks away
    emoji_window.bind("<FocusOut>", lambda e: emoji_window.destroy())
    emoji_window.focus_set()
#=========================================================================


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

# Entry box for message input
entry = tk.Entry(root, font=("Times New Roman", 16), width=50, bg="gray15", fg="white", insertbackground="white")
entry.place(relx=0.0, rely=1.0, anchor="sw", x=60, y=-10, width=500, height=35)

# Emoji Button
emoji_btn = tk.Button(root, text="😀", font=("Times New Roman" ,14), bg="gray15", fg="white", relief="flat", command=open_emoji_menu)
emoji_btn.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-10, width=45, height=35)

#Misc Buttons
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

fle_btn = tk.Button(root, text='file', padx=20, pady= 10, bg='green', fg='black')#add command
fle_btn.place(relx=1.0, rely=1.0, anchor='se', x=-275, y=-60)

#Sidebar for active users
sidebar = tk.Frame(root, width=150, bg="gray10")
sidebar.place(relx=1.0, x=-95, y=80, anchor="ne", width=180, height=350)

tk.Label(sidebar, text="ONLINE USERS", bg="gray10", fg="green", font=("Times New Roman", 12, "bold")).pack(pady=5)

root.bind("<Return>", send_message)

ws_thread = threading.Thread(target=connect_to_server, daemon=True)
ws_thread.start()

root.mainloop()