import json
from pathlib import Path
import socket
import threading
import random
import queue
import time
import math
from dataclasses import dataclass, field, asdict
from typing import List, Tuple
import sys

BASE_DIR = Path(__file__).resolve().parent

HOST = '0.0.0.0'
PORT = 5050

tankComponents_path = BASE_DIR / "config" / "tankComponents.json"

with open(tankComponents_path) as f:
    COMPONENTS = json.load(f)

config_path = BASE_DIR / "config" / "config.json"

with open(config_path) as f:
    config = json.load(f)
TICK_SPEED = config["settings"]["tick_speed"]
TICK_DELAY = 1/TICK_SPEED

MAP_HEIGHT = config["settings"]["MAX_HEIGHT"]
MAP_WIDTH = config["settings"]["MAX_WIDTH"]

last_shot_time = {} # {player_id: timestamp}

server_running = True

tilemap = []

@dataclass
class TankParts:
    tracks: str
    armor: str
    sights: str
    barrels: str

@dataclass
class PlayerParts:
    id: int
    parts: TankParts

@dataclass
class Player:
  id: int
  position: Tuple[float, float]
  rotation: float
  health: float = 100.0 # this value can change, depending on parts (will write a script to determine it)

@dataclass
class Shell:
  id: int
  shell_type: str
  position: Tuple[float, float]
  velocity: Tuple[float, float]

@dataclass
class EntityList:
  players: List[Player] = field(default_factory = list)
  shells: List[Shell] = field(default_factory = list)



parts_registry = {} # {player_id: PlayerParts} Sent at start
active_players = {} # {player_id: Player} Sent every tick
world_shells = [] # list of shells

shutdown_event = threading.Event()

game_started = False

# Utility

_player_id_counter = 0
_id_lock = threading.Lock()
def generatePlayerID():
    # gives uniquePlayerID
    global _player_id_counter
    with _id_lock:
        _player_id_counter += 1
        return _player_id_counter

# These are the map and world states
def initializeMap(width, height):
    # Fill with random noise initially
    num_tiles = config.get("num_tiles", 5)
    tilemap = [[random.randint(1, num_tiles) for _ in range(width)] for _ in range(height)]

    # smoothing (This is why I hate stats)
    for _ in range(3):
        new_map = [row[:] for row in tilemap]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                # Count neighbors
                neighbors = []
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        neighbors.append(tilemap[y+dy][x+dx])
                
                # Set current tile to the most common neighbor (Majority Rule)
                most_common = max(set(neighbors), key=neighbors.count)
                new_map[y][x] = most_common
        tilemap = new_map

    # Add some "Static" (Unbreakable Walls/Borders)
    # Tile 5 is a stone
    for y in range(height):
        tilemap[y][0] = 5
        tilemap[y][width-1] = 5
    for x in range(width):
        tilemap[0][x] = 5
        tilemap[height-1][x] = 5

    return tilemap


def serializeWorldState():
    global world_shells
    # turns world state into something the connection can send
    state = {
        "type": "UPDATE",
        "players": [],
        "shells": []
    }

    for pid, player in active_players.items():
        state["players"].append({
            "id": player.id,
            "pos": player.position,
            "rot": player.rotation,
            "hp": player.health
        })
    
    for shell in world_shells:
        state["shells"].append({
            "id": shell.id,
            "pos": shell.position,
            "type": shell.shell_type
        })
    
    return json.dumps(state)

# These are the combat functions
def detectBulletHits():
    # goes through list of bullets to check for any hits (radial math, simple stuff)
    global world_shells
    remaining_shells = []
    HIT_RADIUS = 0.5

    for shell in world_shells:
        hit_something = False

        for pid, player in active_players.items():
            # for each player, check if in radius
            dist = math.sqrt(
                (shell.position[0] - player.position[0])**2 +
                (shell.position[1] - player.position[1])**2
            )
    
            # if in radius, break from loop, say we hit something and apply damage
            if dist < HIT_RADIUS:
                print(f"[HIT] Player {pid} was struck by Shell {shell.id}!")
                applyDamage(pid, shell.shell_type)
                hit_something = True
                break
        
        # if shell isn't hitting, keep moving
        if not hit_something:
            remaining_shells.append(shell)
    
    world_shells[:] = remaining_shells

def applyDamage(pid, shell_type):
    # if you get hit by bullet, you get hurt, bullet damage is set in the tankComponents.json
    player = active_players.get(pid)

    if player:
        damage = COMPONENTS["barrels"][shell_type]["damage"]
        player.health -= damage
        print(f"[DAMAGE] Player {pid} hit! Health: {player.health}")

        if player.health <= 0:
            handlePlayerDeath(pid)
    pass

