import eventlet
# MUST run before importing socketio. Without it, eventlet can't schedule around the
# blocking stdlib primitives socketio/engineio use internally, so a single blocking
# call freezes the whole single-threaded hub — which was eating ~700 ms/s of
# unaccounted time and stalling every greenlet (the periodic full-server freezes).
eventlet.monkey_patch()

import socketio
import random
import time
from server_objs.Player import Player
from server_objs.map import Map
# async_handlers=False: run event handlers inline in each client's receive greenlet
# instead of spawning a new greenlet per inbound message. on_input is trivial (queue
# append), so inline is cheaper and avoids per-message greenlet-spawn overhead.
sio = socketio.Server(async_handlers=False)
app = socketio.WSGIApp(sio)

playerDict = {}

map = Map()


def get_states():
    # Full per-player state, used only for the join events (init/player) where the
    # client needs id + color. The deque isn't JSON-serializable, so drop it.
    player_states = {}
    for k, v in playerDict.items():
        state = dict(v.__dict__)
        state.pop("input_queue", None)
        player_states[k] = state

    return player_states


def get_snapshot():
    # Minimal per-player state for the 60->30 Hz broadcast: only the fields the
    # client reads each frame (remote interpolation + local reconcile). Keeping
    # this small is what lets the host broadcast to several clients without the
    # loop falling behind and starving the input queue.
    snap = {}
    for k, v in playerDict.items():
        snap[k] = {
            "pos": v.pos,
            "vel": v.vel,
            "facing": v.facing,
            "dashCount": v.dashCount,
            "hit": v.hit,
            "colliding": v.colliding,
            "cooldown": v.cooldown,
            "last_ack": v.last_ack,
        }
    return snap



@sio.event
def connect(sid, environ):
    playerDict[sid] = Player(sid)
    sio.emit("id", sid, room=sid) # sending connecting player their ID

    player_states = get_states()

    print(playerDict[sid].__dict__)

    sio.emit("init", player_states, room=sid) # sending connecting player all the current players
    sio.emit("player", player_states[sid], skip_sid=sid) # Tell every other player the new player has joined
    sio.emit("load_map", map.map, room=sid) # send map
    print("connected, ", sid)


@sio.event
def disconnect(sid):
    playerDict.pop(sid)
    sio.emit("remove", sid, skip_sid=sid)
    print("Disconnected, ", sid)


# Cap the per-player input backlog so a lagging client can't build unbounded
# latency; on overflow we drop the oldest (a rare, small correction).
MAX_INPUT_QUEUE = 15
# Most physics sub-ticks per game_loop iteration (>= the queue cap so a backlog
# drains fully in one pass).
MAX_STEPS_PER_TICK = 15
# Snapshot broadcast rate. The simulation runs at 60 Hz but we only send ~30
# snapshots/s; clients interpolate remotes and reconcile the local player between
# them. Broadcasting every tick to every client is what overloads the host.
SNAPSHOT_HZ = 20
SNAPSHOT_INTERVAL = 1.0 / SNAPSHOT_HZ

# inbound-rate diagnostics: how many input messages/s arrive and how long on_input
# itself costs. If msgs/s is ~40 but the loop still drowns, the cost is engineio's
# websocket frame handling (stack/Pi limit), not our code.
_in_count = 0
_in_time = 0.0
_in_t = time.time()


@sio.on("input")
def on_input(sid, data):
    # The client batches several per-tick inputs into one message to keep the
    # message rate low — a 60 msg/s stream from each client can swamp the server
    # and stall snapshot delivery once 2+ players connect. Each per-tick input is
    # still queued individually and drained one physics tick at a time in
    # game_loop. Accept either a batch (list) or a single dict.
    global _in_count, _in_time, _in_t
    t0 = time.time()

    player = playerDict.get(sid)
    if player is not None:
        if isinstance(data, dict):
            data = [data]
        for inp in data:
            player.input_queue.append(inp)
        while len(player.input_queue) > MAX_INPUT_QUEUE:
            player.input_queue.popleft()

    _in_count += 1
    _in_time += time.time() - t0
    if t0 - _in_t >= 1.0:
        print(f"[in] {_in_count} msgs/s | on_input={_in_time * 1000:.0f}ms/s")
        _in_count = 0
        _in_time = 0.0
        _in_t = t0


