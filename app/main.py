import socket
import threading
import sys
import time

from .resp import RESPDecoder, encode_simple_string, encode_error, encode_integer, encode_bulk_string, encode_array
from .store import KeyValueStore
from .pubsub import PubSubManager

# Global state
store = KeyValueStore()
pubsub = PubSubManager()

def handle_client(connection, address):
    print(f"Accepted connection from {address}", flush=True)
    decoder = RESPDecoder(connection)
    
    try:
        while True:
            payload = decoder.decode()
            if payload is None:
                break
            
            print(f"[{address}] Received: {payload}", flush=True)

            if not isinstance(payload, list):
                # We expect commands to be arrays of bulk strings
                continue
            
            if not payload or payload[0] is None:
                continue

            command = payload[0].upper()
            args = payload[1:]
            
            response = None
            
            if command == "PING":
                if args:
                    response = encode_bulk_string(args[0])
                else:
                    response = encode_simple_string("PONG")
            
            elif command == "ECHO":
                if len(args) == 1:
                    response = encode_bulk_string(args[0])
                else:
                    response = encode_error("ERR wrong number of arguments for 'echo' command")

            elif command == "SET":
                if len(args) >= 2:
                    key = args[0]
                    value = args[1]
                    px = None
                    
                    # Handle PX argument
                    if len(args) >= 4 and args[2].upper() == "PX":
                        try:
                            px = int(args[3])
                        except ValueError:
                             response = encode_error("ERR value is not an integer or out of range")
                    
                    if not response:
                        store.set(key, value, px)
                        response = encode_simple_string("OK")
                else:
                    response = encode_error("ERR wrong number of arguments for 'set' command")

            elif command == "GET":
                if len(args) == 1:
                    value = store.get(args[0])
                    response = encode_bulk_string(value)
                else:
                    response = encode_error("ERR wrong number of arguments for 'get' command")

            elif command == "SUBSCRIBE":
                for channel in args:
                    count = pubsub.subscribe(channel, connection)
                    # For each channel, we send a subscription confirmation
                    # Format: ["subscribe", channel, count]
                    # ✅ FIX: Pass raw values to encode_array, not already-encoded bytes
                    msg = encode_array([
                        "subscribe",  # Pass string, not encoded bytes
                        channel,      # Pass string, not encoded bytes
                        count         # Pass int, not encoded bytes
                    ])
                    connection.sendall(msg)
                # SUBSCRIBE handles its own responses per channel
                continue

            elif command == "PUBLISH":
                if len(args) == 2:
                    count = pubsub.publish(args[0], args[1])
                    response = encode_integer(count)
                else:
                    response = encode_error("ERR wrong number of arguments for 'publish' command")
            
            else:
                response = encode_error(f"ERR unknown command '{command}'")

            if response:
                connection.sendall(response)

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        pubsub.remove_client(connection)
        connection.close()
        print(f"Connection closed {address}")

def main():
    host = "localhost"
    port = 6379
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server started on {host}:{port}")
    
    try:
        while True:
            connection, address = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client, 
                args=(connection, address),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer stopping...")
    sys.exit(0)

if __name__ == "__main__":
    main()