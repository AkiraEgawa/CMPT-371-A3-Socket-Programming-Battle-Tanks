import math
from src import server

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
    print("\n--- Testing Collision Detection (Live Function) ---")
    
    # 1. Clear the environment
    server.world_shells = []
    server.active_players = {}
    
    # 2. Create a Target at (10.0, 10.0)
    target_id = addPlayer({
        "tracks": "heavy_treads", # Fixed string based on your previous KeyError
        "armor": "heavy_armor", 
        "sights": "standard_sight", 
        "barrels": "standard_barrel"
    })
    server.active_players[target_id].position = (10.0, 10.0)
    
    # 3. Add a Shell to the global world_shells list
    # We place it at (10.2, 10.2), which is within the 0.5 threshold
    hit_shell = Shell(
        id=99,
        shell_type="standard_barrel",
        position=(10.2, 10.2),
        velocity=(0, 0)
    )
    server.world_shells.append(hit_shell)

    # 4. Call the ACTUAL server function
    server.detectBulletHits()
    
    # 5. Verify results
    # If the bullet hit, it should have been removed from the list
    if len(server.world_shells) == 0:
        print("SUCCESS: detectBulletHits() found the hit and removed the shell.")
    else:
        # If it failed, let's see why
        bullet_pos = server.world_shells[0].position
        target_pos = server.active_players[target_id].position
        print(f"FAILED: Shell still exists. Shell: {bullet_pos}, Target: {target_pos}")

def test_bullet_physics_flight():
    print("\n--- Testing Bullet Physics & Flight ---")
    global world_shells
    server.world_shells = [] # Reset for clean test

    # 1. Manually create a shell at (0, 0) 
    # Velocity is (1.0, 0.5) -> It should move 1 unit Right and 0.5 units Up per tick
    test_shell = Shell(
        id=777,
        shell_type="test_round",
        position=(0.0, 0.0),
        velocity=(1.0, 0.5)
    )
    server.world_shells.append(test_shell)

    # 2. Simulate 3 Ticks of the game loop
    from src.server import updateBulletPos
    for i in range(3):
        updateBulletPos()
        print(f"Tick {i+1}: Position is now {test_shell.position}")

    # 3. Verify final position
    # After 3 ticks, x should be 3.0 and y should be 1.5
    final_x, final_y = test_shell.position
    if math.isclose(final_x, 3.0) and math.isclose(final_y, 1.5):
        print("SUCCESS: Bullet trajectory math is perfect.")
    else:
        print(f"FAILED: Expected (3.0, 1.5), got ({final_x}, {final_y})")

if __name__ == "__main__":
    test_player_registration()
    test_movement_math()
    test_collision()
    test_bullet_physics_flight()
    test_collision()