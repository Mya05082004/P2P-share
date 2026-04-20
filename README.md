**HOW TO RUN**
1️. Start the Tracker Server (First Terminal)
bash
cd p2p-share
python tracker-server.py
Expected output:

[TRACKER] running on 127.0.0.1:9000
[TRACKER] Press Ctrl+C to stop
Keep this terminal running - tracker must stay active

2️. Share a File (Second Terminal - Peer 1)
bash
cd p2p-share/peer
python peer_client.py
Interactive steps:

Enter peer port: 5001

==================================================
P2P FILE SHARING SYSTEM
==================================================
1. Share a file
2. Download a file
3. List my shared files
4. Exit
==================================================
Choice: 1

File path: ../test.txt     (or full path to your file)

[SPLIT] Created chunk 0: 1048576 bytes
[SPLIT] File test.txt split into 5 chunks
[TRACKER] OK
[SUCCESS] Now sharing 'test.txt' with 5 chunks


3️. Download the File (Third Terminal - Peer 2)
bash
cd p2p-share/peer
python peer_client.py
Interactive steps:

Enter peer port: 5002

==================================================
P2P FILE SHARING SYSTEM
==================================================
1. Share a file
2. Download a file
3. List my shared files
4. Exit
==================================================
Choice: 2

Filename to download: test.txt

[DOWNLOAD] Looking for test.txt...
[TRACKER] Found 1 peers
[DOWNLOAD] Need 5 chunks

[DOWNLOAD] Connecting to 127.0.0.1:5001 for test.txt_chunk0
[DOWNLOAD] Expecting 1048576 bytes
[OK] Downloaded test.txt_chunk0

[MERGE] Merging 5 chunks into downloaded_test.txt
[SUCCESS] File downloaded as: downloaded_test.txt


4️. Verify the Downloaded File
bash
# Check if file exists
ls downloaded_test.txt

# Compare with original
diff test.txt downloaded_test.txt  # Should show no differences
