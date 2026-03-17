import json
from pathlib import Path
import socket
import threading
import random
from dataclasses import dataclass, field
from typing import List, Tuple


BASE_DIR = Path(__file__).resolve().parent

HOST = '127.0.0.1'
PORT = 5050

TICK_SPEED = 50
TICK_DELAY = 1/TICK_SPEED

@dataclass
class PlayerParts:
    id: int
    parts: List[str]

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

# Utility
def generatePlayerID():
    pass

def randomSpawn():
    pass

def generateSpawnPositions():
    pass

# helper functions
def enqueueAction():
    pass

def getActionsForTick():
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

# likely won't need this
def updateWorld():
    pass

def serializeWorldState():
    pass

# These are the combat functions
def detectBulletHits():
    pass

def detectWallCollisions():
    pass

def applyDamage():
    pass

def handlePlayerDeath():
    pass

# These are the bullet functions
def spawnBullet():
    pass

def updateBulletPos():
    pass

def destroyBullet():
    pass

# These are the player functions
def addPlayer():
    pass

def removePlayer():
    pass

def spawnPlayers():
    pass

def updatePlayerPos():
    pass

def applyPlayerAction():
    pass

# These are the networking functions
def broadcastMessage():
    pass

def sendMessage():
    pass

def parseMessage():
    pass

def receiveMessage():
    pass

def handleClientConnection():
    pass


# These are the commands for general game loop on main thread
def broadcastUpdate():
    pass

def processActions():
    pass

def gameLoop():
    pass

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

    try:
        while True:
            try:
                conn, addr = server.accept()
                data = conn.recv(1024).decode('utf-8')

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