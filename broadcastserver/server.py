import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


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
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.debug("Failed to write to client %d: %s", self.id, e)
            await self.close()
            raise ClientDisconnectedError(client_id=self.id) from e

    async def close(self):
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except BrokenPipeError as e:
            logger.debug("Failed to close client %d: %s", self.id, e)
            raise ClientDisconnectedError(client_id=self.id) from e


class Server:
    def __init__(self, host="localhost", port=40004):
        self.clients = [] # Not needed now?
        self.host = host
        self.port = port
        self._client_mapping = dict()
        self._task_mapping = dict()
        self.background_tasks = set()

    async def start_server(self):
        self._server = await asyncio.start_server(
            self.client_connected_cb, self.host, self.port)

        async with self._server:
            logger.info("Listening on %s:%d", self.host, self.port)
            await self._server.serve_forever()

    # TODO Needs cleaning up
    def client_connected_cb(self, reader, writer):
        client = Client(reader, writer)
        logger.info("Client %d connected", client.id)
        self._client_mapping[client.id] = client
        logger.debug("Updated dict _client_mapping with client id %d", client.id)
        client_task = asyncio.create_task(
            self.client_handler(client))
        client_task.set_name(f"Client-Handler-{client.id}")
        logger.debug("Created task %s", client_task.get_name())
        self._task_mapping.update({client.id: client_task})
        logger.debug("Updated dict _task_mapping with client id %d", client.id)

    def _cleanup_client_handler_mappings(self, client_id):
        logger.debug("Cleaning up after %s finished", task.get_name()) 

        del self._task_mapping[client_id]
        logger.debug("Deleted client id %d from dict _task_mapping", client_id)

        del self._client_mapping[client_id]
        logger.debug("Deleted client id %d from dict _client_mapping", client_id)

    def _cleanup_message_handler(self, task):
        logger.debug("Cleaning up task %s", task.get_name())
        self.background_tasks.discard(task)

        exc = task.exception()
        if (exc is not None) and isinstance(exc, ClientDisconnectedError):
            try:
                client_task = self._task_mapping[exc.client_id]
                logger.debug(
                    "Cancelling task %s since ClientDisconnectedError was raised",
                    client_task.get_name(),
                )
                client_task.cancel()

            # The Client-Handler task may have already been cancelled and
            # cleaned itself up if another Message-Handler raised this
            # exception for the same client id
            except KeyError:
                pass

    async def message_handler(self, recipient, message):
        try:
            logger.debug(
                "Sending message to client %d", recipient.id)
            await recipient.write_message(message)

        except asyncio.CancelledError as e:
            current_task = asyncio.current_task()
            logger.debug("Cancelling task %s", current_task.get_name()) 
            raise

    async def client_handler(self, client):
        try:
            message = await client.read_message()
            while message:
                logger.debug(
                    "Message received from client %d: %s",
                    client.id,
                    message.decode().rstrip(),
                ) 

                for _, recipient_client in self._client_mapping.items():
                    message_task = asyncio.create_task(
                        self.message_handler(recipient_client, message))

                    message_task.set_name(f"Message-Handler-{uuid.uuid4()}")
                    logger.debug("Created task %s", message_task.get_name())

                    self.background_tasks.add(message_task)
                    message_task.add_done_callback(
                        self._cleanup_message_handler)

                    # TODO: Add timeout and close writer if it takes too long
                message = await client.read_message()

        except asyncio.CancelledError as e:
            current_task = asyncio.current_task()
            logger.debug("Cancelling task %s", current_task.get_name()) 
            raise

        finally:
            logger.info("Client %d disconnected", client.id)
            self._cleanup_client_handler_mappings(client.id)
            await client.close()

    # TODO: A Server.close() coroutine? Then can make Server an async context manager too


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
    asyncio.run(server.start_server())
    # TODO: Server should shutdown if Tasks hit certain exceptions
