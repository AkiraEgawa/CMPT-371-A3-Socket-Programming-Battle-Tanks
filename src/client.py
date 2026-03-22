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

HOST = '127.0.0.1'
PORT = 5050

target_ip = "127.0.0.1"
target_port = "5050"
active_input = None

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Global game state
world_state = {"players": [], "shells": []}
local_map = []
my_id = None
game_running = False

VISIBLE_RADIUS = 8
TILE_SIZE = 50
smooth_positions = {}



parts_registry = {}

MENU = "menu"
GARAGE = "garage"
GAME = "game"
current_ui_state = MENU

last_cam_pos = [0,0]

selected_parts = {
    "tracks": "heavy_tracks",
    "armor": "heavy_armor",
    "sights": "standard_sight",
    "barrels": "standard_barrel"
}

with open(BASE_DIR / "config" / "tankComponents.json") as f:
    COMPONENTS = json.load(f)

def draw_button(text, x, y, w, h, color, hover_color):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    is_clicked = False

    if x + w > mouse[0] > x and y + h > mouse[1] > y:
        pygame.draw.rect(screen, hover_color, (x, y, w, h))
        if click[0] == 1:
            is_clicked = True
    else:
        pygame.draw.rect(screen, color, (x, y, w, h))
    
    font = pygame.font.SysFont(None, 30)
    text_surf = font.render(text, True, (255, 255, 255))
    screen.blit(text_surf, (x + w/2 - text_surf.get_width()/2, y + h/2 - text_surf.get_height()/2))
    
    return is_clicked

def draw_main_menu():
    global target_ip, target_port, active_input
    screen.fill((20, 20, 20))


    # Title
    title_font = pygame.font.SysFont(None, 80)
    title = title_font.render("BATTLE TANKS", True, (200, 0, 0))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))

    font = pygame.font.SysFont(None, 30)

    # IP Input Box
    ip_label = font.render("Server IP:", True, (255,255,255))
    screen.blit(ip_label, (200,180))

    # if I'm typing in, please make it visible
    ip_color = (100,100,255) if active_input == "IP" else (60,60,60)
    if draw_button(target_ip, 300, 170, 250, 40, ip_color, (80,80,150)):
        active_input = "IP"

    # Port Input Box
    port_label = font.render("Port:", True, (255, 255, 255))
    screen.blit(port_label, (200, 230))
    port_color = (100, 100, 255) if active_input == "PORT" else (60, 60, 60)
    if draw_button(target_port, 300, 220, 100, 40, port_color, (80, 80, 150)):
        active_input = "PORT"


    if draw_button("JOIN SERVER", 300, 250, 200, 50, (50, 50, 50), (100, 100, 100)):
        return "CONNECT"
    if draw_button("BUILD TANK", 300, 320, 200, 50, (50, 50, 50), (100, 100, 100)):
        return "GO_GARAGE"
    if draw_button("QUIT", 300, 390, 200, 50, (150, 0, 0), (200, 0, 0)):
        pygame.quit()
        sys.exit()
    return None

def draw_garage():
    global selected_parts
    screen.fill((30, 30, 30))
    
    y_offset = 150
    # Loop through the JSON categories to make selection buttons
    for category, options in COMPONENTS.items():
        font = pygame.font.SysFont(None, 35)
        cat_text = font.render(f"{category.upper()}: {selected_parts[category]}", True, (255, 255, 0))
        screen.blit(cat_text, (100, y_offset))
        
        # Draw small buttons for each part in that category
        x_offset = 350
        for part_name in options.keys():
            if draw_button(part_name, x_offset, y_offset - 10, 150, 35, (70, 70, 70), (120, 120, 120)):
                selected_parts[category] = part_name
            x_offset += 160
        y_offset += 60

    if draw_button("BACK TO MENU", 300, 500, 200, 50, (100, 100, 100), (150, 150, 150)):
        return "GO_MENU"
    return None

