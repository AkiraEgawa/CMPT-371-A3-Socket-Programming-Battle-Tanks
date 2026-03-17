import json
from pathlib import Path
import socket
import threading
import random
BASE_DIR = Path(__file__).resolve().parent

HOST = '127.0.0.1'
PORT = 5050

TICK_SPEED = 50
TICK_DELAY = 1/TICK_SPEED

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

def runServer():
    pass

print("Hello World: This is server")

tankComponents_path = BASE_DIR / "config" / "tankComponents.json"

with open(tankComponents_path) as f:
    COMPONENTS = json.load(f)

print(COMPONENTS)

map = initializeMap(MAP_HEIGHT, MAP_WIDTH)
for row in map:
    print(" ".join(str(tile) for tile in row))