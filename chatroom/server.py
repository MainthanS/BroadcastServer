import asyncio

class Server:
    def __init__(self, host="localhost", port=40004):
        self.clients = []
        self.host = host
        self.port = port

    async def start_server(self):
        await asyncio.start_server(
            self.client_connected_cb, self.host, self.port)

        while True:
            await asyncio.sleep(1)

    def client_connected_cb(self, reader, writer):
        print("Hello world!")

if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
