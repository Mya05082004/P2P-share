import socket
import json
import os
import threading
import time
from uploader import start_uploader  # Import upload server module
from downloader import download_all    # Import download functions

# Tracker server address (host, port)
TRACKER = ("127.0.0.1", 9000)

# Get peer port from user input (each peer needs unique port)
PEER_PORT = int(input("Enter peer port: "))

# Set up chunks directory - absolute path to ../chunks from current location
CHUNK_DIR = os.path.abspath("../chunks")
os.makedirs(CHUNK_DIR, exist_ok=True)  # Create directory if it doesn't exist

# Debug information to verify paths
print(f"[DEBUG] Chunk directory: {CHUNK_DIR}")
print(f"[DEBUG] Current directory: {os.getcwd()}")

def split_file(filepath, size=1024*1024):
    """
    Split a file into smaller chunks (default 1MB each).
    
    Args:
        filepath: Path to the file to split
        size: Chunk size in bytes (default 1MB = 1,048,576 bytes)
    
    Returns:
        filename: Base name of the original file
        chunks: List of chunk indices created
    
    Raises:
        FileNotFoundError: If the input file doesn't exist
    """
    # Validate that input file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Extract just the filename without path
    filename = os.path.basename(filepath)
    chunks = []  # List to store chunk indices

    # Open file in binary read mode
    with open(filepath, "rb") as f:
        i = 0
        while True:
            # Read chunk of data (size bytes)
            data = f.read(size)
            if not data:  # End of file reached
                break
            
            # Create chunk filename: e.g., "test.txt_chunk0"
            name = f"{filename}_chunk{i}"
            chunk_path = os.path.join(CHUNK_DIR, name)
            
            # Write chunk to chunks directory
            with open(chunk_path, "wb") as c:
                c.write(data)
            
            chunks.append(i)  # Store chunk index
            print(f"[SPLIT] Created chunk {i}: {len(data)} bytes")
            i += 1

    print(f"[SPLIT] File {filename} split into {len(chunks)} chunks")
    return filename, chunks

def register(filename, chunks):
    """
    Register this peer's file with the tracker server.
    This allows other peers to discover this file for downloading.
    
    Args:
        filename: Name of the file being shared
        chunks: List of chunk indices this peer has
    """
    # Create socket connection to tracker
    s = socket.socket()
    s.connect(TRACKER)

    # Prepare registration message
    msg = {
        "type": "REGISTER",      # Message type identifier
        "filename": filename,    # File name
        "ip": "127.0.0.1",       # This peer's IP
        "port": PEER_PORT,       # This peer's upload port
        "chunks": chunks         # List of available chunks
    }

    # Send JSON-encoded message to tracker
    s.sendall(json.dumps(msg).encode())
    
    # Wait for tracker response
    response = s.recv(1024).decode()
    print(f"[TRACKER] {response}")
    s.close()  # Close connection

def get_peers(filename):
    """
    Query tracker for peers that have the requested file.
    
    Args:
        filename: Name of the file to search for
    
    Returns:
        List of peer dictionaries containing ip, port, and chunks
    """
    # Create socket connection to tracker
    s = socket.socket()
    s.connect(TRACKER)

    # Prepare query message
    msg = {"type": "GET_PEERS", "filename": filename}
    s.sendall(json.dumps(msg).encode())

    # Receive and parse peer list
    peers = json.loads(s.recv(4096).decode())
    s.close()
    
    print(f"[TRACKER] Found {len(peers)} peers")
    return peers

def merge(filename, chunks):
    """
    Merge downloaded chunks back into the complete original file.
    
    Args:
        filename: Original filename
        chunks: List of chunk indices (sorted)
    
    Returns:
        bool: True if merge successful, False otherwise
    """
    # Output filename with "downloaded_" prefix
    out = f"downloaded_{filename}"
    
    print(f"\n[MERGE] Merging {len(chunks)} chunks into {out}")
    
    # Verify all chunks exist before merging
    missing = []
    for i in chunks:
        chunk_path = os.path.join(CHUNK_DIR, f"{filename}_chunk{i}")
        if not os.path.exists(chunk_path):
            missing.append(i)
    
    if missing:
        print(f"[ERROR] Missing chunks: {missing}")
        return False
    
    # Merge chunks in order
    with open(out, "wb") as f:
        for i in chunks:
            chunk_path = os.path.join(CHUNK_DIR, f"{filename}_chunk{i}")
            with open(chunk_path, "rb") as c:
                data = c.read()
                f.write(data)
                print(f"[MERGE] Written chunk {i}: {len(data)} bytes")
    
    # Verify final file was created
    if os.path.exists(out):
        size = os.path.getsize(out)
        print(f"[MERGED] {out} created successfully ({size} bytes)")
        return True
    else:
        print(f"[ERROR] Failed to create {out}")
        return False

