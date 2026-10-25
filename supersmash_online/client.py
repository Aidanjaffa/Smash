import pygame
pygame.init()

import time
import random
from collections import deque
import socketio
from client_objs.Network import *
import client_objs.Network as Network
from client_objs.Network import sio, playerDict, map, connect_to_server, update
from client_objs.Player import Player
import client_objs.Camera as Camera
from client_objs.menus import Pause


width, height = 1200, 720
screen = pygame.display.set_mode((width, height))
surf = pygame.Surface((1200, 720))

clock = pygame.time.Clock()

camera = Camera.Camera()

dirt = pygame.transform.scale(pygame.image.load("assets/dirt.png").convert_alpha(), (40, 40))
background = pygame.transform.scale(pygame.image.load("assets/Lv1_BG1.png").convert_alpha(), (width * 0.9, height * 0.9))

fonts = [pygame.font.Font("assets/joystix.otf", 19), pygame.font.Font("assets/joystix.otf", 35)]

connect_to_server()

def draw_map():
    y = 0
    for row in Network.map:
        x = 0
        for block in row:
            if block == "c" or block == "1":
                surf.blit(dirt, (x * 40 + camera.scroll[0], y * 40 + camera.scroll[1]))
            x += 1
        y += 1


def build_map_rects(grid):
    rects = []
    for y, row in enumerate(grid):
        for x, block in enumerate(row):
            if block == "1":
                rects.append(pygame.Rect(x * 40, y * 40, 40, 40))
    return rects


# How far behind the server clock we render remote players. Larger = more jitter
# absorption, more visible lag for other players. With a steady 60 Hz server tick,
# 80 ms covers ~5 ticks of snapshots — enough margin for typical network jitter.
# Drop to ~0.05 if your link to the host is very clean; raise to 0.12+ if you see
# remote players freeze briefly when packets bunch up.
INTERP_DELAY = 0.08

# Local prediction runs at a fixed wall-clock rate, decoupled from render fps.
# Must match the server's tick rate or the local player will drift relative to where
# the server (and therefore other clients) thinks they are.
PHYSICS_DT = 1.0 / 60
MAX_PHYSICS_STEPS_PER_FRAME = 5

run = True

scale = [1200 * 1.5, 720 * 1.5]

fullscreen = False
def toggle_fullscreen(fullscreen):
    if not fullscreen:
        fullscreen = True
        print("big")
        return pygame.display.set_mode((width, height), pygame.FULLSCREEN), fullscreen
    else:
        print("small")
        fullscreen = False
        return pygame.display.set_mode((width, height)), fullscreen


pause = False

map_rects = None
next_predict_time = None

# Local-player input/prediction state. Held movement keys are sampled once per
# physics tick; dash is a one-shot. Each sampled input gets a sequence number,
# is buffered for replay, and is sent to the server.
tick_seq = 0
pending_inputs = deque()
held = {"left": False, "right": False, "jump": False}
dash_pressed = False

# Per-tick inputs are accumulated and sent in batches every SEND_EVERY frames to
# keep the message rate low. A 60 msg/s stream per client can swamp the server
# and starve snapshot delivery once 2+ players connect; batching cuts that ~3x
# while still sending every per-tick input (the server drains them one at a time).
outbound = []
SEND_EVERY = 3
frame_count = 0

