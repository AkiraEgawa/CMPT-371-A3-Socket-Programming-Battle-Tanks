Hello to readers: This is what I've gotten so far for how the program will work

# Procedure
1. Clients have some ability on their own side, can create their tanks and stuff privately
2. Client connects to server, sends over json for their tank
3. Host can press start, sends start to server, server sends start to clients
4. Server randomizes spawn pos, places them on map
5. Server sends json of map to client
6. clients begin, actions are sent via json to server
7. In a loop, server uses threads to handle clients, writes to map, server handles the calculation for bullet movement and damage

# Json Message
1. Type
  1. Map: For when server sends map
  2. Action: for client action to send to server
  3. Update: for game updates, every tick
  4. Leave: Client wants to leave, sends a message to server (cleaner than read(client_fd) < 0)
  5. Shutdown: Server sends to client, is keyboard interrupt, forced shutdown on server, tells clients that things are done
  6. State
    1. Game Start
    2. Game End: comes with winner
2. Content, contains whatever content is needed
  1. Map: contains map in 2d array, client displays it using a spritemap (easy)
  2. Action: 1d array of button inputs every tick or 2 tick?
  3. Update: contains map with player and enemy data
  4. Leave: no content
  5. Shutdown: no content
  6. State: no content
