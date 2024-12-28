import socket
import threading

def recive_message(client_socket):
    while True:
        responseData = client_socket.recv(4096).decode('utf-8')
        print(f"{responseData}")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = '0.0.0.0'
server_port = 9001

client_address = '0.0.0.0'
client_port = 0

#すでにほかのクライアントにポートが使われていた時
try:
    client_socket.bind((client_address, client_port))
except OSError as e:
    print(f"Error: {e}. Please choose a different port.")
    exit()


username = input("please username(max:255): ")
#ユーザー名の長さがオーバーしたとき
if len(username) > 255:
    print("username exceeds the maximum value.")
    exit()

#ユーザー名を送信
client_socket.sendto(username.encode('utf-8'), (server_address, server_port))

receiver_thread = threading.Thread(target=recive_message, args=(client_socket, ))
receiver_thread.start()

try:
    while True:
        message = input()
        client_socket.sendto(message.encode('utf-8'), (server_address, server_port))
except KeyboardInterrupt:
    client_socket.close()
    print("client closed")