while run:
    # Build collision rects once the map has arrived from the server
    if map_rects is None and Network.map:
        map_rects = build_map_rects(Network.map)

    local = playerDict.get(Network.client_id) if Network.client_id else None

    # --- Local player: sample input at a fixed 60 Hz, reconcile against server ---
    # Physics is decoupled from render fps so the local player advances at the same
    # rate the server simulates them, regardless of how fast/slow this client renders.
    if local is not None and map_rects is not None:
        now = time.time()
        if next_predict_time is None:
            next_predict_time = now

        # Sample held input once per physics tick, stamp it with a sequence number,
        # buffer it for replay, and send it. Prediction itself happens in reconcile()
        # so the rendered position is always "server state + unacked inputs" rather
        # than a free-running guess that can silently drift until it teleports.
        steps = 0
        while next_predict_time <= now and steps < MAX_PHYSICS_STEPS_PER_FRAME:
            tick_seq += 1
            inp = {"seq": tick_seq,
                   "left": held["left"], "right": held["right"],
                   "jump": held["jump"], "dash": dash_pressed}
            pending_inputs.append(inp)
            outbound.append(inp)
            dash_pressed = False  # one-shot: a dash press fires on a single tick
            next_predict_time += PHYSICS_DT
            steps += 1

        # If we hit the step cap and are still behind real time, abandon the backlog
        # rather than spiraling; reconcile() re-bases us on the next snapshot anyway.
        if steps == MAX_PHYSICS_STEPS_PER_FRAME and next_predict_time < now:
            next_predict_time = now + PHYSICS_DT

        # Send accumulated inputs as one batch a few times per second instead of
        # one message per tick. Inputs stay per-tick; we just send fewer, larger
        # messages (or flush early if a backlog builds).
        frame_count += 1
        if outbound and (frame_count % SEND_EVERY == 0 or len(outbound) >= 6):
            sio.emit("input", outbound)
            outbound = []

        if Network.latest_local_state is not None:
            local.reconcile(Network.latest_local_state, pending_inputs, map_rects)

        # draw() reads render_pos; for the local player it tracks the reconciled pos
        local.render_pos = pygame.Vector2(local.pos[0], local.pos[1])

    # --- Remote players: interpolate using the server clock ---
    server_now = Network.server_time_now()
    if server_now is not None:
        render_time = server_now - INTERP_DELAY

        # Drop snapshots that are fully behind render_time, keep at least 2
        while len(Network.state_buffer) >= 2:
            t0, _ = Network.state_buffer[0]
            t1, _ = Network.state_buffer[1]
            if t1 <= render_time:
                Network.state_buffer.popleft()
            else:
                break

        if len(Network.state_buffer) >= 2:
            t0, s0 = Network.state_buffer[0]
            t1, s1 = Network.state_buffer[1]

            if t1 != t0:
                alpha = max(0.0, min(1.0, (render_time - t0) / (t1 - t0)))
            else:
                alpha = 0

            # Iterate the *newer* snapshot so a player who just appeared (in s1 but
            # not the older s0) renders immediately instead of being pinned at their
            # join position until the buffer rotates.
            for k in s1:
                if k == Network.client_id:
                    continue  # local player is handled by prediction
                if k not in playerDict:
                    continue
                p1 = pygame.Vector2(s1[k]["pos"])
                playerDict[k].dashCount = s1[k]["dashCount"]
                playerDict[k].facing = s1[k]["facing"]
                playerDict[k].pos = s1[k]["pos"]
                if k in s0:
                    p0 = pygame.Vector2(s0[k]["pos"])
                    playerDict[k].render_pos = p0.lerp(p1, alpha)
                else:
                    playerDict[k].render_pos = p1

    clock.tick(60)
    screen.fill((50,50,50))

    draw_map()

    if local is not None:
        camera.follow(local)

    scaled_surf = pygame.transform.scale(surf, scale)
    offset = camera.Offset(scale)
    screen.blit(scaled_surf, (offset[0], offset[1]))


    surf.fill((50, 50, 50))
    surf.blit(background, (0, 0))


    for id in playerDict.keys():
        playerDict[id].draw(surf, camera.scroll)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.KEYDOWN:
            # Just record key state here; the physics tick samples it, assigns a
            # sequence number, predicts, and emits to the server.
            if event.key == pygame.K_LEFT:
                held["left"] = True
            if event.key == pygame.K_RIGHT:
                held["right"] = True
            if event.key == pygame.K_SPACE:
                held["jump"] = True
            if event.key == pygame.K_LCTRL:
                dash_pressed = True

            if event.key == pygame.K_ESCAPE:
                if not pause:
                    pause = True
                else:
                    pause = False

            if event.key == pygame.K_ESCAPE:
                screen, fullscreen = toggle_fullscreen(fullscreen)


        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                held["left"] = False
            if event.key == pygame.K_RIGHT:
                held["right"] = False
            if event.key == pygame.K_SPACE:
                held["jump"] = False


    if pause:
        Pause(screen, fonts)

    pygame.display.update()
pygame.quit()
quit()