def game_loop():
    # Hold the tick rate at a true 60 Hz wall-clock. eventlet.sleep(1/60) by itself
    # only sleeps *after* the tick work finishes, so on a Pi the real rate drops to
    # ~40-50 Hz and the client's 60 Hz prediction drifts ahead.
    tick_interval = 1.0 / 60
    next_tick = time.time()
    # --- diagnostics: with emit moved out, ticks/s should hold ~60 even with 2 players ---
    diag_t = time.time()
    diag_ticks = 0
    diag_maxq = 0
    diag_sim_total = 0.0
    diag_sim_max = 0.0
    while True:
        # Drain every queued input this iteration, one physics tick each, so each
        # player's sim advances exactly by the inputs received — no collapsing
        # (snaps backward) and no extra ticks (snaps forward). A player with an
        # empty queue is simply not advanced this sub-tick; it catches up exactly
        # when its next batch arrives.
        diag_ticks += 1
        raw_max_q = 0
        for player in playerDict.values():
            raw_max_q = max(raw_max_q, len(player.input_queue))
        diag_maxq = max(diag_maxq, raw_max_q)
        steps = min(raw_max_q, MAX_STEPS_PER_TICK)

        sim_start = time.time()
        for _ in range(steps):
            for k, player in playerDict.items():
                if player.apply_net_input():
                    player.update(map.rects, playerDict)
                    player.dash()

            for player in playerDict.values():
                if player.pos[1] > 1200:
                    player.pos[1] = 0
                    player.pos[0] = 50
        sim_dt = time.time() - sim_start
        diag_sim_total += sim_dt
        diag_sim_max = max(diag_sim_max, sim_dt)

        # Diagnostics. ticks/s = real loop rate. sim ms/s = CPU actually spent
        # simulating. The key tell: if ticks/s is low while sim ms/s is SMALL, the
        # eventlet hub is being starved by socket I/O (inbound messages), not the
        # sim; if sim ms/s is LARGE, the simulation itself is the bottleneck.
        now2 = time.time()
        if now2 - diag_t >= 1.0:
            print(f"[loop] {diag_ticks} ticks/s | max_q={diag_maxq} | "
                  f"sim={diag_sim_total * 1000:.0f}ms/s (max {diag_sim_max * 1000:.1f}ms) | "
                  f"players={len(playerDict)}")
            diag_t = now2
            diag_ticks = 0
            diag_maxq = 0
            diag_sim_total = 0.0
            diag_sim_max = 0.0

        next_tick += tick_interval
        sleep_time = next_tick - time.time()
        if sleep_time > 0:
            eventlet.sleep(sleep_time)
        else:
            # We're behind — work took longer than a tick. Reset the schedule so we
            # don't enter a catch-up spiral, and yield to other greenlets.
            next_tick = time.time()
            eventlet.sleep(0)
    
    
def broadcast_loop():
    # Send trimmed snapshots at a fixed rate, on its OWN greenlet. If an emit blocks
    # (slow client / full TCP send buffer), only this greenlet waits — game_loop
    # keeps simulating and draining inputs, so the local player never rubber-bands.
    next_send = time.time()
    diag_t = time.time()
    diag_emits = 0
    diag_emit_total = 0.0
    diag_emit_max = 0.0
    while True:
        emit_start = time.time()
        sio.emit("state", {"t": time.time(), "players": get_snapshot()})
        emit_dt = time.time() - emit_start
        diag_emits += 1
        diag_emit_total += emit_dt
        diag_emit_max = max(diag_emit_max, emit_dt)

        now2 = time.time()
        if now2 - diag_t >= 1.0:
            print(f"[bcast] {diag_emits} emits/s | "
                  f"emit={diag_emit_total * 1000:.0f}ms/s (max {diag_emit_max * 1000:.1f}ms)")
            diag_t = now2
            diag_emits = 0
            diag_emit_total = 0.0
            diag_emit_max = 0.0

        next_send += SNAPSHOT_INTERVAL
        sleep_time = next_send - time.time()
        if sleep_time > 0:
            eventlet.sleep(sleep_time)
        else:
            next_send = time.time()
            eventlet.sleep(0)


if __name__ == "__main__":
    # async_mode should print 'eventlet'. If it says 'threading', that's a second
    # problem — socketio didn't pick up eventlet and won't cooperate with the loop.
    print("Starting | socketio async_mode =", sio.async_mode)
    eventlet.spawn(game_loop)
    eventlet.spawn(broadcast_loop)
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)
