import asyncio


class Server:
    def __init__(self, host="localhost", port=40004):
        self.clients = []  # Can this be a set or a dict?
        self.host = host
        self.port = port
        self.background_tasks = set()

    async def start_server(self):
        self._server = await asyncio.start_server(
            self.client_connected_cb, self.host, self.port)

        async with self._server:
            await self._server.serve_forever()

    def client_connected_cb(self, reader, writer):
        self.clients.append((reader, writer))
        task = asyncio.create_task(
            self.client_messages_server(reader, writer))
        self.background_tasks.add(task)
        print("Registered task")

    async def client_messages_server(self, reader, writer):

        message = await reader.readline()
        while message:
            print(message)
            message = await reader.readline()

        # TODO: Deregister client

        # print(message)
        # if not message:
        #     # TODO: Deregister client
        #     pass


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
