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
        self.clients = []
        self.host = host
        self.port = port
        self.background_tasks = set()

    async def start_server(self):
        self._server = await asyncio.start_server(
            self.client_connected_cb, self.host, self.port)

        async with self._server:
            await self._server.serve_forever()

    def client_connected_cb(self, reader, writer):
        client = Client(reader, writer)
        self.clients.append(client)
        task = asyncio.create_task(
            self.client_messages_server(client))
        self.background_tasks.add(task)
        print(f"Registered callback for client {client.id}")

    async def client_messages_server(self, client):
        message = await client.read_message()
        while message:
            print(f"User {client.id}: {message}")
            # Possible race condition?
            for client_ in self.clients:
                print(f"Broadcasting to {client_.id}")
                task = asyncio.create_task(client_.write_message(message))
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
                # TODO: Add timeout and close writer if it takes too long
            message = await client.read_message()

        print(f"User {client.id} disconnected")
        self.clients.remove(client)
        await client.close()
        # ConnectionResetError: Connection lost is the error if you try to write to a closed writer

    # TODO: A Server.close() coroutine? Then can make Server an async context manager too


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
