import json
import secrets
import socket
import struct
import threading
from concurrent.futures import ThreadPoolExecutor

import chat_room

class Server:
    def __init__(self):
        self.tcp_address = ("127.0.0.1", 9002)
        self.udp_address = ("127.0.0.1", 9003)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket.bind(self.tcp_address)
        self.udp_socket.bind(self.udp_address)
        self.rooms = {}
        # クライアントアクション
        self.CREATE_ROOM = 1
        self.JOIN_ROOM = 2
        self.QUIT = 3
        # State
        self.SERVER_INIT = 0
        self.REQUEST_OF_RESPPONSE = 1
        self.REQUEST_COMPLETION = 2
        self.ERROR_RESPONSE = 3
    
    def start(self):
        """サーバーを起動する"""
        print("Server started Port: 9002")

        while True:
            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    executor.submit(self.__hand_tcp_con)
                    executor.submit(self.__handle_udp_conn)
            except:
                self.tcp_socket.close()
                self.udp_socket.close()
                print("\nServer Closed")
                break

    def __hand_tcp_con(self):
        """TCP接続を処理する"""
        HEADER_BYTE_SZIE = 32
        while True:
            self.tcp_socket.listen(5)
            conn, _ = self.tcp_socket.accept()

            try:
                # クライアントデータ受信
                header = conn.recv(HEADER_BYTE_SZIE)
                room_name_size, operation, _, _ = struct.unpack_from("!B B B 29s", header)
                
                body = conn.recv(4096)
                room_name = body[:room_name_size].decode("utf-8")
                operation_payload = body[room_name_size:].decode("utf-8")

                # OperationPayloadを辞書に変換
                payload = json.loads(operation_payload)
                user_name = payload["user_name"]
                user_address = payload["user_address"]

            except Exception as e:
                print(f"Server Error1: {e}")
                self.__send_state_res(
                    conn, room_name, operation, self.ERROR_RESPONSE, ""
                )

            try:
                token = self.handle_room(
                    room_name, user_address, user_name, operation
                )

                self.__send_state_res(
                    conn, room_name, operation, self.REQUEST_COMPLETION, token
                )
            except Exception as e:
                print(f"Server Error2:{e}")
                self.__send_state_res(conn, room_name, operation, self.SERVER_INIT, "")

    def __generate_token(self):
        """トークンを生成する
        
        :return: トークン
        """
        return secrets.token_hex(32)

    def handle_room(self, room_name, user_address, user_name, operation):
        """チャットルームを作成またはチャットルームに参加
        
        :param room_name: チャットルーム名
        :param user_address: クライアントアドレス(IPアドレス&ポート番号)
        :param user_name: ユーザー名
        :param operation: アクション番号(1:チャットルーム作成, 2:チャットルームに参加)
        :return: トークン
        """

        token = self.__generate_token()

        # チャットルームを新規作成の場合
        if operation == self.CREATE_ROOM:
            # チャットルームの存在確認
            if room_name in self.rooms:
                raise KeyError(f"{room_name} already exists")
            else:
                room = chat_room.ChatRoom(room_name)
                self.rooms[room_name] = room
                print(f"{user_name}が{room_name}を作成しました")
                room.host_token = token
        # チャットルームに参加の場合
        elif operation == self.JOIN_ROOM:
            if room_name not in self.rooms:
                raise KeyError(f"{room_name} not found")
            else:
                room = self.rooms[room_name]

        if room.add_user(token, user_address, user_name):
            print(f"{user_name}が{room_name}に参加しました")
            return token
    
    def __send_state_res(self, conn, room_name, operation, state, token):
        """リクエストに応じてヘッダーとペイロードを送信
        
        :param conn: ソケットオブジェクト
        :param room_name: チャットルーム名
        :param operation: アクション番号
        :param state: 操作コード(0:サーバー初期化, 1:リクエストの応答, 2:リクエストの完了)
        :param token: トークン
        """
        if state == self.SERVER_INIT:
            payload_data = (
                {"status": 400, "message": "部屋 {} はすでに存在します".format(room_name)}
                if operation == 1
                else {"status": 400, "message": "部屋 {} は存在しません".format(room_name)}
            )
        elif state == self.REQUEST_OF_RESPPONSE:
            payload_data = {"status": 200, "message": "リクエストを受理しました。"}
        elif state == self.ERROR_RESPONSE:
            payload_data = {
                "status": 500,
                "message": "リクエストを完了できませんでした。\n入力し直してください。",
            }
        else:
            payload_data = {"status": 202, "message": "リクエストを完了しました。", "token": token}

        res_payload = json.dumps(payload_data).encode("utf-8")

        header = struct.pack(
            "!B B B 29s",
            len(room_name),
            operation,
            state,
            len(res_payload).to_bytes(29, byteorder="big"),
        )

        conn.sendall(header + res_payload)

    def __handle_udp_conn(self):
        """UDP接続を処理する"""
        HEADER_BYTE_SIZE = 2

        while True:
            data, _ = self.udp_socket.recvfrom(4096)

            room_name_size, token_size = struct.unpack_from("!B B", data[:HEADER_BYTE_SIZE])
            room_name = data[HEADER_BYTE_SIZE:HEADER_BYTE_SIZE + room_name_size].decode("utf-8")
            token = data[
                HEADER_BYTE_SIZE + room_name_size : HEADER_BYTE_SIZE + room_name_size + token_size
            ].decode("utf-8")
            message = data[HEADER_BYTE_SIZE + room_name_size + token_size:]

            threading.Thread(
                target=self.handle_message, args=(message, room_name, token)
            ).start()

    def handle_message(self, message, room_name, token):
        """メッセージを処理する関数

        :param message: 送信メッセージ(byte)
        :param room_name: チャットルーム名
        :param token: トークン
        """
        room = self.rooms[room_name]
        sender_name = room.token_to_user_name[token]

        if message == b"exit":
            if token == room.host_token:
                message = f"{sender_name}が{room_name}から退出しました\nホストが退出したため、チャットルーム:{room_name}を終了します"
                self.__send_message(room, token, message)
                room.remove_all_users()
                del self.rooms[room_name]
            else:
                message = f"{sender_name}が{room_name}から退出しました"
                self.__send_message(room, token, message)
                room.remove_user(token)
            print(message)
        else:
            print(f"{room_name}: {sender_name}が'{message.decode('utf-8')}'を送信しました")
            decode_message = message.decode('utf-8')
            message = f"{sender_name}: {decode_message}"
            self.__send_message(room, token, message)

    def __send_message(self, room, token, message):
        """同じ部屋のほかのユーザーにメッセージを送信
        
        :param romm: チャットルーム
        :param token: トークン
        :param message: 送信メッセージ
        """
        for token_key, user_address in room.token_to_addrs.items():
            if token != token_key:
                self.udp_socket.sendto(message.encode("utf-8"), tuple(user_address))

if __name__ == "__main__":
    try:
        server = Server()
        server.start()
    except KeyboardInterrupt:
        server.tcp_socket.close()
        server.udp_socket.close()
        print("\nServer closed")
