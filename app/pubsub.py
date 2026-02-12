import threading
from collections import defaultdict
from .resp import encode_array, encode_bulk_string

class PubSubManager:
    def __init__(self):
        self.channels = defaultdict(list)
        self.lock = threading.Lock()

    def subscribe(self, channel, connection):
        with self.lock:
            if connection not in self.channels[channel]:
                self.channels[channel].append(connection)
            return len(self.subscriptions(connection))

    def unsubscribe(self, channel, connection):
        with self.lock:
            if channel in self.channels and connection in self.channels[channel]:
                self.channels[channel].remove(connection)
                if not self.channels[channel]:
                    del self.channels[channel]
            return len(self.subscriptions(connection))

    def subscriptions(self, connection):
        """Returns a list of channels the connection is subscribed to."""
        subs = []
        for channel, clients in self.channels.items():
            if connection in clients:
                subs.append(channel)
        return subs

    def publish(self, channel, message):
        with self.lock:
            if channel not in self.channels:
                return 0
            
            clients = self.channels[channel]
            count = 0
            disconnected = []
            
            # Message format: ["message", channel, message]
            # ✅ FIX: Pass raw values to encode_array, not already-encoded bytes
            response = encode_array([
                "message",  # Pass string, not encoded bytes
                channel,    # Pass string, not encoded bytes
                message     # Pass string, not encoded bytes
            ])

            for client in clients:
                try:
                    client.sendall(response)
                    count += 1
                except (BrokenPipeError, ConnectionResetError):
                    disconnected.append(client)
            
            for client in disconnected:
                self.channels[channel].remove(client)
                
            return count

    def remove_client(self, connection):
        """Removes a client from all subscriptions."""
        with self.lock:
            for channel in list(self.channels.keys()):
                if connection in self.channels[channel]:
                    self.channels[channel].remove(connection)
                    if not self.channels[channel]:
                        del self.channels[channel]