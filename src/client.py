import json
from pathlib import Path
import socket
import threading
import random
from dataclasses import dataclass, field
from typing import List, Tuple
import pygame
import sys
import math

@dataclass
class TankParts:
    tracks: str
    armor: str
    sights: str
    barrels: str

BASE_DIR = Path(__file__).resolve().parent

config_path = BASE_DIR / "config" / "config.json"
with open(config_path) as f:
    config = json.load(f)

MAP_WIDTH = config["settings"]["MAX_WIDTH"]
MAP_HEIGHT = config["settings"]["MAX_HEIGHT"]
TILE_SIZE = 800 // MAP_WIDTH

HOST = '127.0.0.1'
PORT = 5050

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Global game state
world_state = {"players": [], "shells": []}
local_map = []
my_id = None
game_running = False

def listen_to_server(client_socket):
    global world_state, local_map, my_id, game_running
    buffer = ""

    while True:
        try:
            chunk = client_socket.recv(8192).decode('utf-8')
            if not chunk: break

            buffer += chunk

            while "{" in buffer and "}" in buffer:
                try:
                    start_index = buffer.find("{")

                    bracket_count = 0
                    end_index = -1

                    for i in range(start_index, len(buffer)):
                        if buffer[i] == "{":
                            bracket_count += 1
                        elif buffer[i] == "}":
                            bracket_count -= 1

                            if bracket_count == 0:
                                end_index = i+1
                                break
                    
                    if end_index == -1:
                        break

                    message_str = buffer[start_index: end_index]
                    message = json.loads(message_str)

                    handle_message(message)

                    buffer = buffer[end_index:]

                except json.JSONDecodeError:
                    buffer = ""
                    break
    
        except Exception as e:
            print(f"Network error: {e}")
            break

def handle_message(message):
    global world_state, local_map, my_id, game_running
    if message["type"] == "ACCEPTED":
        my_id = message["id"]
        print(f"Connected as Player {my_id}.")
    elif message["type"] == "GAME_START":
        local_map = message["content"]["map"]
        game_running = True
    elif message["type"] == "UPDATE":
        world_state["players"] = message["players"]
        world_state["shells"] = message["shells"]

def run_client():
    global game_running
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    threading.Thread(target=listen_to_server, args=(client,), daemon = True).start()

    connect_msg = {
        "type": "CONNECT",
        "content": {
            "tracks": "heavy_tracks",
            "armor": "heavy_armor",
            "sights": "standard_sight",
            "barrels": "standard_barrel"
        }
    }
    client.send(json.dumps(connect_msg).encode())

    while True:
        screen.fill((0,0,0))
        draw_game()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                client.send(json.dumps({"type": "START"}).encode())
            
            if game_running:
                keys = pygame.key.get_pressed()
                active_keys = []
                if keys[pygame.K_w]: active_keys.append("W")
                if keys[pygame.K_s]: active_keys.append("S")
                if keys[pygame.K_a]: active_keys.append("A")
                if keys[pygame.K_d]: active_keys.append("D")
                if keys[pygame.K_SPACE]: active_keys.append("SPACE")
            
                if active_keys:
                    action = {"type": "ACTION", "content": {"keys": active_keys}}
                    client.send(json.dumps(action).encode())

def draw_game():
    if not local_map or not game_running:
        # Draw a "Waiting" screen if map hasn't arrived
        font = pygame.font.SysFont(None, 48)
        img = font.render('WAITING FOR GAME START...', True, (255, 255, 255))
        screen.blit(img, (150, 250))
        return

    # 1. Calculate Scaling (Based on your config 80x100)
    rows = len(local_map)     # 100
    cols = len(local_map[0])  # 80
    # Use the smaller ratio to ensure the whole map fits the screen
    tile_size = min(SCREEN_WIDTH // cols, SCREEN_HEIGHT // rows)

    # 2. Draw Map Tiles
    colors = {
        1: (34, 139, 34),   # Grass
        2: (139, 69, 19),   # Dirt
        3: (100, 100, 100), # Stone
        4: (0, 0, 255),     # Water
        5: (20, 20, 20)     # Wall
    }

    for y, row in enumerate(local_map):
        for x, tile_id in enumerate(row):
            rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, colors.get(tile_id, (0, 0, 0)), rect)

    # 3. Draw Players
    for p in world_state["players"]:
        # Convert server units to screen pixels
        pos_x = int(p["pos"][0] * tile_size)
        pos_y = int(p["pos"][1] * tile_size)
        
        # Color: Green for you, Red for enemies
        color = (0, 255, 0) if p["id"] == my_id else (255, 0, 0)
        
        # Draw Tank Body
        pygame.draw.circle(screen, color, (pos_x, pos_y), int(tile_size * 0.8))
        
        # Draw Barrel (Direction Indicator)
        angle = math.radians(p["rot"])
        end_x = pos_x + math.cos(angle) * tile_size
        end_y = pos_y + math.sin(angle) * tile_size
        pygame.draw.line(screen, (255, 255, 255), (pos_x, pos_y), (end_x, end_y), 3)

    # 4. Draw Shells
    for s in world_state["shells"]:
        shell_x = int(s["pos"][0] * tile_size)
        shell_y = int(s["pos"][1] * tile_size)
        pygame.draw.circle(screen, (255, 255, 255), (shell_x, shell_y), 3)

if __name__ == "__main__":
    run_client()