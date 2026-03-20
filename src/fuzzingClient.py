import socket
import json
import time
import random

HOST = '127.0.0.1'
PORT = 5050

def run_fuzzer():
    # 1. Setup Socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
        print(f"[CONNECTED] Connected to server at {HOST}:{PORT}")
    except ConnectionRefusedError:
        print("[ERROR] Server is not running.")
        return

    # 2. Handshake: Send CONNECT with TankParts
    # Use the exact keys your TankParts dataclass expects
    setup_data = {
        "type": "CONNECT",
        "content": {
            "tracks": "heavy_tracks",
            "armor": "heavy_armor",
            "sights": "standard_sight",
            "barrels": "standard_barrel"
        }
    }
    client.send(json.dumps(setup_data).encode('utf-8'))
    
    # Wait for ACCEPTED response
    response = client.recv(1024).decode('utf-8')
    print(f"[SERVER RESPONSE] {response}")

    # 3. Fuzzing Loop: Send random actions
    possible_keys = ["W", "A", "S", "D", "SPACE", "JUNK_KEY"]
    
    print("[FUZZING] Starting action spam...")
    try:
        for i in range(100): # Send 100 random bursts
            # Randomly pick 1-3 keys to "press"
            active_keys = random.sample(possible_keys, random.randint(1, 3))
            
            action_message = {
                "type": "ACTION",
                "content": {
                    "keys": active_keys
                }
            }
            
            client.send(json.dumps(action_message).encode('utf-8'))
            
            # Listen for the server's broadcast update
            # (Note: In a real client, this would be in a separate thread)
            try:
                client.settimeout(0.1)
                update = client.recv(4096).decode('utf-8')
                # print(f"Tick {i}: Received World Update") 
            except socket.timeout:
                pass

            time.sleep(0.05) # Simulate ~20 actions per second
            
    except Exception as e:
        print(f"[ERROR] Fuzzer crashed: {e}")
    finally:
        # 4. Cleanup: Send LEAVE
        leave_msg = {"type": "LEAVE", "content": {}}
        client.send(json.dumps(leave_msg).encode('utf-8'))
        client.close()
        print("[SHUTDOWN] Fuzzer disconnected.")

if __name__ == "__main__":
    run_fuzzer()