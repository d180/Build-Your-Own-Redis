import threading
import time

class KeyValueStore:
    def __init__(self):
        self.store = {}
        self.expiries = {}
        self.lock = threading.Lock()

    def set(self, key, value, px=None):
        with self.lock:
            self.store[key] = value
            if px:
                self.expiries[key] = time.time() * 1000 + px
            elif key in self.expiries:
                del self.expiries[key]

    def get(self, key):
        with self.lock:
            if key not in self.store:
                return None
            
            if key in self.expiries:
                if time.time() * 1000 > self.expiries[key]:
                    del self.store[key]
                    del self.expiries[key]
                    return None
            
            return self.store[key]

    def delete(self, key):
        with self.lock:
            if key in self.store:
                del self.store[key]
                if key in self.expiries:
                    del self.expiries[key]
                return 1
            return 0
