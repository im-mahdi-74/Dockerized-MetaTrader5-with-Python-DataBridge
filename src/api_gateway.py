# api_gateway.py

import os
import sys
import json
import logging
import functools
import hmac
from datetime import datetime
from typing import Any, Callable, Tuple, List

import pandas as pd
import MetaTrader5 as mt5
from flask import Flask, request, jsonify, Response
from waitress import serve

# Initial settings from environment variables
MT5_ACCOUNT: int = int(os.environ.get("MT5_ACCOUNT", 0))
MT5_PASSWORD: str = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER: str = os.environ.get("MT5_SERVER", "")
MT5_PATH: str = os.environ.get("MT5_PATH", r"C:\Program Files\meta\terminal64.exe")
API_KEY: str = os.environ.get("API_KEY", "")

# List of allowed functions for RPC calls
ALLOWED_FUNCTIONS: List[str] = [
    'account_info', 'terminal_info', 'version', 'positions_get', 'positions_total', 
    'orders_get', 'orders_total', 'history_orders_get', 'history_orders_total', 
    'history_deals_get', 'history_deals_total', 'order_send', 'order_check', 
    'symbol_info', 'symbol_info_tick', 'symbol_select', 'symbols_get', 
    'symbols_total', 'copy_rates_from', 'copy_rates_from_pos', 'copy_rates_range', 
    'copy_ticks_from', 'copy_ticks_range', 'market_book_add', 'market_book_release', 
    'market_book_get', 'last_error'
]

# Setting up the logging system
log_formatter = logging.Formatter('%(asctime)s - API_GATEWAY - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

# Initializing the Flask web server
app = Flask(__name__)


def custom_json_encoder(obj: Any) -> Any:
    """
    Convert various data types to JSON serializable formats.
    
    Args:
        obj: The object to be serialized.
        
    Returns:
        A JSON serializable representation of the object.
        
    Raises:
        TypeError: If the object cannot be serialized.
    """
    if hasattr(obj, '_asdict'):
        return obj._asdict()
    
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')

    if isinstance(obj, datetime):
        return obj.isoformat()

    if hasattr(obj, '__dict__'):
        return obj.__dict__
        
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def require_api_key(f: Callable) -> Callable:
    """
    Decorator to verify the API Key in the request header.
    
    Args:
        f: The function to be decorated.
        
    Returns:
        The decorated function.
    """
    @functools.wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if 'X-API-KEY' in request.headers and hmac.compare_digest(request.headers['X-API-KEY'], API_KEY):
            return f(*args, **kwargs)
        else:
            logger.warning("Unauthorized access attempt detected.")
            return jsonify({"status": "error", "message": "Unauthorized: API Key is missing or invalid"}), 401
    return decorated_function


@app.route('/health')
def health_check() -> Tuple[Response, int]:
    """
    Check the health and connection status of the MT5 terminal.
    
    Returns:
        JSON response with the status and HTTP status code.
    """
    if mt5.terminal_info():
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error", "message": "MT5 connection is not active"}), 503


@app.route('/rpc', methods=['POST'])
@require_api_key
def rpc_handler() -> Tuple[Response, int]:
    """
    Handle incoming RPC requests to execute allowed MetaTrader 5 functions.
    
    Returns:
        JSON response containing the execution result or error, and HTTP status code.
    """
    try:
        req_data = request.get_json()
        function_name = req_data.get('function_name')
        args = req_data.get('args', [])
        kwargs = req_data.get('kwargs', {})
    except Exception as e:
        logger.error(f"Invalid JSON request: {e}")
        return jsonify({"status": "error", "message": f"Invalid JSON request: {e}"}), 400

    logger.info(f"Received RPC call for function: '{function_name}'")

    if function_name not in ALLOWED_FUNCTIONS:
        logger.warning(f"Attempt to call disallowed function: {function_name}")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": "This function is not allowed via RPC."
        }), 403

    try:
        mt5_function = getattr(mt5, function_name)
        result = mt5_function(*args, **kwargs)

        final_result = result
        if hasattr(result, '_asdict'):
            final_result = result._asdict()
        elif isinstance(result, (list, tuple)):
            final_result = [item._asdict() if hasattr(item, '_asdict') else item for item in result]

        json_result = json.loads(json.dumps(final_result, default=custom_json_encoder))

        logger.info(f"Successfully executed '{function_name}'.")
        return jsonify({
            "status": "success",
            "function_name": function_name,
            "data": json_result
        }), 200

    except AttributeError:
        logger.error(f"Function '{function_name}' not found in MetaTrader5 library.")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": f"Function '{function_name}' not found in MetaTrader5 library."
        }), 404
    except Exception as e:
        last_error = mt5.last_error()
        logger.error(f"An error occurred while executing '{function_name}': {e}. MT5 Last Error: {last_error}")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": str(e),
            "mt5_last_error": str(last_error)
        }), 500


if __name__ == "__main__":
    logger.info("API Gateway starting up...")

    if not API_KEY:
        logger.critical("CRITICAL: API_KEY environment variable is not set. Exiting.")
        sys.exit(1)
    
    if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.critical(f"MT5 initialize() failed, error code: {mt5.last_error()}. Exiting.")
        mt5.shutdown()
        sys.exit(1)
    
    logger.info(f"Successfully connected to MT5 account {MT5_ACCOUNT}.")
    logger.info("API Gateway is running. Waiting for HTTP requests on port 8080...")
    
    try:
        serve(app, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        logger.info("API Gateway stopped by user.")
    finally:
        logger.info("Shutting down MT5 connection.")
        mt5.shutdown()