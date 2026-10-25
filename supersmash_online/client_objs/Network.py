import pygame
from client_objs.Player import Player
import socketio

from collections import deque
import time

state_buffer = deque(maxlen=20)


global map

sio = socketio.Client()

client_id = ""
playerDict = {}
map = []

clock_offset = None
latest_local_state = None
latest_local_state_seq = 0

# snapshot-rate diagnostics
_snap_count = 0
_snap_t = time.time()


def connect_to_server():
    # Force WebSocket: the default polling-then-upgrade can leave a high-rate input
    # stream stuck on HTTP long-polling, which batches terribly and adds latency.
    sio.connect("http://192.168.1.149:5000", transports=["websocket"])


def server_time_now():
    if clock_offset is None:
        return None
    return time.time() + clock_offset


@sio.event
def connect():
    # Confirm we got a websocket (not stuck on long-polling, which would lag badly).
    print("connected, transport =", sio.transport())

@sio.event
def disconnect():
    print("disconnected, ")


@sio.on("remove")
def remove(sid):
    playerDict.pop(sid)


@sio.on("id")
def getID(data):
    global client_id
    client_id = data
    print(client_id)


@sio.on("init")
def getCurrentPlayers(data):
    global playerDict
    for k, v in data.items():
        playerDict[k] = Player(v["pos"], v["id"])
        playerDict[k].color = v["color"]
    print("added all current players", playerDict)


@sio.on("player")
def addNewPlayer(data):
    playerDict[data["id"]] = Player(data["pos"], data["id"])
    playerDict[data["id"]].color = data["color"]
    print("added new player", playerDict)


@sio.on("load_map")
def load_map(data):
    global map
    map = data


@sio.on("state")
def update(data):
    global clock_offset, latest_local_state, latest_local_state_seq
    global _snap_count, _snap_t

    _snap_count += 1
    nowx = time.time()
    if nowx - _snap_t >= 1.0:
        print(f"[net] {_snap_count} snapshots/s received")
        _snap_count = 0
        _snap_t = nowx

    server_t = data["t"]
    players = data["players"]

    local_t = time.time()
    observed_offset = server_t - local_t
    if clock_offset is None:
        clock_offset = observed_offset
    else:
        clock_offset = 0.95 * clock_offset + 0.05 * observed_offset

    state_buffer.append((server_t, players))

    if client_id and client_id in players:
        latest_local_state = players[client_id]
        latest_local_state_seq += 1
