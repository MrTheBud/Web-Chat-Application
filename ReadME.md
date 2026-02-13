# Project 1 - Client-Server Communication using Web Sockets 🔌💻🔌

A real-time communication tool that is developed in Python, called **SecureChat**, that allows remote teams to communicate in a secure and efficient communication. 

## Developers 👤

- **Class**: CPSC 455-01
- **Professor**: Michael Franklin
- **Group Members**:
1. Kevin Perez
2. Alex Islas
3. Dino Rozac

## What it does 🔨

- A client-server WebSocket-based chat system enables team members to communicate in real time. To accomplish this, the requirement are as follows:

1. Real-Time Messaging - messages instantly appear
2. Secure Conenction - wss://
3. User Authentication - Basic authentication method
4. Rate Limiting - Implement anti spamming method
5. Connection Handling - Detects and connects connections as well as reconnects in terms of interruptions

## How to Run 💡

For a Windows 11 OS with the goal being to run two clients on the same device, follow these instructions 

1. Download Python and make sure it is in PATH

 * If do not have Python, download from https://python.org/
 * To verify, open Command Prompt and run either of the following commands:

         py -m pip install websockets
      
         python --version

  **INSERT IMAGE HERE**

2. Power on Visual Studio and open up a Project labled "Project 1 - Client-Server Communication using Web Sockets"

  **INSERT IMAGE HERE**

3. Move Server.py, Client.py, cert.pem, and key.pem into the folder containing the project. Open both Server.py and Client.py

  **INSERT IMAGE HERE**

  **INSERT IMAGE HERE**

4. Install Required Python Libraries

    * View tab on top of Visual Studio (VS) labeled "Terminal"
    * Make sure that terinal has correct path:

  **INSERT IMAGE HERE**

 * Type into the terminal the following command and press Enter

         py -m pip install websockets

  **INSERT IMAGE HERE**

 * Type into the terminal the following command and press Enter

         py -m pip install websocket-client”

  **INSERT IMAGE HERE**

5. Run Server.py by typing into the terminal and pressing Enter the following command:

         py server.py

  **INSERT IMAGE HERE**

6. Check your IP Address by openning Command Prompt and typing in the following command:

         ipconfig

  **INSERT IMAGE HERE**

7. Change to Client.py and input the IP Address into "Host = [insert IP Address here]"

      * Please note, if you are running the client and server on the same device, you can use either of the following:
  
         * "Host = localhost"

         * "Host = 127.0.0.1"
  
  **INSERT IMAGE HERE**

8. Run Client.py in a new terminal

* At the top of the VS Terminal, press the "+" to open up another terminal
  
  **INSERT IMAGE HERE**

* Start the file by typing the following code into the terminal and pressing enter:

         py client.py

  **INSERT IMAGE HERE**
 
9. Register a User (for the first time you run the client on the server)

* Press "R", and then input a username and password
* Will be logged out once registered, so press "connect" to continue
        
  **INSERT IMAGE HERE**

10) Login as User:

      * Press "L", and then input username and password
      * Once logged in, you will be able to send messages

  **INSERT IMAGE HERE**
   
11. Run Client.py in a new terminal to create a second user

* At the top of the VS Terminal, press the "+" to open up another terminal
* Type in the following code in the terminal and press Enter:
      
         "py client.py"
      
* Repeat steps 10 - 11 for a second client using the third terminal

  **INSERT IMAGE HERE**

12. Enjoy the connection: typing in either will have the message reach the other

  **INSERT IMAGE HERE**

## Customization 🔍

How do you change it to try with one client and one VM

How do you change connect two people who are on the same network, with one person being the host and giving their IP to the other client
 
## Technical Details 📃

* OS Types: Windows 11 and Tuffix 2022
* Python version: 3.9.13
* Websockets: 
* Websockets clients: 
* Visual Studio [Version: VS 2022 (x64) Version 17.14.26 for demo]


