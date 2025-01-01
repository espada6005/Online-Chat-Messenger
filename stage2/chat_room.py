import secrets

class ChatRoom:

    def __init__(self, room_name):
        self.name = room_name
        self.host_token = ""
        self.users = {}
        self.token_to_addrs = {}
        self.token_to_user_name = {}
        self.messages = []

    def generate_token(self):
        """トークンを生成する
        
        :return: トークン
        """
        return secrets.token_hex(16)
    
    def add_user(self, token, user_address, user_name):
        """チャットルームにユーザー追加
        
        :return: 成否
        """
        MAX_USERS = 1000
        if len(self.token_to_addrs) <= MAX_USERS:
            self.token_to_addrs[token] = user_address
            self.token_to_user_name[token] = user_name
            return True
        else:
            print(f"{self.name} is full")
            return False

    def remove_user(self, token):
        """チャットルームからユーザー削除
        
        :return: 成否
        """
        if token in self.token_to_addrs:
            del self.token_to_addrs[token]
            del self.token_to_user_name[token]

    def remove_all_users(self):
        """全ユーザーチャットルームから削除(ホスト退出)"""
        tokens_to_romove = self.token_to_addrs.copy
        for token in tokens_to_romove:
            if self.remove_user(token):
                self.users = {}
                self.token_to_addrs = {}
                self.messages = []