def handlePlayerDeath(pid):
    global active_players
    # What do we do when players die? I got no clue yet
    if pid in active_players:
        print(f"[DEATH] Player {pid} has been destroyed!")
        del active_players[pid]
    
    if len(active_players) == 1:
        winner = next(iter(active_players))
        print(f"[VICTORY] Player {winner} has won!")

        # Send out message to all players
        victory_message = {
            "type": "VICTORY",
            "content": {
                "id": winner
            }
        }
        message_bytes = json.dumps(victory_message).encode('utf-8')
        for pid, conn in clients.items():
            try:
                conn.send(message_bytes)
            except Exception as e:
                print(f"[ERROR] Failed to send start sync to Player {pid}: {e}")

# These are the bullet functions
def spawnBullet(player_id: int):
    global world_shells, last_shot_time
    current_time = time.time()
    # handles the shoot action from clients, spawns in a bullet
    last_time = last_shot_time.get(player_id, 0)
    
    player = active_players.get(player_id)
    static_data = parts_registry.get(player_id)
    if not player:
        return
    
    barrel_type = static_data.parts.barrels
    barrel_stats = COMPONENTS["barrels"][barrel_type]
    SHOOT_COOLDOWN = barrel_stats["reload"]

    if current_time - last_time < SHOOT_COOLDOWN:
        return


    BULLET_SPEED = barrel_stats["bullet_speed"]

    rad = math.radians(player.rotation)
    vx = math.cos(rad) * BULLET_SPEED
    vy = math.sin(rad) * BULLET_SPEED

    dx = math.cos(rad) * 0.75
    dy = math.sin(rad) * 0.75

    bulletSpawnX, bulletSpawnY = player.position
    bulletSpawnX += dx
    bulletSpawnY += dy
    

    new_shell = Shell(
        id = random.randint(0, 999999),
        shell_type = barrel_type,
        position = (bulletSpawnX, bulletSpawnY),
        velocity = (vx,vy)
    )

    world_shells.append(new_shell)
    print(f"[COMBAT] Player {player_id} fired a {barrel_type} shell")

    last_shot_time[player_id] = current_time

def updateBulletPos():
    global world_shells, tilemap
    remaining_shells = []
    # updates where bullets are flying depending on their vectors
    # this updates all bullets in world_shells
    for shell in world_shells:
        vx, vy = shell.velocity
        curr_x, curr_y = shell.position

        # find new position
        new_x = curr_x + vx
        new_y = curr_y + vy

        grid_x = int(new_x)
        grid_y = int(new_y)
        # check map boundaries
        if 0 <= new_x <= MAP_WIDTH and 0 <= new_y <= MAP_HEIGHT:
            if tilemap[grid_y][grid_x] == 5:
                print(f"[COMBAT] Shell {shell.id} hit a wall")
                continue
            shell.position = (new_x,new_y)
            remaining_shells.append(shell)
        else:
            print(f"[COMBAT] Shell {shell.id} dissipated at bounds")
        
    world_shells[:] = remaining_shells

# These are the player functions

def _statCalculation(tankParts):
    armor = tankParts["armor"]
    hp = COMPONENTS["armor"][armor]["hp"]
    return hp

def addPlayer(tankParts):
    # when player joins, add player
    new_id = generatePlayerID()
    tank_parts = TankParts(**tankParts)
    static_data = PlayerParts(id=new_id, parts = tank_parts)

    # create dynamic dataclass
    dynamic_data = Player(
        id = new_id,
        position = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT)),
        rotation = 0.0,
        health = _statCalculation(tankParts)
    )

    # store them
    parts_registry[new_id] = static_data
    active_players[new_id] = dynamic_data

    print(f"[REGISTERED] Player {new_id} parts stored")
    return new_id

def removePlayer(pid):
    # when player leaves, remove player
    if pid in active_players:
        del active_players[pid]
    if pid in parts_registry:
        del parts_registry[pid]
    print(f"[DISCONNECT] Player {pid} removed from server.")

    if len(active_players) == 0:
        print(f"[SERVER] Zero players remaining. Initializing auto-shutdown...")
        shutdown_event.set()

def updatePlayerPos():
    # player position needs to update based on actions
    pass

