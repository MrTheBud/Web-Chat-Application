# Capstone Project **SEC** Secure / Encrypted / Chat

A real-time communication tool that is developed in Python/Html, called **SEC**, that allows anyone to communicate in a secure and efficient way whether in public or private message.

## Developers 👤

- **Class**: CPSC 455-01
- **Professor**: Michael Franklin
- **Group Members**:
1. Kevin Perez
2. Alex Islas
3. Dino Rozac

## What it does 🔨

- A client-server WebSocket-based chat system enables team members to communicate in real time. To accomplish this, the requirements are as follows:

1. **Real-Time Messaging** - Messages instantly appear
2. **Backend Server** - Python, Aiohttp, Asyncio, Hosted on Render
3. **Frontend** - Html, InfinityFree
4. **Secure File Sharing** - Firebase
5. **User Authentication** - Basic authentication method
6. **Rate Limiting** - Implement anti spamming method
7. **24/7 Uptime** - Uptime Robot Pinging the Server every 10 minutes, and Render starter Tier

## How to Run

1. Go to https://sec.infinityfreeapp.com/ any web browser
2. Fill Out Your Birthdate
   <img width="445" height="342" alt="image" src="https://github.com/user-attachments/assets/92841620-b558-4bbb-a2bb-1df91d7e4b3c" />
**MUST BE OLDER THAN 18**

3. Type R in the chat box to register an account
   <img width="763" height="496" alt="image" src="https://github.com/user-attachments/assets/83e6ff9a-c4e4-4675-8839-9463187be0e0" />
   **Follow The Password Requirement On Screen**
   **If Requirements Not Met The Prompt Will Blink**

5. Type L with the same credential you used to register
   **If Credential Do Not Match The Prompt Will Blink**

6. CHAT
   <img width="1920" height="1032" alt="image" src="https://github.com/user-attachments/assets/58a5d265-61c9-4f36-b5c1-998277770454" />

## What Has Changed

This repository retains the original team project and its core chat features. The following updates clarify and change how the current version handles encryption and configuration:

- The client now asks for a private passphrase of at least 16 characters after age verification. This replaces the hard-coded shared passphrase used by an earlier version.
- The browser derives an AES-GCM encryption key from that passphrase and uses it for chat messages and files. The passphrase is not sent to the chat server or saved by the client. Users who need to read the same content must enter the same passphrase.
- `.gitignore` now excludes environment files and common service-account/private-key files to help prevent accidental additions. This does not remove files that are already tracked or secrets in Git history.
- The security notes below distinguish public Firebase client configuration from private server credentials and explain that Firebase Storage access must be controlled by Firebase security rules.

**Legacy data and repository history:** Earlier public commits include the former hard-coded chat passphrase. Treat messages and files encrypted with that legacy passphrase as potentially readable by anyone who can access their ciphertext. Changing the current client does not erase that passphrase from existing Git history or re-encrypt old data.

## Security and Configuration

- After age verification, enter a private passphrase of at least 16 characters. Everyone in a conversation must enter the exact same passphrase to read its messages and files. Choose a long, unique phrase and share it only through a trusted channel. The app does not save the phrase or send it to the chat server.
- The shared passphrase is held in browser memory for the current page session. If it is lost or changed, messages and files encrypted with the previous phrase cannot be read.
- `DATABASE_URL` is read from the server environment; do not put database credentials, service-account keys, or other server secrets in frontend files or commit them to Git.
- The Firebase web configuration in `frontend_sec.html` identifies the Firebase project and is public client configuration, not a private credential. Restrict its API key where applicable and configure Firebase Storage security rules in Firebase Console; the client configuration itself does not control access.
- The public deployment host and project URLs are identifiers, not credentials. Protect access through server authorization, Firebase rules, and deployment settings rather than relying on hiding public URLs.
