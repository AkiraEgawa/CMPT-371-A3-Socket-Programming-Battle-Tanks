import json

print("Hello World: This is server")

with open("tankComponents.json") as f:
    COMPONENTS = json.load(f)

print(COMPONENTS)