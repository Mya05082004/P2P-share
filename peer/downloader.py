import socket
import threading
import os

CHUNK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../chunks"))
os.makedirs(CHUNK_DIR, exist_ok=True)

def download_chunk(peer, chunk_name):
    """Download a single chunk from a peer"""
    try:
        print(f"[DOWNLOAD] Connecting to {peer['ip']}:{peer['port']} for {chunk_name}")
        s = socket.socket()
        s.settimeout(30)
        s.connect((peer["ip"], peer["port"]))
        
        # Send chunk name with newline
        s.sendall(f"{chunk_name}\n".encode())
        print(f"[DOWNLOAD] Sent request for {chunk_name}")
        
        # Read header (size)
        header = b""
        timeout_counter = 0
        while not header.endswith(b"\n"):
            try:
                data = s.recv(64)
                if not data:
                    raise Exception("Connection lost while reading header")
                header += data
                timeout_counter = 0
            except socket.timeout:
                timeout_counter += 1
                if timeout_counter > 5:
                    raise Exception("Timeout reading header")
                continue
        
        size_str = header.strip().decode()
        print(f"[DOWNLOAD] Header received: '{size_str}'")
        size = int(size_str)
        
        if size == 0:
            print(f"[SKIP] {chunk_name} not found on peer")
            return False
        
        print(f"[DOWNLOAD] Expecting {size} bytes for {chunk_name}")
        
        # Save chunk
        path = os.path.join(CHUNK_DIR, chunk_name)
        received = 0
        
        with open(path, "wb") as f:
            while received < size:
                remaining = size - received
                chunk_size = min(8192, remaining)
                data = s.recv(chunk_size)
                if not data:
                    break
                f.write(data)
                received += len(data)
                
                # Show progress
                if received % (1024*100) < 8192:  # Update every 100KB
                    progress = (received / size) * 100
                    print(f"[DOWNLOAD] {chunk_name}: {progress:.1f}% ({received}/{size})", end='\r')
        
        print(f"\n[DOWNLOAD] {chunk_name}: {received}/{size} bytes")
        
        if received != size:
            print(f"[ERROR] Incomplete {chunk_name}")
            if os.path.exists(path):
                os.remove(path)  # Delete incomplete file
            return False
        else:
            print(f"[OK] Downloaded {chunk_name}")
            return True
            
    except socket.timeout:
        print(f"\n[ERROR] Timeout downloading {chunk_name}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Failed to download {chunk_name}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        s.close()

def download_all(peers, chunks):
    """Download all chunks in parallel"""
    threads = []
    results = {}
    
    print(f"\n[DOWNLOAD] Starting download of {len(chunks)} chunks")
    
    for chunk in chunks:
        # Find peer that has this chunk
        idx = int(chunk.split("_chunk")[-1])
        
        peer = None
        for p in peers:
            if idx in p["chunks"]:
                peer = p
                break
        
        if not peer:
            print(f"[WARN] No peer found for {chunk}")
            results[chunk] = False
            continue
        
        # Start download thread
        def download_wrapper(chunk_name, peer_obj):
            results[chunk_name] = download_chunk(peer_obj, chunk_name)
        
        t = threading.Thread(target=download_wrapper, args=(chunk, peer))
        t.daemon = True
        t.start()
        threads.append(t)
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Check results
    success_count = sum(1 for success in results.values() if success)
    print(f"\n[DOWNLOAD] Completed: {success_count}/{len(chunks)} chunks downloaded")
    
    # Retry failed downloads 
    failed = [chunk for chunk, success in results.items() if not success]
    if failed:
        print(f"[WARN] Failed chunks: {failed}")
        return False
    
    return True