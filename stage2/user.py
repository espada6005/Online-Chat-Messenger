import socket
import struct
import threading

class User:
    TIMEOUT = 300

    def __init__(self, user_name):
        self.RANDOM_PORT = 0
        self.udp_server_address = ("127.0.0.1", 9003)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("127.0.0.1", self.RANDOM_PORT))
        self.user_name = user_name
        self.token = ""
        self.room_name = ""
        self.is_host = False
        self.address = self.udp_socket.getsockname()
        self.timer = None
        self.CREATE_ROOM = 1
        self.JOIN_ROOM = 2
        self.QUIT = 3

    def __input_text(self, description):
        """入力を受け付ける
        
        :param description: 説明
        :return text: 入力内容
        """
        while True:
            text = input(description)
            if text == "":
                continue
            return text
        
    def get_action_number(self):
        """アクションを受け付ける
        
        :return operation: 入力番号
        """
        while True:
            try:
                print("Please enter 1 or 2 or 3")
                description = "1. Create a new room\n2. Join an existing room\n3. Quit\nChoose an option: "
                operation = self.__input_text(description)
                if int(operation) in [
                    self.CREATE_ROOM,
                    self.JOIN_ROOM,
                    self.QUIT,
                ]:
                    return operation
            except Exception:
                continue

    def get_room_name(self):
        """部屋名の入力

        :return room_name: チャットルーム名
        """
        ROOM_NAME_MAX_BYTE_SIZE = 255
        while True:
            input_description = "Enter room name: "
            self.room_name = self.__input_text(input_description)
            room_name_size = len(self.room_name.encode("utf-8"))
            if room_name_size > ROOM_NAME_MAX_BYTE_SIZE:
                print(f"Room name bytes: {room_name_size} is too large.")
                print(
                    f"Please retype the room name with less than {ROOM_NAME_MAX_BYTE_SIZE} bytes"
                )
                continue
            return self.room_name
        
    def __generate_request(self, message):
        """リクエスト情報の生成

        :param message: メッセージ
        :return request: リクエスト情報
        """
        header = struct.pack(
            "!B B",
            len(self.room_name.encode("utf-8")),
            len(self.token.encode("utf-8")),
        )
        body = self.room_name + self.token + message
        encoded_body = body.encode("utf-8")
        request_info = header + encoded_body
        return request_info

    def send_message(self):
        """メッセージの送信"""

        while True:
            # メッセージの入力
            input_message = self.__input_text("")
            self.__reset_timer()
            request_info = self.__generate_request(input_message)
            # メッセージを送信
            # Todo メッセージのバイトサイズを超えた際の例外処理
            self.udp_socket.sendto(request_info, self.udp_server_address)
            if "exit" == input_message:
                self.udp_socket.close()
                exit()

    def receive_message(self):
        """メッセージの受信"""
        while True:
            # メッセージを受信
            data, _ = self.udp_socket.recvfrom(4096)
            decoded_data = data.decode("utf-8")
            print(decoded_data)
            if (
                f"ホストが退出したため、チャットルーム:{self.room_name}を終了します。" in decoded_data
                or decoded_data == f"{self.user_name}が{self.room_name}から退出しました。"
            ):
                print("UDPソケットを閉じる")
                self.__cancel_timer()
                self.udp_socket.close()
                exit()

    def __reset_timer(self):
        """タイムアウトのカウントをリセットする"""
        self.start_timer()

    def start_timer(self):
        """タイマーを開始または再開する"""
        if self.timer:
            # 既存のタイマーがあればキャンセル
            self.timer.cancel()
        self.timer = threading.Timer(User.TIMEOUT, self.__timeout)
        self.timer.start()

    def __timeout(self):
        """指定した時間が経過したときに実行される"""
        print("Timed out!")
        request_info = self.__generate_request("exit")

        # メッセージを送信
        # Todo メッセージのバイトサイズを超えた際の例外処理
        self.udp_socket.sendto(request_info, self.udp_server_address)
        self.udp_socket.close()
        exit()

    def __cancel_timer(self):
        """タイマーを止める"""
        self.timer.cancel()
