class RESPDecoder:
    def __init__(self, connection):
        self.connection = connection
        self.file = connection.makefile('rb')

    def decode(self):
        """
        Decodes a RESP message. Returns None on connection error/EOF.
        """
        try:
            # Inspect first byte
            byte = self.file.read(1)
            if not byte:
                return None
            
            dtype = byte
            
            if dtype == b'+':
                return self._decode_simple_string()
            elif dtype == b'-':
                return self._decode_error()
            elif dtype == b':':
                return self._decode_integer()
            elif dtype == b'$':
                return self._decode_bulk_string()
            elif dtype == b'*':
                return self._decode_array()
            else:
                # Fallback: Inline command
                # We read one byte 'X'. We need to read the rest of the line '... \r\n'
                # and return ['X...']
                line = self.file.readline()
                if not line:
                    return None
                
                full_line = dtype + line
                full_line = full_line.strip()
                if not full_line:
                    return None
                
                # Decode and split by whitespace
                decoded = full_line.decode('utf-8', errors='replace')
                return decoded.split()
                
        except (ConnectionResetError, BrokenPipeError):
            return None
        except Exception as e:
            print(f"DEBUG: decode exception: {e}", flush=True)
            return None

    def _read_line(self):
        """Reads a line ending in CRLF, strips CRLF."""
        line = self.file.readline()
        if not line:
            return None
        
        # Simple strip of whitespace to handle \r\n or \n
        return line.strip()

    def _decode_simple_string(self):
        line = self._read_line()
        if line is None: return None
        return line.decode('utf-8', errors='replace')

    def _decode_error(self):
        line = self._read_line()
        if line is None: return None
        return Exception(line.decode('utf-8', errors='replace'))

    def _decode_integer(self):
        line = self._read_line()
        if line is None: return None
        try:
            return int(line)
        except ValueError:
            return None

    def _decode_bulk_string(self):
        # Format: $ <length> \r\n <data> \r\n
        line = self._read_line()
        if line is None: return None
        
        try:
            length = int(line)
        except ValueError:
            print(f"DEBUG: Invalid bulk length: {line}", flush=True)
            return None

        if length == -1:
            return None

        # Read exact data
        data = self.file.read(length)
        if len(data) != length:
            print(f"DEBUG: Incomplete bulk read. Expected {length}, got {len(data)}", flush=True)
            return None
            
        # ✅ FIX: Consume EXACTLY 2 bytes (\r\n) instead of readline()
        # Using readline() was over-consuming data when the next command followed immediately,
        # causing buffer desynchronization
        crlf = self.file.read(2)
        if crlf not in (b'\r\n', b'\n'):
            print(f"DEBUG: Expected CRLF after bulk string, got: {crlf!r}", flush=True)
            # Don't return None - the data is still valid

        return data.decode('utf-8', errors='replace')

    def _decode_array(self):
        # Format: * <count> \r\n <element-1> ... <element-n>
        line = self._read_line()
        if line is None: return None
        
        try:
            count = int(line)
        except ValueError:
             print(f"DEBUG: Invalid array length: {line}", flush=True)
             return None

        if count == -1:
            return None

        array = []
        for _ in range(count):
            val = self.decode()
            array.append(val)
        return array


# --- Encoders ---

def encode_simple_string(s):
    return f"+{s}\r\n".encode('utf-8')

def encode_error(e):
    return f"-{e}\r\n".encode('utf-8')

def encode_integer(i):
    return f":{i}\r\n".encode('utf-8')

def encode_bulk_string(s):
    if s is None:
        return b"$-1\r\n"
    return f"${len(s)}\r\n{s}\r\n".encode('utf-8')

def encode_array(items):
    if items is None:
        return b"*-1\r\n"
    res = f"*{len(items)}\r\n".encode('utf-8')
    for item in items:
        if isinstance(item, str):
            res += encode_bulk_string(item)
        elif isinstance(item, int):
            res += encode_integer(item)
        elif isinstance(item, bytes):
             res += f"${len(item)}\r\n".encode('utf-8') + item + b"\r\n"
        elif isinstance(item, list):
            res += encode_array(item)
        elif item is None:
             res += encode_bulk_string(None)
        else:
             raise ValueError(f"Unsupported type for RESP encoding: {type(item)}")
    return res