import socket
import json
import struct
import threading

from user import User


class Client:
    def __init__(self):
        self.tcp_address = ("127.0.0.1", 9002)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # クライアントが入力したアクション番号
        self.CREATE_ROOM = 1
        self.JOIN_ROOM = 2
        # state
        self.SERVER_INIT = 0
        self.REQUEST_COMPLETION = 2

    def start(self):
        """クライアントを起動する"""
        # ユーザー名入力
        user_name = self.__get_user_name()
        user = User(user_name)

        user.token = None
        while user.token is None:
            operation = user.get_action_number()
            # TCP接続するかどうか
            tcp_connected = self.__check_tcp_connection(int(operation))
            if not tcp_connected:
                print("Closing connection...")
                self.tcp_socket.close()
                print("Connection closed.")
                exit()

            # 部屋名を入力
            room_name = user.get_room_name()
            # 入室リクエストを送信
            self.__request_to_join_room(operation, user, room_name)
            # 入室リクエストのレスポンスを受け取る
            token = self.__receive_response_to_join_room()

            if token is not None:
                user.token = token
                # 参加した部屋名をセット
                user.room_name = room_name
                break

        # TCP接続を閉じる
        self.tcp_socket.close()

        # 部屋に参加してからタイマースタート
        user.start_timer()
        # 他クライアントからのメッセージを別スレッドで受信
        threading.Thread(target=user.receive_message).start()
        # メッセージを送信
        threading.Thread(target=user.send_message).start()

    def __get_user_name(self):
        """ユーザー名入力

        :return: ユーザー名
        """
        USER_NAME_MAX_BYTE_SIZE = 255
        while True:
            user_name = input("Enter your username: ")
            if user_name == "":
                continue
            user_name_size = len(user_name.encode("utf-8"))
            if user_name_size > USER_NAME_MAX_BYTE_SIZE:
                print(f"User name bytes: {user_name_size} is too large.")
                print(
                    f"Please retype the room name with less than {USER_NAME_MAX_BYTE_SIZE} bytes"
                )
                continue
            return user_name

    def __check_tcp_connection(self, operation):
        """TCP接続の確認
        
        :param operation: クライアントが入力したアクション番号(1:部屋作成, 2:参加, 3:終了)

        :return tcp_connected: TCP接続成否
        """
        tcp_connected = False
        if operation == self.CREATE_ROOM or operation == self.JOIN_ROOM:
            self.tcp_socket.connect(self.tcp_address)
            tcp_connected = True

        return tcp_connected

    def __request_to_join_room(self, operation, user, room_name):
        """部屋入室リクエストの関数(部屋作成・部屋参加共通)

        :param operation: クライアントが入力したアクション番号(1:部屋作成, 2:参加)
        :param user(インスタンス): ユーザー
        :param room_name: チャットルーム名
        """

        encoded_room_name = room_name.encode("utf-8")
        payload = {
            "user_name": user.user_name,
            "user_address": user.address,
        }
        payload_data = json.dumps(payload).encode("utf-8")
        # ヘッダーを作成
        header = struct.pack(
            "!B B B 29s",
            len(encoded_room_name),
            int(operation),
            self.SERVER_INIT,
            len(payload_data).to_bytes(29, byteorder="big"),
        )
        # ボディを作成
        # Todo OperationPayloadSizeの最大バイト数を超えた場合の例外処理
        body = encoded_room_name + payload_data

        # ヘッダーとボディをサーバーに送信
        req = header + body
        self.tcp_socket.sendall(req)

    def __receive_response_to_join_room(self):
        """部屋入室リクエストのレスポンスを受け取る

        return : トークン
        """
        header = self.tcp_socket.recv(32)
        _, _, state, payload_size = struct.unpack_from("!B B B 29s", header)
        operation_payload_size = int.from_bytes(payload_size, byteorder="big")
        payload = self.tcp_socket.recv(operation_payload_size)

        if state == self.SERVER_INIT:
            print(json.loads(payload.decode("utf-8"))["message"])
            self.tcp_socket.close()
            self.__init__()
            return None
        elif state == self.REQUEST_COMPLETION:
            # トークンを取得
            token = json.loads(payload.decode("utf-8"))["token"]
            message = json.loads(payload.decode("utf-8"))["message"]
            print(message)
            return token


if __name__ == "__main__":
    print("---WELCOME TO THE CHAT MESSENGER PROGRAM!---")
    client = Client()
    client.start()
