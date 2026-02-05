#Dev: Alex Islas

# ftp_server.py
# A simple FTP server using pyftpdlib (for file transfer functionality)

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

authorizer = DummyAuthorizer()
authorizer.add_user("alice", "pass123", "./files", perm="elradfmw")  # e for enter, l list, etc.
authorizer.add_user("bob", "secret", "./files", perm="elradfmw")

handler = FTPHandler
handler.authorizer = authorizer

server = FTPServer(("localhost", 2121), handler)
server.serve_forever()