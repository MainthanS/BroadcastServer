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
            print(writer._transport._sock_fd, message)
            for _, writer_ in self.clients:
                # Shouldn't iterate synchronously, and must remove old writers
                print("messaging", writer_._transport._sock_fd)
                writer_.write(message) # TODO: Add timeout and close writer if it takes too long
                await writer_.drain()
            message = await reader.readline()

        # ConnectionResetError: Connection lost is the error if you try to write to a closed writer

        print(f"Client {writer._transport._sock_fd} disconnected")
        # TODO close writer
        self.clients.remove((reader, writer))


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
