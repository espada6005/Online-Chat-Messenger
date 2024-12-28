import socket
from datetime import datetime

class User:
    def __init__(self, username):
        self.username = username
        self.last_visited_time = datetime.now()
        self.exists = True

    def update_last_visited_time(self):
        self.last_visited_time = datetime.now()

    def is_session_active(self):
        timeout_seconds = 60
        time_difference = datetime.now() - self.last_visited_time
        return time_difference.seconds <= timeout_seconds

class Server:
    def __init__(self):
        self.clients = {}
        self.server_address = ("0.0.0.0", 9001)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(self.server_address)

    def start(self):
        print("starting socket server")
        try:
            while True:
                client_message_bytes, send_client_address = self.server_socket.recvfrom(4096)
                client_message = client_message_bytes.decode("utf-8")
                self.handle_client_message(client_message, send_client_address)
        except Exception as e:
            print("Error: ", e)
        finally:
            self.server_socket.close()

    def handle_client_message(self, client_message, send_client_address):
        if send_client_address not in self.clients:
            self.register_new_client(client_message, send_client_address)
        else:
            self.process_client_message(client_message, send_client_address)

    def register_new_client(self, client_message, send_client_address):
        self.clients[send_client_address] = User(client_message)
        print("Session in user: " + self.clients[send_client_address].username)

    def process_client_message(self, client_message, send_client_address):
        client = self.clients[send_client_address]

        if not client.exists:
            return

        if not client.is_session_active():
            client.exists = False
            print("Session out user: " + client.username)
            return
        
        if client_message:
            client.update_last_visited_time()
            response_message = client.username + ": " + client_message
            self.relay_message(response_message, send_client_address)

    def relay_message(self, message, sender_address):
        for receive_client_address, client in self.clients.items():
            if not client.is_session_active():
                client.exists = False
                print("Session out user: " + client.username)
                continue
            if sender_address == receive_client_address:
                continue
            self.server_socket.sendto(message.encode("utf-8"), receive_client_address)

if __name__ == "__main__":
    try:
        server = Server()
        server.start()
    except KeyboardInterrupt:
        server.server_socket.close()
        print("server closed")