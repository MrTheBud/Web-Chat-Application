# Made By: Kevin Perez
import tkinter as tk
from tkinter import scrolledtext, filedialog
import os

#button functions
def send_message(event=None):
    msg = entry.get().strip()
    if not msg:
        return
    chat.configure(state="normal")
    chat.insert("end", f"You: {msg}\n")
    chat.configure(state="disabled")
    chat.see("end")
    entry.delete(0, "end")

def clear_chat():
    chat.configure(state="normal")
    chat.delete("1.0", "end")
    chat.configure(state="disabled")

def disconnect():
    root.destroy()

#gui settings
root = tk.Tk()
root.title("SecChat")
root.geometry("950x550")
root.configure(bg="black")
#title
title = tk.Label(root, text="SecChat", font=("Times New Roman", 36), bg="black", fg="green")
title.place(relx=1.0, x=-100, y=15, anchor="ne")


#chat box
chat = tk.Text(
    root,
    wrap="word",
    font=("Times New Roman", 14),
    bg="black",
    fg="white",
    insertbackground="white"
)
chat.configure(state="disabled")
chat.place(x=10, y=10, relwidth=0.60, relheight=0.80)

#image 


#buttons and clicking functions
send_btn = tk.Button(root, text="Send", padx=20, pady=10, bg="green", fg="black", command=send_message)
send_btn.place(relx=1.0, rely=1.0, anchor="se", x=-275, y=-10)

clear_btn = tk.Button(root, text="Clear", padx=20, pady=10, bg="green", fg="black", command=clear_chat)
clear_btn.place(relx=1.0, rely=1.0, anchor="se", x=-150, y=-10)

entry = tk.Entry(root, font=("Times New Roman", 16), width=50,
                 bg="gray15", fg="white", insertbackground="white")
entry.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-10)

disc_btn = tk.Button(root, text="Disconnect", padx=20, pady=10, bg="green", fg="black", command=disconnect)
disc_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

root.bind("<Return>", send_message)

root.mainloop()