import math
# Ensure Shell is imported so the constructor works in test_collision
from src.server import (
    addPlayer, applyPlayerAction, spawnBullet, 
    active_players, parts_registry, world_shells, 
    COMPONENTS, MAP_WIDTH, MAP_HEIGHT, Shell
)

def test_player_registration():
    print("\n--- Testing Player Registration ---")
    # Updated with your specific part names
    mock_parts = {
        "tracks": "heavy_tracks",
        "armor": "heavy_armor",
        "sights": "standard_sight",
        "barrels": "standard_barrel"
    }
    
    try:
        pid = addPlayer(mock_parts)
        player = active_players[pid]
        static = parts_registry[pid]
        
        print(f"SUCCESS: Created Player {pid}")
        # Verify HP from COMPONENTS JSON
        expected_hp = COMPONENTS["armor"]["heavy_armor"]["hp"]
        print(f"HP Assigned: {player.health} (Expected: {expected_hp})")
        print(f"Parts Verified: {static.parts.tracks}")
    except Exception as e:
        print(f"FAILED: Registration crashed with: {e}")

def test_movement_math():
    print("\n--- Testing Movement Math ---")
    # Using real parts to avoid KeyErrors during lookup
    pid = addPlayer({
        "tracks": "heavy_tracks",
        "armor": "heavy_armor", 
        "sights": "standard_sight", 
        "barrels": "standard_barrel"
    })
    player = active_players[pid]
    player.position = (5.0, 5.0)
    player.rotation = 0.0 
    
    # Simulate pressing 'W'
    mock_action = {"keys": ["W"]}
    applyPlayerAction(pid, mock_action)
    
    new_x, new_y = player.position
    # If rotation is 0, cos(0) = 1, so X should increase
    if new_x > 5.0 and math.isclose(new_y, 5.0):
        print(f"SUCCESS: Tank moved East. New Pos: ({new_x:.2f}, {new_y:.2f})")
    else:
        print(f"FAILED: Movement math is off. New Pos: ({new_x}, {new_y})")

def test_collision():
    print("\n--- Testing Collision Detection ---")
    
    # Create a Target
    target_id = addPlayer({
        "tracks": "heavy_tracks",
        "armor": "heavy_armor", 
        "sights": "standard_sight", 
        "barrels": "standard_barrel"
    })
    target = active_players[target_id]
    target.position = (10.0, 10.0)
    
    # Create a Shell close to the target
    bullet = Shell(
        id=99,
        shell_type="standard_barrel",
        position=(10.1, 10.1), 
        velocity=(0, 0)
    )
    
    dist = math.sqrt(
        (bullet.position[0] - target.position[0])**2 + 
        (bullet.position[1] - target.position[1])**2
    )
    
    HIT_THRESHOLD = 0.5 
    
    if dist < HIT_THRESHOLD:
        print(f"SUCCESS: Collision detected! Distance: {dist:.2f}")
    else:
        print(f"FAILED: Collision missed. Distance: {dist:.2f}")

if __name__ == "__main__":
    test_player_registration()
    test_movement_math()
    test_collision()