#
# WebSocket Hub/Router (Professional Version)
# This server acts as a central hub to receive data from MT5 streamers
# and broadcast it to any connected viewers.
#
import asyncio
import websockets
import json
import logging
from websockets.server import WebSocketServerProtocol

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# A dictionary to hold the data producers (the MT5 streamer bots)
# Structure: { account_id: websocket_connection }
STREAMERS = {}

# A set to hold the data consumers (dashboards, viewers, etc.)
VIEWERS = set()

async def handle_streamer(websocket: WebSocketServerProtocol, account_id: int | str) -> None:
    """
    Manages the logic for a connected Streamer.
    It forwards any message received from this client to all viewers.
    """
    logging.info(f"Streamer for account {account_id} is now live.")
    try:
        async for message in websocket:
            # Broadcast the message only if there are viewers
            if VIEWERS:
                websockets.broadcast(VIEWERS, message)
    finally:
        # When the streamer disconnects, remove it from the dictionary
        logging.info(f"Streamer for account {account_id} disconnected.")
        if account_id in STREAMERS:
            del STREAMERS[account_id]

async def handle_viewer(websocket: WebSocketServerProtocol) -> None:
    """
    Manages the logic for a connected Viewer.
    Its main job is to keep the connection alive to receive messages.
    """
    logging.info(f"Viewer connected from {websocket.remote_address[0]}.")
    try:
        # We just wait until the viewer's connection is closed.
        # Viewers are typically listeners and don't send messages.
        await websocket.wait_closed()
    finally:
        # When the viewer disconnects, remove it from the set
        logging.info(f"Viewer disconnected from {websocket.remote_address[0]}.")
        VIEWERS.remove(websocket)

async def main_handler(websocket: WebSocketServerProtocol) -> None:
    """
    The main handler that runs for each new connection.
    It identifies the client's role and routes it to the appropriate handler.
    """
    client_info = None # To store client identity for cleanup
    logging.info(f"New connection attempt from: {websocket.remote_address[0]}")
    try:
        # Wait for the initial identification message
        initial_message = await websocket.recv()
        data = json.loads(initial_message)
        client_type = data.get("type")

        if client_type == "streamer_hello":
            account_id = data.get("account_number")
            if account_id is None:
                await websocket.close(1008, "Account number is required for streamers.")
                return
            
            client_info = ("streamer", account_id)
            
            # If an account is already connected, close the old connection
            if account_id in STREAMERS:
                 logging.warning(f"Closing existing connection for account {account_id}.")
                 await STREAMERS[account_id].close(1012, "New connection established.")

            STREAMERS[account_id] = websocket
            await handle_streamer(websocket, account_id)

        elif client_type == "viewer_hello":
            client_info = ("viewer", websocket)
            VIEWERS.add(websocket)
            await handle_viewer(websocket)

        else:
            logging.warning(f"Unknown client type: '{client_type}'. Closing connection.")
            await websocket.close(1008, "Unknown client type")

    except json.JSONDecodeError:
        logging.error("Invalid JSON in initial message. Closing connection.")
        await websocket.close(1008, "Invalid JSON format")
    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
        logging.info(f"Connection from {websocket.remote_address[0]} closed before registration.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in main_handler: {e}")
        await websocket.close(1011, "Internal server error")
    finally:
        # Proper cleanup after disconnection
        if client_info:
            role, identity = client_info
            if role == "streamer" and identity in STREAMERS and STREAMERS[identity] == websocket:
                del STREAMERS[identity]
                logging.info(f"Cleaned up streamer for account {identity}.")
            elif role == "viewer" and identity in VIEWERS:
                VIEWERS.remove(identity)
                logging.info(f"Cleaned up viewer from {websocket.remote_address[0]}.")


async def main() -> None:
    """
    The main function to start the server.
    """
    host = "0.0.0.0"
    port = 8765

    async with websockets.serve(main_handler, host, port):
        logging.info(f"🚀 Professional WebSocket Hub started on ws://{host}:{port}")
        await asyncio.Future()  # Keep the server running forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server is shutting down.")