def list_available_files():
    """
    List all files currently available in the chunks directory.
    
    Returns:
        dict: Dictionary mapping filenames to list of chunk files
    """
    if not os.path.exists(CHUNK_DIR):
        return []
    
    files_dict = {}
    # Iterate through all files in chunks directory
    for chunk_file in os.listdir(CHUNK_DIR):
        if "_chunk" in chunk_file:  # Only process chunk files
            # Extract base filename (remove "_chunkX" suffix)
            filename = chunk_file.split("_chunk")[0]
            if filename not in files_dict:
                files_dict[filename] = []
            files_dict[filename].append(chunk_file)
    
    return files_dict

if __name__ == "__main__":
    """
    Main program entry point.
    Starts uploader in background and presents interactive menu.
    """
    
    # Start uploader server as a background daemon thread
    # This allows other peers to download chunks from this peer
    uploader_thread = threading.Thread(
        target=start_uploader,
        args=(PEER_PORT,),
        daemon=True  # Thread exits when main program exits
    )
    uploader_thread.start()
    
    # Give uploader time to initialize
    time.sleep(1)
    
    # Main interactive loop
    while True:
        # Display menu
        print("\n" + "="*50)
        print("P2P FILE SHARING SYSTEM")
        print("="*50)
        print("1. Share a file")      # Upload/seed a file
        print("2. Download a file")    # Download a file from peers
        print("3. List my shared files")  # Show local shared files
        print("4. Exit")               # Exit program
        print("="*50)
        
        choice = input("Choice: ")
        
        # OPTION 1: Share a file (Seeder)
        if choice == "1":
            file = input("File path: ").strip()
            
            # Validate file exists
            if not os.path.exists(file):
                print(f"[ERROR] File '{file}' not found!")
                continue
            
            try:
                # Split file into chunks
                filename, chunks = split_file(file)
                # Register with tracker
                register(filename, chunks)
                print(f"[SUCCESS] Now sharing '{filename}' with {len(chunks)} chunks")
                print("[SEEDER] Running in background...")
            except Exception as e:
                print(f"[ERROR] {e}")
        
        # OPTION 2: Download a file (Leecher)
        elif choice == "2":
            filename = input("Filename to download: ").strip()
            
            print(f"[DOWNLOAD] Looking for {filename}...")
            # Get list of peers that have this file
            peers = get_peers(filename)
            
            if not peers:
                print(f"[ERROR] No peers found for {filename}")
                continue
            
            # Collect all unique chunk indices from all peers
            all_chunks = set()
            for p in peers:
                all_chunks.update(p["chunks"])
            
            # Sort chunks for proper order
            all_chunks = sorted(all_chunks)
            names = [f"{filename}_chunk{i}" for i in all_chunks]
            
            print(f"[DOWNLOAD] Need {len(names)} chunks")
            print(f"[DOWNLOAD] Chunks: {all_chunks}")
            
            # Download all chunks in parallel
            success = download_all(peers, names)
            
            if success:
                # Merge chunks into final file
                if merge(filename, all_chunks):
                    print(f"\n[SUCCESS] File downloaded as: downloaded_{filename}")
                else:
                    print("[ERROR] Failed to merge chunks")
            else:
                print("[ERROR] Download failed")
        
        # OPTION 3: List locally shared files
        elif choice == "3":
            files_dict = list_available_files()
            if files_dict:
                print("\n[MY SHARED FILES]")
                for filename, chunks in files_dict.items():
                    print(f"  - {filename}: {len(chunks)} chunks")
                    # Calculate total size
                    total_size = 0
                    for chunk in chunks:
                        chunk_path = os.path.join(CHUNK_DIR, chunk)
                        if os.path.exists(chunk_path):
                            total_size += os.path.getsize(chunk_path)
                    print(f"    Size: {total_size} bytes ({total_size/1024:.2f} KB)")
            else:
                print("\n[MY SHARED FILES] No files shared yet")
        
        # OPTION 4: Exit
        elif choice == "4":
            print("[EXIT] Goodbye!")
            break
        
        # Invalid option
        else:
            print("[ERROR] Invalid choice")