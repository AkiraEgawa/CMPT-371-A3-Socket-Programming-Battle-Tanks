# **CMPT 371 A3 Socket Programming `Battle Tanks`**

**Course:** CMPT 371 \- Data Communications & Networking  
**Instructor:** Mirza Zaeem Baig  
**Semester:** Spring 2026 

## **Group Members**

| Name | Student ID | Email |
| :---- | :---- | :---- |
| Lucian Chen | 301588981 | lca193@sfu.ca |
| Tristan Liu | 301567578 | tristan_liu@sfu.ca |

## **1\. Project Overview & Description**

This project is a multplayer tank battle game, where users can build their own tanks and participate in a battle royale style battle using Python's Socket API (TCP). Players can all join the same lobby then start the game, fighting against each other in real time with tanks they customize beforehand. The server handles the game logic, game state calculations, and damage checks to prevent cheating. This renders the client essentially as a glorified television, in which I implemented LERP (Linear Interpolation), and client-side prediction in order for a smoother experience for the player.

## **2\. System Limitations & Edge Cases**
As required by the project specifications, we have identified and handled (or defined) the following limitations and potential issues within our application scope:

* **Handling Multiple Clients Concurrently**
    * *Solution:* We utilized Python's threading module, with each client connecting causing another thread to be opened. They will be assigned a userID that is sent to them via a packet with "type":"ACCEPTED" and can then track their own positions in a fog of war style map
    * *Limitation:* Thread creation is limited by system resources, with my PC being limited to around 500 threads. This however, should never be an issue as our map isn't large enough to support 500 players and would require the user to edit config.json
* **TCP Stream Buffering**
    * *Solution:* TCP is a continuous byte stream, so not everything arrives at once, and some messages can be mashed together if sent too fast. As such, we implemented a fix on both client and server end by just using bracket-counting to seperate the messages.
        * *Bracket-Counting:* Essentially, every open bracket adds 1 to the bracket count, and every closed bracket subtracts one. Upon hitting a closed bracket, we check if the count is 0. If it is, then we've reached a full message and pop it out to process.
* **Input Validation & Security*
    * *Limitation:* The client side uses many try/excepts enclosed within each other to capture every possible error. As we don't trust users to not intercept packets and send fake results over, all math is done of server side. However, malicious users can still intercept the message and delete the content, as .get() can not retrieve a NoneType.
* **Victory Checks**
    * *Limitation:* Our victory check works by checking if there's only one player left after a player death or a player disconnecting either by using ESC or by using a system interrupt to forcefully shut down their client. However, a crash can still occur if a player manages to leave between the check of len(active_players) == 1 succeeding and the victory message being sent out. This however, should also not be a major issue, as with the last player leaving the server, the server should close either way

## **3\. Video Demo**
[**TODO**]

## **4\. Prerequisites (Fresh Environment)**

To run this project you need:
* **Python 3.10** or higher
* **Pygame Library**: This is required for the client-side GUI and rendering
* **Standard Libraries**: Uses `socket`, `threading`, `json`, `math`, and `pathlib` which are all included within Python

[IMPORTANT]
**External Library Installation**
Before running the client, you must install Pygame via pip:
```Bash
pip install pygame
```