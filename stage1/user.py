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
        time_defference = datetime.now() - self.last_visited_time
        return time_defference.seconds <= timeout_seconds