def listen_to_server(client_socket):
    global world_state, local_map, my_id, game_running, parts_registry, COMPONENTS
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
    global world_state, local_map, my_id, game_running, parts_registry
    if message["type"] == "ACCEPTED":
        my_id = message["id"]
        print(f"Connected as Player {my_id}.")
    elif message["type"] == "GAME_START":
        local_map = message["content"]["map"]
        parts_registry = message["content"]["registry"]
        game_running = True
    elif message["type"] == "UPDATE":
        world_state["players"] = message["players"]
        world_state["shells"] = message["shells"]

def run_client():
    global current_ui_state, game_running, my_id, smooth_positions, parts_registry, selected_parts, target_ip, target_port, active_input
    client = None

    while True:
        screen.fill((0,0,0))

        # --- 1. HANDLE INPUT & LOGIC ---
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # --- MY TYPING LOGIC ---
            if current_ui_state == MENU and active_input is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        if active_input == "IP": target_ip = target_ip[:-1]
                        else: target_port = target_port[:-1]
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                        active_input = None
                    else:
                        # add typed character and limit length so we don't have weirdos spamming
                        if active_input == "IP" and len(target_ip) < 15:
                            target_ip += event.unicode
                        elif active_input == "PORT" and len(target_port) < 5:
                            target_port += event.unicode

            # Start Game Command
            if current_ui_state == GAME and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if client:
                    client.send(json.dumps({"type": "START"}).encode())

        # --- 2. UI STATE MACHINE ---
        if current_ui_state == MENU:
            action = draw_main_menu()
            if action == "GO_GARAGE":
                current_ui_state = GARAGE
            elif action == "CONNECT":
                
                try:
                    p = int(target_port)
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.settimeout(5.0)
                    client.connect((target_ip, p))
                    client.settimeout(None)
                    threading.Thread(target=listen_to_server, args=(client,), daemon=True).start()
                    # Send ACTUAL selected parts from garage
                    connect_msg = {"type": "CONNECT", "content": selected_parts}
                    client.send(json.dumps(connect_msg).encode())
                    current_ui_state = GAME
                except Exception as e:
                    print(f"Connection failed: {e}")
                    current_ui_state = MENU

        elif current_ui_state == GARAGE:
            action = draw_garage()
            if action == "GO_MENU":
                current_ui_state = MENU

        elif current_ui_state == GAME:
            draw_game()
            
            # --- MOVEMENT & PREDICTION ---
            if game_running and my_id in smooth_positions:
                str_id = str(my_id)
                if str_id in parts_registry:
                    active_keys = []
                    my_parts = parts_registry[str_id]
                    track_name = my_parts["tracks"]
                    
                    stats = COMPONENTS["tracks"][track_name]
                    current_move_speed = stats["speed"]
                    
                    move_dir = 0
                    if keys[pygame.K_w]: active_keys.append("W"); move_dir = 1
                    if keys[pygame.K_s]: active_keys.append("S"); move_dir = -1
                    if keys[pygame.K_a]: active_keys.append("A")
                    if keys[pygame.K_d]: active_keys.append("D")
                    if keys[pygame.K_SPACE]: active_keys.append("SPACE")

                    if move_dir != 0:
                        me = next((p for p in world_state["players"] if p["id"] == my_id), None)
                        if me:
                            rad = math.radians(me["rot"])
                            smooth_positions[my_id][0] += math.cos(rad) * current_move_speed * move_dir
                            smooth_positions[my_id][1] += math.sin(rad) * current_move_speed * move_dir
                    
                    if active_keys and client:
                        try:
                            client.send(json.dumps({"type": "ACTION", "content": {"keys": active_keys}}).encode())
                        except: pass

        pygame.display.flip()
        clock.tick(60)

