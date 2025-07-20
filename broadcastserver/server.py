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
    """Represents a client connected to the broadcast server.

    Wrapper around asyncio.StreamReader and asyncio.StreamWriter."""


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
    """Broadcast server encapsulating an asyncio.Server object.

    Initialises and runs a broadcast server while managing client
    connections and facilitating communication between them."""

    def __init__(self, host, port):
        self.host = host
        self.port = port

        # Map client.id to associated Client object and Client-Handler Task
        self.client_mapping = dict()
        self.task_mapping = dict()

        # Stores references to Message-Handler Tasks so they aren't
        # garbage collected
        self.message_tasks = set()

        self._server = None


    async def start_server(self):
        self._server = await asyncio.start_server(
            self._client_connected_callback, self.host, self.port)

    async def serve_forever(self):
        if self._server is None:
            raise RuntimeError(f"Server {self!r} is closed")
        else:
            logger.info("Listening on %s:%d", self.host, self.port)
            await self._server.serve_forever()

    def _log_exception_callback(self, task):
        exc = task.exception()
        if exc:
            logger.error("%s failed: %s", task.get_name(), exc) 

    # TODO Needs cleaning up
    def _client_connected_callback(self, reader, writer):
        client = Client(reader, writer)
        logger.info("Client %d connected", client.id)
        self.client_mapping[client.id] = client
        logger.debug("Updated dict client_mapping with client id %d", client.id)
        client_task = asyncio.create_task(
            self.client_handler(client))
        client_task.set_name(f"Client-Handler-{client.id}")
        logger.debug("Created task %s", client_task.get_name())
        self.task_mapping.update({client.id: client_task})
        logger.debug("Updated dict task_mapping with client id %d", client.id)
        client_task.add_done_callback(self._log_exception_callback)

    def _cleanup_client_handler_mappings(self, client_id):
        task = asyncio.current_task()
        logger.debug("Cleaning up after %s finished", task.get_name()) 

        del self.task_mapping[client_id]
        logger.debug("Deleted client id %d from dict task_mapping", client_id)

        del self.client_mapping[client_id]
        logger.debug("Deleted client id %d from dict client_mapping", client_id)

    def _cleanup_message_handler(self, task):
        logger.debug("Cleaning up task %s", task.get_name())
        self.message_tasks.discard(task)

        exc = task.exception()
        if (exc is not None) and isinstance(exc, ClientDisconnectedError):
            try:
                client_task = self.task_mapping[exc.client_id]
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
        """Coroutine used to create Message-Handler tasks."""

        try:
            logger.debug(
                "Sending message to client %d", recipient.id)
            await recipient.write_message(message)

        except asyncio.CancelledError as e:
            current_task = asyncio.current_task()
            logger.debug("Cancelling task %s", current_task.get_name()) 
            raise

    async def client_handler(self, client):
        """Coroutune used to create Client-Handler tasks."""

        try:
            message = await client.read_message()
            while message:
                logger.debug(
                    "Message received from client %d: %s",
                    client.id,
                    message.decode().rstrip(),
                ) 

                for _, recipient_client in self.client_mapping.items():
                    message_task = asyncio.create_task(
                        self.message_handler(recipient_client, message))

                    message_task.set_name(f"Message-Handler-{uuid.uuid4()}")
                    logger.debug("Created task %s", message_task.get_name())

                    self.message_tasks.add(message_task)
                    message_task.add_done_callback(
                        self._cleanup_message_handler)
                    message_task.add_done_callback(
                        self._log_exception_callback)

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

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        logger.info("Closing server %s", repr(self))
        if self._server:
            self._server.close()
            await self._server.wait_closed()
