import asyncio


class ClientDisconnectedError(Exception):
    """Exception raised when attempting to write to a disconnected client."""
    def __init__(self, client_id):
        super().__init__(f"ClientDisconnectedError with {client_id=}")
        self.client_id = client_id


class Client:
    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self.id = writer._transport._sock_fd

    async def read_message(self):
        return await self._reader.readline()

    async def write_message(self, message):
        try:
            self._writer.write(message)
            await self._writer.drain()
        except ConnectionResetError as e:
            # TODO: Client must be removed from Server.clients too
            await self.close()
            raise ClientDisconnectedError(client_id=self.id) from e

    async def close(self):
        self._writer.close()
        await self._writer.wait_closed()


class Server:
    def __init__(self, host="localhost", port=40004):
        self.clients = []
        self.host = host
        self.port = port
        self.background_tasks = set()
        #self.background_tasks = dict()

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
        #self.background_tasks.update({client.id: task})
        task.add_done_callback(self.background_tasks.discard)
        #task.add_done_callback(
        #    lambda x: self.background_tasks.pop(client.id))
        print(f"Registered callback for client {client.id}")

    # TODO: cleanup
    def client_exception_cb(self, task):
        if (exc := task.exception()) is not None:
            if isinstance(exc, ClientDisconnectedError):
                print(exc)
                print(f"Deleting client {exc.client_id} from client list")
            else:
                print(exc)
                print("Some other exception")


    async def client_messages_server(self, client):
        message = await client.read_message()
        while message:
            print(f"User {client.id}: {message}")
            for client_ in self.clients:
                print(f"Broadcasting to {client_.id}")
                task = asyncio.create_task(client_.write_message(message))
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
                task.add_done_callback(self.client_exception_cb)
                # TODO: Add timeout and close writer if it takes too long
            message = await client.read_message()

        print(f"User {client.id} disconnected")
        # XXX tmp debugging
        #self.clients.remove(client)
        await client.close()

    # TODO: A Server.close() coroutine? Then can make Server an async context manager too


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
