# streamer.py
import os
import time
import asyncio
import json
import logging
import sys
import MetaTrader5 as mt5
import websockets

# Initial configurations
MT5_ACCOUNT = int(os.environ.get("MT5_ACCOUNT", 0))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER = os.environ.get("MT5_SERVER", "")
MT5_PATH = os.environ.get("MT5_PATH", r"C:\Program Files\meta\terminal64.exe")
WEBSOCKET_URI = os.environ.get("WEBSOCKET_URI", "ws://localhost:8765")
SEND_INTERVAL_SECONDS = 1
RECONNECT_DELAY_SECONDS = 10

# Logging setup
log_formatter = logging.Formatter('%(asctime)s - STREAMER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

def initialize_mt5() -> bool:
    """
    Initialize connection to MetaTrader 5 terminal.
    
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    logger.info("Attempting to initialize MetaTrader 5...")
    if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.error(f"MT5 initialize() failed, error code: {mt5.last_error()}")
        mt5.shutdown()
        return False
    logger.info(f"Successfully initialized MT5 for account {MT5_ACCOUNT}")
    return True

def get_realtime_data() -> dict | None:
    """
    Retrieve real-time account and position data from MetaTrader 5.
    
    Returns:
        dict | None: A dictionary containing account and position data, or None if retrieval fails.
    """
    try:
        account_info = mt5.account_info()
        if not account_info:
            logger.warning("Could not get account info.")
            return None

        positions = mt5.positions_get()
        open_trades = []
        if positions is not None:
            open_trades = [
                {"ticket": p.ticket, "symbol": p.symbol, "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                 "volume": p.volume, "price_open": p.price_open, "price_current": p.price_current,
                 "profit": p.profit, "swap": p.swap, "time_open": p.time} for p in positions
            ]

        data = {
            "type": "account_update", "account_number": account_info.login, "timestamp": int(time.time()),
            "data": {
                "balance": account_info.balance, "equity": account_info.equity, "profit": account_info.profit,
                "margin": account_info.margin, "margin_free": account_info.margin_free,
                "margin_level": account_info.margin_level, "open_trades_count": len(open_trades),
                "open_trades": open_trades
            }
        }
        return data
    except Exception as e:
        logger.error(f"Exception in get_realtime_data: {e}")
        return None

async def stream_data_handler() -> None:
    """
    Connect to the WebSocket server and continuously stream data from MetaTrader 5.
    """
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URI) as websocket:
                logger.info(f"Connected to WebSocket server: {WEBSOCKET_URI}")
                
                # Introduce as streamer
                await websocket.send(json.dumps({
                    "type": "streamer_hello",
                    "account_number": MT5_ACCOUNT
                }))

                while True:
                    realtime_data = get_realtime_data()
                    if realtime_data:
                        await websocket.send(json.dumps(realtime_data))
                        logger.debug(f"Sent update for account {MT5_ACCOUNT}")
                    await asyncio.sleep(SEND_INTERVAL_SECONDS)
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"WebSocket connection lost: {e}. Reconnecting in {RECONNECT_DELAY_SECONDS} seconds...")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. Reconnecting...")
        
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)

if __name__ == "__main__":
    logger.info("Streamer bot starting up...")
    time.sleep(5)  # Initial delay

    if not all([MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER]):
        logger.critical("CRITICAL: MT5 environment variables not set. Exiting.")
        sys.exit(1)

    if initialize_mt5():
        try:
            asyncio.run(stream_data_handler())
        except KeyboardInterrupt:
            logger.info("Streamer bot stopped by user.")
        finally:
            logger.info("Shutting down MT5 connection.")
            mt5.shutdown()
    else:
        logger.critical("Could not initialize MT5. Streamer bot will not start.")
        sys.exit(1)