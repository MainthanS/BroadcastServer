import asyncio


class Client:
    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self.id = writer._transport._sock_fd

    async def read_message(self):
        return await self._reader.readline()

    async def write_message(self, message):
        self._writer.write(message)
        await self._writer.drain()

    async def close(self):
        self._writer.close()
        await self._writer.wait_closed()


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


        print(f"Client {writer._transport._sock_fd} disconnected")
        self.clients.remove((reader, writer))
        writer.close()
        await writer.wait_closed()
        # ConnectionResetError: Connection lost is the error if you try to write to a closed writer

    # TODO: A Server.close() coroutine? Then can make Server an async context manager too


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
