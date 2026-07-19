class ServerGameLogic:
    def __init__(self):
        pass

    def process_message(self, message):
        response = {"status": "processed", "message": message}
        return response