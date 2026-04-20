import socket
import os
import threading

# Get absolute path to chunks directory (located one level up from current directory)
# Example: if script is in /p2p-share/peer/, chunks will be in /p2p-share/chunks/
CHUNK_DIR = os.path.abspath("../chunks")

def start_uploader(port):
    """
    Start the uploader server to serve file chunks to requesting peers.
    This runs as a background thread on each peer that has files to share.
    
    Args:
        port: Port number to listen on for incoming chunk requests
    """
    # Create TCP socket for the uploader server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # SO_REUSEADDR allows immediate restart without "address already in use" error
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to all available network interfaces (0.0.0.0) on specified port
    # This allows connections from localhost and other machines on the network
    server.bind(("0.0.0.0", port))
    
    # Listen for incoming connections (max 5 pending connections in queue)
    server.listen(5)
    
    print(f"[UPLOADER] Running on port {port}")
    print(f"[UPLOADER] Serving chunks from: {CHUNK_DIR}")

    # Main server loop - continuously accept and handle connections
    while True:
        try:
            # Accept incoming connection (blocking call)
            # Returns: connection object and client address
            conn, addr = server.accept()
            print(f"[UPLOADER] Connection from {addr}")
            
            # Create a new thread to handle this upload request
            # This allows handling multiple simultaneous downloads
            thread = threading.Thread(target=handle_upload, args=(conn,))
            thread.daemon = True  # Thread will exit when main program exits
            thread.start()
            
        except Exception as e:
            print(f"[UPLOADER ERROR] {e}")

def handle_upload(conn):
    """
    Handle an individual upload request from a downloading peer.
    Protocol:
    1. Receive chunk name from requester
    2. Look up chunk in chunks directory
    3. Send size header: "{size}\n"
    4. Send chunk data
    5. Close connection
    
    Args:
        conn: Socket connection object for this specific client
    """
    try:
        # Step 1: Receive the chunk name from the requesting peer
        # Maximum 1024 bytes, decode from bytes to string, remove whitespace
        chunk_name = conn.recv(1024).decode().strip()
        print(f"[UPLOADER] Request for chunk: {chunk_name}")
        
        # Step 2: Construct full path to the requested chunk
        # Join chunks directory with the requested chunk filename
        chunk_path = os.path.join(CHUNK_DIR, chunk_name)
        
        # Step 3: Check if the requested chunk exists
        if os.path.exists(chunk_path):
            # Read the entire chunk file into memory
            with open(chunk_path, "rb") as f:
                data = f.read()
                
            # Step 4: Send size header first
            # Format: "{size}\n" - newline helps receiver know header is complete
            # Example: "1048576\n" for a 1MB chunk
            size_header = f"{len(data)}\n"
            conn.sendall(size_header.encode())  # Encode string to bytes
            
            # Step 5: Send the actual chunk data
            conn.sendall(data)
            
            print(f"[UPLOADER] Sent {chunk_name}: {len(data)} bytes")
        else:
            # Chunk not found - send header with size 0
            # This tells the downloader that the chunk is unavailable
            conn.sendall(b"0\n")
            print(f"[UPLOADER] Chunk not found: {chunk_name}")
            
    except socket.timeout:
        # Handle timeout errors (if socket timeout was set)
        print(f"[UPLOADER] Timeout error for chunk: {chunk_name}")
    except ConnectionResetError:
        # Handle case where client disconnects unexpectedly
        print(f"[UPLOADER] Connection reset by peer")
    except Exception as e:
        # Catch any other exceptions and log them
        print(f"[UPLOADER ERROR] {e}")
    finally:
        # Always close the connection when done, even if error occurred
        # This prevents resource leaks
        conn.close()