def applyPlayerAction(player_id: int, action: dict):
    player = active_players.get(player_id)
    static_data = parts_registry.get(player_id)
    if not player:
        return # player left after sending action, before processing
    
    track_type = static_data.parts.tracks
    MOVE_SPEED = COMPONENTS["tracks"][track_type]["speed"]
    ROTATION_SPEED = COMPONENTS["tracks"][track_type]["turn_rate"]

    grid_x, grid_y = int(player.position[0]), int(player.position[1])
    speed_multiplier = 1.0

    if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
        current_tile = tilemap[grid_y][grid_x]
        if current_tile == 4:  # Water
            speed_multiplier = 0.5  # 50% speed reduction
        elif current_tile == 2: # Mud
            speed_multiplier = 0.8  # 20% speed reduction

    move_speed = MOVE_SPEED * speed_multiplier

    keys = action.get("keys", [])

    # Get rotated
    if "A" in keys:
        player.rotation -= ROTATION_SPEED
    if "D" in keys:
        player.rotation += ROTATION_SPEED
    
    player.rotation %= 360 # Cuz rotation is technically a ring of size 360

    # math is stupid, we think in degrees, but computers use radians
    rad = math.radians(player.rotation)

    move_dir = 0
    if "W" in keys: move_dir = 1
    elif "S" in keys: move_dir = -1

    if move_dir != 0:
        new_x = player.position[0] + (math.cos(rad) * move_speed * move_dir)
        new_y = player.position[1] + (math.sin(rad) * move_speed * move_dir)

        if 0 <= new_x <= MAP_WIDTH and 0 <= new_y <= MAP_HEIGHT:
            grid_x = int(new_x)
            grid_y = int(new_y)
            if tilemap[grid_y][grid_x] != 5:
                player.position = (new_x, new_y)

    if "SPACE" in keys:
        spawnBullet(player_id)

# These are the networking functions
def broadcastMessage():
    # send entity info to all clients
    pass

def parseMessage():
    # if type == action, add it to the list
    pass

