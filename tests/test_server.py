
import socket
import time
import threading
import sys

def send_command(sock, command):
    sock.sendall(command.encode('utf-8'))
    response = sock.recv(1024)
    return response.decode('utf-8')

def test_basic_commands():
    try:
        sock = socket.create_connection(('localhost', 6379))
        
        # Test PING
        assert "+PONG" in send_command(sock, "*1\r\n$4\r\nPING\r\n")
        print("PING passed")

        # Test SET
        assert "+OK" in send_command(sock, "*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n")
        print("SET passed")

        # Test GET
        response = send_command(sock, "*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n")
        assert "$3\r\nbar" in response
        print("GET passed")
        
        sock.close()
    except Exception as e:
        print(f"Basic commands failed: {e}")
        sys.exit(1)

def test_pubsub_subscriber():
    try:
        sock = socket.create_connection(('localhost', 6379))
        # Subscribe to channel 'test'
        sock.sendall("*2\r\n$9\r\nSUBSCRIBE\r\n$4\r\ntest\r\n".encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        assert "subscribe" in response
        assert "test" in response
        
        print("Subscriber waiting for message...")
        # Wait for message
        response = sock.recv(1024).decode('utf-8')
        assert "message" in response
        assert "test" in response
        assert "hello" in response
        print("Pub/Sub passed (Subscriber)")
        sock.close()
    except Exception as e:
        print(f"Subscriber failed: {e}")
        sys.exit(1)

def test_pubsub_publisher():
    try:
        time.sleep(1) # Wait for subscriber
        sock = socket.create_connection(('localhost', 6379))
        # Publish to channel 'test'
        sock.sendall("*3\r\n$7\r\nPUBLISH\r\n$4\r\ntest\r\n$5\r\nhello\r\n".encode('utf-8'))
        response = sock.recv(1024).decode('utf-8')
        assert ":" in response # Integer response
        print("Pub/Sub passed (Publisher)")
        sock.close()
    except Exception as e:
        print(f"Publisher failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting tests...")
    
    # Run basic tests
    test_basic_commands()
    
    # Run Pub/Sub tests
    sub_thread = threading.Thread(target=test_pubsub_subscriber)
    pub_thread = threading.Thread(target=test_pubsub_publisher)
    
    sub_thread.start()
    pub_thread.start()
    
    sub_thread.join()
    pub_thread.join()
    
    print("All tests passed!")