def draw_game():
    global last_cam_pos, smooth_positions
    if not local_map or not game_running:
        # Draw "Waiting" screen
        font = pygame.font.SysFont(None, 48)
        img = font.render('WAITING FOR GAME START...', True, (255, 255, 255))
        screen.blit(img, (150, 250))
        return

    # --- 1. UPDATE SMOOTH POSITIONS (LERP) ---
    # We do this for ALL players before drawing anything
    for p in world_state["players"]:
        pid = p["id"]
        target_x, target_y = p["pos"]

        if pid not in smooth_positions:
            smooth_positions[pid] = [target_x, target_y]

        if pid == my_id:
            curr_x, curr_y = smooth_positions[pid]
            smooth_positions[pid][0] += (target_x - curr_x) * 0.2
            smooth_positions[pid][1] += (target_y - curr_y) * 0.2
        
        else:
            curr_x, curr_y = smooth_positions[pid]
            smooth_positions[pid][0] += (target_x - curr_x) * 0.2
            smooth_positions[pid][1] += (target_y - curr_y) * 0.2

    # --- 2. CAMERA CALCULATION ---
    me = next((p for p in world_state["players"] if p["id"] == my_id), None)
    
    if me:
        # Use the SMOOTH position for the camera to prevent camera jitter
        player_x, player_y = smooth_positions[my_id]
        last_cam_pos = [player_x, player_y]
        is_alive = True
    else:
        player_x, player_y = last_cam_pos
        is_alive = False

    offset_x = (SCREEN_WIDTH // 2) - (player_x * TILE_SIZE)
    offset_y = (SCREEN_HEIGHT // 2) - (player_y * TILE_SIZE)

    # --- 3. DRAW MAP ---
    start_x = max(0, int(player_x - VISIBLE_RADIUS - 1))
    end_x = min(len(local_map[0]), int(player_x + VISIBLE_RADIUS + 2))
    start_y = max(0, int(player_y - VISIBLE_RADIUS - 1))
    end_y = min(len(local_map), int(player_y + VISIBLE_RADIUS + 2))

    colors = {1: (34, 139, 34), 2: (139, 69, 19), 3: (100, 100, 100), 4: (0, 0, 255), 5: (20, 20, 20)}

    for y in range(start_y, end_y):
        for x in range(start_x, end_x):
            rect = pygame.Rect(x * TILE_SIZE + offset_x, y * TILE_SIZE + offset_y, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, colors.get(local_map[y][x], (0, 0, 0)), rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1) # Grid

    # --- 4. DRAW SHELLS ---
    for s in world_state["shells"]:
        sx = s["pos"][0] * TILE_SIZE + offset_x
        sy = s["pos"][1] * TILE_SIZE + offset_y
        if 0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT:
            pygame.draw.circle(screen, (255, 255, 0), (int(sx), int(sy)), 4)

    # --- 5. DRAW PLAYERS (FIXED: USING SMOOTH POSITIONS) ---
    for p in world_state["players"]:
        pid = p["id"]
        # CRITICAL FIX: Use the lerped coordinates for drawing
        px_smooth, py_smooth = smooth_positions[pid]
        
        px = px_smooth * TILE_SIZE + offset_x
        py = py_smooth * TILE_SIZE + offset_y
        
        if -TILE_SIZE <= px <= SCREEN_WIDTH + TILE_SIZE and -TILE_SIZE <= py <= SCREEN_HEIGHT + TILE_SIZE:
            color = (0, 255, 0) if pid == my_id else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(px), int(py)), 15)
            
            # Draw Barrel
            angle = math.radians(p["rot"])
            pygame.draw.line(screen, (255, 255, 255), (px, py), 
                             (px + math.cos(angle)*25, py + math.sin(angle)*25), 3)

    # --- 6. FOG & DEATH OVERLAY ---
    fog_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    fog_surface.fill((0, 0, 0, 220)) 
    # Hole of light
    pygame.draw.circle(fog_surface, (0, 0, 0, 0), (SCREEN_WIDTH//2, SCREEN_HEIGHT//2), VISIBLE_RADIUS * TILE_SIZE)
    screen.blit(fog_surface, (0, 0))

    if not is_alive:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((100, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        font = pygame.font.SysFont(None, 72)
        text = font.render("TANK DESTROYED", True, (255, 255, 255))
        screen.blit(text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 36))

if __name__ == "__main__":
    try:
        run_client()
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down client...")
    finally:
        pygame.quit()
        sys.exit()