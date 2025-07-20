import argparse
import asyncio
import logging

import broadcastserver.server

async def main(**kwargs):
    async with broadcastserver.server.Server(**kwargs) as server:
        await server.start_server()
        await server.serve_forever()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="broadcastserver.run_server")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=40004)
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    logging.basicConfig(level=logging_level)

    asyncio.run(main(host=args.host, port=args.port))
