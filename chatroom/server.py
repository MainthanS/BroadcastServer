import asyncio

class Server:
    def __init__(self, hostname="localhost", port=40004):
        self.clients = []
        self.hostname = hostname
        self.port = port

    async def start(self):
        await asyncio.start_server(self.callback, self.hostname, self.port)
        while True:
            await asyncio.sleep(1)

    def callback(self, reader, writer):
        print("Hello world!")

if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start())
