import json
from pathlib import Path
import socket
import threading
import random
from dataclasses import dataclass, field
from typing import List, Tuple

BASE_DIR = Path(__file__).resolve().parent

# Note to self, please just move this to config so I don't have to edit as much in future
tankComponents_path = BASE_DIR / "config" / "tankComponents.json"
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

print("Hello World: This is client")