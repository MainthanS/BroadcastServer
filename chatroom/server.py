import asyncio

class Server:
    def __init__(self, host="localhost", port=40004):
        self.clients = [] # can this be a set or a dict?
        self.host = host
        self.port = port

    async def start_server(self):
        await asyncio.start_server(
            self.client_connected_cb, self.host, self.port)

        while True:
            for reader, writer in self.clients:
                message = await reader.readline()
                print(message)
                if not message:
                    self.clients.remove((reader, writer))
                # Why does this keep printing even after I exit netcat?
                # Oh.. no logic to remover them from self.clients after they disconnect...
            await asyncio.sleep(1)

    def client_connected_cb(self, reader, writer):
        self.clients.append((reader, writer))

if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
