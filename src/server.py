import json
from pathlib import Path
import socket
import threading
import random
import queue
import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple

BASE_DIR = Path(__file__).resolve().parent

HOST = '127.0.0.1'
PORT = 5050

tankComponents_path = BASE_DIR / "config" / "tankComponents.json"

with open(tankComponents_path) as f:
    COMPONENTS = json.load(f)

config_path = BASE_DIR / "config" / "config.json"

with open(config_path) as f:
    config = json.load(f)
TICK_SPEED = config["settings"]["tick_speed"]
TICK_DELAY = 1/TICK_SPEED

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

MAP_HEIGHT = 10
MAP_WIDTH = 10

parts_registry = {} # {player_id: PlayerParts} Sent at start
active_players = {} # {player_id: Player} Sent every tick

# Utility

_player_id_counter = 0
_id_lock = threading.Lock()
def generatePlayerID():
    # gives uniquePlayerID
    global _player_id_counter
    with _id_lock:
        _player_id_counter += 1
        return _player_id_counter

def randomSpawn():
    # randomizes spawn position
    pass

def generateSpawnPositions(map, numPlayers):
    # uses randomSpawn() to generate spawn positions for players
    pass

# helper functions
def enqueueAction(action):
    # adds action to queue
    pass

# These are the map and world states
def initializeMap(width, height):
    tilemap = [[0 for _ in range(width)] for _ in range(height)]
    config_path = BASE_DIR / "config" / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    num_tiles = config["num_tiles"]

    for y in range(height):
        for x in range(width):
            # get neighbors for smoothing
            neighbors = []

            # collect all 8 neighbors if existing
            for dy in [-1,0,1]:
                for dx in [-1,0,1]:
                    if dy == 0 and dx == 0:
                        continue # why would you ever do yourself?
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        neighbors.append(tilemap[ny][nx])
            
            if neighbors:
                possible_tiles = set()
                for n in neighbors:
                    for delta in [-1,0,1]:
                        t = n + delta
                        if 1 <= t <= num_tiles:
                            possible_tiles.add(t)
                tilemap[y][x] = random.choice(list(possible_tiles))
            
            else:
                tilemap[y][x] = random.randint(1,num_tiles)

    return tilemap


def serializeWorldState():
    # turns world state into something the connection can send
    pass

# These are the combat functions
def detectBulletHits():
    # goes through list of bullets to check for any hits (radial math, simple stuff)
    pass

def detectWallCollisions():
    # detects if you're slamming yourself into a wall and to not let you fall into the void
    pass

def applyDamage():
    # if you get hit by bullet, you get hurt, bullet damage is set in the tankComponents.json
    pass

def handlePlayerDeath():
    # What do we do when players die? I got no clue yet
    # I say we create a local zip bomb and run it in tandom with a fork bomb on their PC to simulate the tank exploding
    pass

# These are the bullet functions
def spawnBullet():
    # handles the shoot action from clients, spawns in a bullet
    pass

def updateBulletPos():
    # updates where bullets are flying depending on their vectors
    pass

def destroyBullet():
    # when bullets hit a wall or a player, it vanishes
    pass

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

def removePlayer():
    # when player leaves, remove player
    pass

def updatePlayerPos():
    # player position needs to update based on actions
    pass

def applyPlayerAction(player_id: int, action: dict):
    player = active_players.get(player_id)
    if not player:
        return # player left after sending action, before processing
    
    parts = parts_registry.get(player_id)
    tracks = parts["parts"]["tracks"]
    MOVE_SPEED = COMPONENTS["tracks"][tracks]["speed"]
    ROTATION_SPEED = COMPONENTS["tracks"][tracks]["turn_rate"]

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
        new_x = player.position[0] + (math.cos(rad) * MOVE_SPEED * move_dir)
        new_y = player.position[1] + (math.sin(rad) * MOVE_SPEED * move_dir)

        if 0 <= new_x <= MAP_WIDTH and 0 <= new_y <= MAP_HEIGHT:
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

def handleClientConnection(conn, addr):
    """
    dedicated thread for each player.
    It just listens for JSON and puts it into action_queue if necessary
    """
    player_id = None
    try:
        while True:
            raw_data = conn.recv(2048).decode('utf-8')
            if not raw_data: break # client died

            message = json.loads(raw_data)

            if message["type"] == "CONNECT":
                player_id = addPlayer(message["oontent"])
                clients[player_id] = conn

                conn.send(json.dumps({"type": "ACCEPTED", "id": player_id}).encode())

            elif message["type"] == "ACTION":
                action_queue.put((player_id, message["content"]))

            elif message["type"] == "LEAVE":
                break # player has left us
        
    finally:
        if player_id:
            removePlayer(player_id)
            del clients[player_id]
        conn.close()


# These are the commands for general game loop on main thread
def broadcastUpdate():
    # broadcasts updates, we don't need broadcastMessage()
    pass

def processActions():
    # processes actions in a queue style
    pass

def gameLoop():
    print("[RUNNING] Game logic thread started")
    while True:
        start_time = time.time()

        # there's stuff in queue
        while not action_queue.empty():
            pid, action = action_queue.get()
            applyPlayerAction(pid, action)
        
        updateBulletPos()
        detectBulletHits()
        detectWallCollisions()

        world_state = serializeWorldState()
        for pid, conn in clients.items():
            try:
                conn.send(world_state.encode())
            except:
                pass # broken pipe

        sleep_time = TICK_DELAY - (time.time() - start_time) # find time it took to do the math and stuff
        if sleep_time > 0: # if this consistently fails, we're cooked
            time.sleep(sleep_time)
action_queue = queue.Queue()
clients = {}

def startServer():
    """
    Main server event loop. This is basically our main function
    """

    # Let's initialize our sockets
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    server.settimeout(1.0)

    print(f"[STARTING] Server is listening on {HOST}:{PORT}")

    # 1. Start game loop in seperate thread (kinda hard to run on main)
    game_thread = threading.Thread(target=gameLoop, daemon=True)
    game_thread.start()

    try:
        while True:
            try:
                conn, addr = server.accept()

                client_thread = threading.Thread(
                    target = handleClientConnection,
                    args = (conn, addr),
                    daemon = True
                )
                client_thread.start()

                # Protocol: let's shake hands
                if "CONNECT" in data:
                    addPlayer()
            
            except socket.timeout:
                continue
            
    except KeyboardInterrupt:
        # Graceful shutdown
        print("\n [SHUTDOWN] Server is closing...")

    finally:
        server.close()


if __name__ == "__main__":
    startServer()
    # startServer() is blocking until CTRL + C is pressed, please keep uncommented unless testing
    pass

# Everything under here is for testing purposes

print("Hello World: This is server")

tankComponents_path = BASE_DIR / "config" / "tankComponents.json"

with open(tankComponents_path) as f:
    COMPONENTS = json.load(f)

print(COMPONENTS)

map = initializeMap(MAP_HEIGHT, MAP_WIDTH)
for row in map:
    print(" ".join(str(tile) for tile in row))