class PyarconlineException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__name__}({self.args[0]!r})"


class FriendcodeError(PyarconlineException):
    def __init__(self, friend_code):
        self.friend_code = friend_code
        super().__init__(f'Friendcode {friend_code} is not valid')

    def __repr__(self):
        return f"{self.__class__.__name__}(friend_code={self.friend_code})"


class ApiException(PyarconlineException):
    def __init__(self, response):
        self.response = response
        super().__init__(f'API called failed with message: {response}')

    def __repr__(self):
        return f"{self.__class__.__name__}(response={self.response})"


class FriendNotFoundError(PyarconlineException):

    def __init__(self, idlike):
        self.friend_id = idlike
        super().__init__(f'Friend {idlike} is not in your friend list! You should add_friend first.')

    def __repr__(self):
        return f"{self.__class__.__name__}(friend_id={self.friend_id})"


class SongNotFoundError(PyarconlineException):
    def __init__(self, song_id):
        self.id = song_id
        super().__init__(f'Song with identifier {song_id} does not exist!')

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class NotloggedError(PyarconlineException):
    def __init__(self):
        super().__init__('You are not logged in yet!')

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class LoginError(PyarconlineException):
    def __init__(self):
        super().__init__('Login failed! Please check your username and password!')

    def __repr__(self):
        return f"{self.__class__.__name__}()"