def findSafeSpawn(tilemap):
    """
    Finds a random coordinate that is not a Wall (5) or Water (4).
    """
    max_attempts = 200
    for _ in range(max_attempts):
        rx = random.uniform(1, MAP_WIDTH - 1)
        ry = random.uniform(1, MAP_HEIGHT - 1)
        
        # Check tile type at this coordinate
        if tilemap[int(ry)][int(rx)] not in [4, 5]:
            return (rx, ry)
            
    # How is it all walls?
    return (MAP_WIDTH // 2, MAP_HEIGHT // 2)

def startGame():
    global game_started, tilemap
    game_started = True

    tilemap = initializeMap(MAP_WIDTH, MAP_HEIGHT)


    for pid, player in active_players.items():
            player.position = findSafeSpawn(tilemap)
            print(f"[SPAWN] Player {pid} safely placed at {player.position}")

    initial_sync = {
        "type": "GAME_START",
        "content": {
            "map": tilemap,
            "registry": {pid: asdict(p.parts) for pid, p in parts_registry.items()},
            "dimensions": {"width": MAP_WIDTH, "height": MAP_HEIGHT}
        }
    }

    message_bytes = json.dumps(initial_sync).encode('utf-8')
    for pid, conn in clients.items():
        try: 
            conn.send(message_bytes)
        except Exception as e:
            print(f"[ERROR] Failed to send start sync to Player {pid}: {e}")

def handleClientConnection(conn, addr):
    player_id = None
    buffer = "" # Add a buffer for this specific connection
    
    try:
        while True:
            try:
                raw_data = conn.recv(2048).decode('utf-8')
                if not raw_data:
                    print(f"[INFO] Client {addr} closed connection gracefully.")
                    break
            
            except (ConnectionResetError, ConnectionAbortedError):
                # client forcibly closed smth
                print(f"[WARNING] Client {addr} disconnected forcibly")
                break

            except Exception as e:
                print(f"[ERROR] Unexpected network error for {addr}: {e}")
                break

            buffer += raw_data
            
            # Process all complete JSON objects in the buffer
            while "{" in buffer and "}" in buffer:
                start_index = buffer.find("{")
                bracket_count = 0
                end_index = -1
                
                for i in range(start_index, len(buffer)):
                    if buffer[i] == "{":
                        bracket_count += 1
                    elif buffer[i] == "}":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_index = i + 1
                            break
                
                if end_index == -1: 
                    break # Incomplete message
                
                # Extract and parse ONE message
                message_str = buffer[start_index:end_index]
                try:
                    message = json.loads(message_str)
                    
                    # Logic block
                    if message["type"] == "CONNECT":
                        player_id = addPlayer(message["content"])
                        clients[player_id] = conn
                        conn.send(json.dumps({"type": "ACCEPTED", "id": player_id}).encode())
                    elif message["type"] == "START":
                        global game_started
                        print("The game has started!")
                        if not game_started: startGame()
                    elif message["type"] == "ACTION":
                        action_queue.put((player_id, message["content"]))
                    elif message["type"] == "LEAVE":
                        return # triggers the 'finally' block

                except json.JSONDecodeError:
                    pass # Skip broken fragments
                
                # Clear the processed part of the buffer
                buffer = buffer[end_index:]

    finally:
        if player_id is not None:
            removePlayer(player_id)
            if player_id in clients:
                del clients[player_id]
        conn.close()
        print(f"[CLEANUP] Connection with {addr} closed")


# These are the commands for general game loop on main thread
def processActions():
    # processes actions in a queue style
    pass

def gameLoop():
    global server_running
    print("[RUNNING] Game logic thread started")
    while server_running:
        start_time = time.time()

        if game_started:
            # there's stuff in queue
            while not action_queue.empty():
                pid, action = action_queue.get()
                applyPlayerAction(pid, action)
            
            updateBulletPos()
            detectBulletHits()

            world_state = serializeWorldState()
            for pid, conn in clients.items():
                try:
                    conn.send(world_state.encode())
                except:
                    pass # broken pipe

        sleep_time = TICK_DELAY - (time.time() - start_time) # find time it took to do the math and stuff
        if sleep_time > 0: # if this consistently fails, we're cooked
            time.sleep(sleep_time)
    print("[CLEANUP] Game logic thread stopped")
action_queue = queue.Queue()
clients = {}

def startServer():
    """
    Main server event loop. This is basically our main function
    """

    # Let's initialize our sockets
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
    except socket.error as e:
        print(f"[ERROR] Could not bind to {HOST}:{PORT}. Is the port in use? {e}")
        return
    server.listen()
    server.settimeout(1.0)

    local_ip = get_local_ip()

    print("\n" + "="*50)
    print(f"[ONLINE] Server listening on: {HOST}:{PORT}")
    print(f"[CONNECT] Friends on your Wi-Fi should use: {local_ip}")
    print(f"[CONNECT] You (locally) can use: 127.0.0.1")
    print("="*50 + "\n") 

    # 1. Start game loop in seperate thread (kinda hard to run on main)
    game_thread = threading.Thread(target=gameLoop, daemon=True)
    game_thread.start()

    try:
        while not shutdown_event.is_set():
            try:
                conn, addr = server.accept()

                client_thread = threading.Thread(
                    target = handleClientConnection,
                    args = (conn, addr),
                    daemon = True
                )
                client_thread.start()
            
            except socket.timeout:
                continue
            
    except KeyboardInterrupt:
        # Graceful shutdown
        print("\n [SHUTDOWN] Server is closing...")

    finally:
        global server_running
        server_running = False
        shutdown_msg = json.dumps({"type": "SERVER_SHUTDOWN", "content": "Server is closing"}).encode()
        
        # shotgun
        print(f"[SHUTDOWN] Notifying {len(clients)} players...")
        for pid, conn in list(clients.items()):
            try:
                conn.send(shutdown_msg)
                conn.close()
            except:
                # if we can't reach them, we assume they're gone already
                pass
        server.close()
        time.sleep(0.2)
        print("[SHUTDOWN] All sockets have been closed. Good knowing you!")

def get_local_ip():
    """
    Tries to find actual IP of host
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
            
        s.connect(('8.8.8.8'), 80)
        ip = s.getsockname()[0]
        s.close()

        if ip != '127.0.0.1':
            return ip
    
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return '127.0.0.1'


if __name__ == "__main__":
    try:
        input_host = input(f"Enter Host IP (default {HOST}): ").strip()
        if input_host:
            # is user stupid
            if "." in input_host or input_host == "localhost":
                HOST = input_host
            else:
                print("[!] Invalid IP format. Falling back to 0.0.0.0")
                HOST = "0.0.0.0"
            
        input_port = input(f"Enter Port (default {PORT}): ").strip()
        if input_port:
            p = int(input_port)
            if 1024 <= p <= 65535:
                PORT = p
            else:
                print("[!] Port out of range (1024-65535). Falling back to 5050")
        
        startServer()
    except ValueError:
        print("[ERROR] Port must be a number!")
    
    except KeyboardInterrupt:
        print("\nUser has attempted to kill server")
        sys.exit()
