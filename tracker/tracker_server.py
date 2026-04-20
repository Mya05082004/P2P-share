import socket
import threading
import json
import time

# Tracker server configuration
HOST = "127.0.0.1"  # Localhost address
PORT = 9000         # Port number for tracker server

# Dictionary to store registered files and their peers
# Structure: {filename: [peer1, peer2, ...]}
files = {}

# Thread lock for thread-safe operations on shared resources
lock = threading.Lock()

def handle_client(conn):
    """
    Handle client requests (REGISTER or GET_PEERS)
    
    Args:
        conn: Socket connection object for the client
    """
    try:
        # Receive and decode JSON data from client (max 4096 bytes)
        data = conn.recv(4096).decode()
        req = json.loads(data)  # Parse JSON into Python dictionary

        # Handle REGISTER request - Peer wants to share a file
        if req["type"] == "REGISTER":
            filename = req["filename"]  # Name of the file being shared
            
            # Create peer information dictionary
            peer = {
                "ip": req["ip"],           # Peer's IP address
                "port": req["port"],       # Peer's port number
                "chunks": req["chunks"],   # List of chunk indices this peer has
                "timestamp": time.time()   # Registration time (for cleanup)
            }

            # Thread-safe update of files dictionary
            with lock:
                # Get existing peers for this file, or create new list
                peers = files.setdefault(filename, [])
                peer_exists = False
                
                # Check if this peer is already registered
                for existing_peer in peers:
                    if (existing_peer["ip"] == peer["ip"] and 
                        existing_peer["port"] == peer["port"]):
                        # Update existing peer's information
                        existing_peer["chunks"] = peer["chunks"]
                        existing_peer["timestamp"] = peer["timestamp"]
                        peer_exists = True
                        break
                
                # Add new peer if not already registered
                if not peer_exists:
                    peers.append(peer)

            # Send success response to client
            conn.sendall(b"OK")
            print(f"[REGISTER] {filename} from {peer['ip']}:{peer['port']} - Chunks: {peer['chunks']}")

        # Handle GET_PEERS request - Client wants to download a file
        elif req["type"] == "GET_PEERS":
            filename = req["filename"]  # Name of the file to download
            
            # Thread-safe retrieval of peer list
            with lock:
                # Clean up stale peers (older than 5 minutes = 300 seconds)
                if filename in files:
                    current_time = time.time()
                    # Keep only peers that are still active (timestamp within 5 minutes)
                    files[filename] = [
                        peer for peer in files[filename] 
                        if current_time - peer.get("timestamp", current_time) < 300
                    ]
                # Get the (cleaned) list of peers for this file
                peers = files.get(filename, [])

            # Send peer list as JSON to client
            conn.sendall(json.dumps(peers).encode())
            print(f"[GET_PEERS] {filename} -> {len(peers)} peers found")

        # Handle unknown command types
        else:
            conn.sendall(b"UNKNOWN_COMMAND")

    except Exception as e:
        # Log any errors that occur during client handling
        print(f"[TRACKER ERROR] {e}")
    finally:
        # Always close the connection when done
        conn.close()

def start_tracker():
    """
    Start the tracker server and listen for incoming connections
    """
    # Create TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow reuse of address (helps with quick restarts)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to host and port
    server.bind((HOST, PORT))
    # Listen for up to 10 pending connections
    server.listen(10)

    print(f"[TRACKER] running on {HOST}:{PORT}")
    print("[TRACKER] Press Ctrl+C to stop\n")

    try:
        # Main server loop - accept and handle connections
        while True:
            # Accept incoming connection (blocking call)
            conn, addr = server.accept()
            print(f"[CONNECTION] from {addr}")
            # Create a new thread to handle each client (non-blocking)
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        print("\n[TRACKER] Shutting down...")
    finally:
        # Always close the server socket
        server.close()

# Entry point of the script
if __name__ == "__main__":
    start_tracker()