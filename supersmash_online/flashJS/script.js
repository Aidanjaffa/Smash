/* =============================================================================
 * Super Smash — browser client (JavaScript port of client.py)
 *
 * This is a faithful port of the pygame client. It speaks the exact same
 * Socket.IO protocol as server.py and runs the same netcode:
 *   - fixed 60 Hz local input sampling + client-side prediction
 *   - server-authoritative reconciliation with input replay
 *   - remote players interpolated behind a fixed render delay
 *
 * IMPORTANT (mirrors the note in client.py / server_objs/Player.py): the physics
 * constants below MUST match the server. If you change a number here, change it
 * on the server too, or the local player will drift relative to where the server
 * (and therefore every other client) thinks they are.
 * ========================================================================== */

"use strict";

// --- Server address ----------------------------------------------------------
// Defaults to the LAN address client.py uses. Override at runtime with
// ?server=http://host:port  (handy when the host is the Pi over the internet).
const SERVER_URL =
  new URLSearchParams(location.search).get("server") || "http://192.168.1.149:5000";

// --- Render / world geometry -------------------------------------------------
const W = 1200,
  H = 720;
const ZOOM = 1.5; // surf is scaled 1.5x and centered (client.py: scale = [1200*1.5, 720*1.5])
const OFFSET_X = (W - W * ZOOM) / 2; // = -300  (camera.Offset)
const OFFSET_Y = (H - H * ZOOM) / 2; // = -180
const PLAYER_W = 10 * 2; // 20
const PLAYER_H = 16 * 2; // 32
const BLOCK = 40;

// --- Netcode constants (see the long comments in client.py for the why) ------
const INTERP_DELAY = 0.08; // render remote players 80 ms behind the server clock
const PHYSICS_DT = 1.0 / 60; // local prediction tick; must equal the server tick rate
const MAX_PHYSICS_STEPS_PER_FRAME = 5;
const SEND_EVERY = 3; // batch per-tick inputs, flush every 3 frames
const STATE_BUFFER_MAX = 20; // matches deque(maxlen=20) in Network.py

// --- Physics constants (MUST MIRROR server_objs/Player.py) -------------------
const MOVE_SPEED = 15;
const GRAVITY = 3;
const MAX_FALL = 50;
const JUMP_IMPULSE = 25;
const DASH_FRAMES = 20;
const DASH_SPEED = 37;
const DASH_COOLDOWN = 10;
const DASH_WALK_SPEED = 10;
const GROUND_SNAP = 31; // pos[1] = item.top - 31 (note: 31, not 32)

// =============================================================================
// Small helpers
// =============================================================================
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];

// pygame Rect.colliderect: overlap with strict inequality (touching edges is NOT
// a collision). Replicate exactly so prediction matches the server.
function colliderect(ax, ay, aw, ah, bx, by, bw, bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

// =============================================================================
// Assets — loaded from ../assets (sibling of flashJS). Everything degrades to a
// colored-rectangle fallback if an image can't be reached, so the game is still
// playable when served from somewhere the PNGs aren't.
// =============================================================================
function loadImage(src) {
  const img = new Image();
  img.src = src;
  return img;
}
const IMG = {
  dirt: loadImage("../assets/dirt.png"),
  bg: loadImage("../assets/Lv1_BG1.png"),
  man: loadImage("../assets/horatioStand.png"),
  sword: loadImage("../assets/sword.png"),
  // pause-menu key icons
  arrow: loadImage("../assets/arrow.png"),
  space: loadImage("../assets/space.png"),
  ctrl: loadImage("../assets/Ctrl.png"),
};
const ready = (img) => img && img.complete && img.naturalWidth > 0;

// joystix.otf — the pause menu's font. Loads async; canvas falls back to monospace
// until it's ready (matches the two pygame sizes 19 and 35).
if (window.FontFace) {
  const joystix = new FontFace("joystix", "url(../assets/joystix.otf)");
  joystix
    .load()
    .then((f) => document.fonts.add(f))
    .catch(() => {});
}

// Build a tinted, optionally flipped sprite the way pygame's BLEND_RGBA_MULT
// does: multiply the sprite's RGB by the player color, keeping the sprite's
// alpha mask. Cached per (color, facing).
function makeTinted(img, color, flip, w, h) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const cx = c.getContext("2d");
  if (flip) {
    cx.translate(w, 0);
    cx.scale(-1, 1);
  }
  cx.drawImage(img, 0, 0, w, h);
  cx.globalCompositeOperation = "multiply";
  cx.fillStyle = `rgb(${color[0]},${color[1]},${color[2]})`;
  cx.fillRect(0, 0, w, h);
  cx.globalCompositeOperation = "destination-in"; // clip the fill back to the sprite shape
  cx.drawImage(img, 0, 0, w, h);
  return c;
}

// =============================================================================
// Player — mirror of client_objs/Player.py (prediction half) + drawing
// =============================================================================
class Player {
  constructor(pos, id) {
    this.pos = [pos[0], pos[1]];
    this.renderPos = [pos[0], pos[1]];
    this.vel = [0, 0];
    this.id = id;
    this.color = [
      Math.floor(Math.random() * 256),
      Math.floor(Math.random() * 256),
      Math.floor(Math.random() * 256),
    ];
    this.dashCount = 0;

    // mirror of server-side physics state used by predict()
    this.colliding = false;
    this.jump = false;
    this.moving = false;
    this.Dash = false;
    this.cooldown = 0;
    this.facing = 0; // 0 = right, 1 = left

    this.afterImages = []; // [x, y, alpha]
    this._tintCache = {}; // facing -> tinted canvas
  }

  // server.py @sio.on("input") movement: zero vel, set from the held key
  applyInput(data) {
    this.vel[0] = 0;
    this.moving = false;
    if (data.left) {
      this.vel[0] = -MOVE_SPEED;
      this.moving = true;
      this.facing = 1;
    } else if (data.right) {
      this.vel[0] = MOVE_SPEED;
      this.moving = true;
      this.facing = 0;
    }
  }

  // Mirror of server_objs/Player.py update() for walk + gravity + jump + ground.
  predict(mapRects) {
    this.pos[0] += this.vel[0];
    this.pos[1] += this.vel[1];

    const rx = this.pos[0],
      ry = this.pos[1];

    if (!this.colliding) this.vel[1] += GRAVITY;
    if (this.vel[1] > MAX_FALL) this.vel[1] = MAX_FALL;

    this.colliding = false;
    for (const r of mapRects) {
      if (colliderect(rx, ry, PLAYER_W, PLAYER_H, r.x, r.y, r.w, r.h)) {
        if (this.vel[1] > 1) {
          this.vel[1] = 0;
          this.pos[1] = r.y - GROUND_SNAP;
          this.colliding = true;
          if (this.jump) {
            this.vel[1] -= JUMP_IMPULSE;
            this.pos[1] -= 1;
          }
        }
      }
    }
  }

  // Mirror of server_objs/Player.py dash(). Dash is predicted locally to avoid
  // the round-trip snap; the server runs identical logic in lockstep.
  dashPredict() {
    if (this.Dash && this.cooldown === 0 && this.dashCount <= 0) {
      this.dashCount = DASH_FRAMES;
    }
    if (this.dashCount > 0) {
      this.dashCount -= 1;
      if (this.facing === 1) this.vel[0] = -DASH_SPEED;
      else if (this.facing === 0) this.vel[0] = DASH_SPEED;
      if (this.dashCount === 0) this.cooldown = DASH_COOLDOWN;
    }
    if (this.Dash && this.cooldown > 0) {
      this.vel[0] = 0;
      if (this.moving) {
        this.vel[0] = this.facing === 1 ? -DASH_WALK_SPEED : DASH_WALK_SPEED;
      }
    }
    if (this.cooldown > 0) {
      this.cooldown -= 1;
      this.Dash = false;
    }
  }

  // Server-authoritative prediction with input replay (see client_objs/Player.py
  // reconcile docstring): drop acked inputs, snap to server truth, replay the rest.
  // `pendingInputs` is an array used as a queue and is mutated in place.
  reconcile(serverState, pendingInputs, mapRects) {
    const ack = serverState.last_ack || 0;
    while (pendingInputs.length && pendingInputs[0].seq <= ack) {
      pendingInputs.shift();
    }

    this.pos = [serverState.pos[0], serverState.pos[1]];
    this.vel = serverState.vel ? [serverState.vel[0], serverState.vel[1]] : [0, 0];

    // During knockback the server owns vel[0] entirely (server Hit()), so follow
    // it exactly instead of predicting over it.
    if (serverState.hit) return;

    this.colliding = !!serverState.colliding;
    this.cooldown = serverState.cooldown || 0;
    this.dashCount = serverState.dashCount || 0;
    if (serverState.facing !== undefined) this.facing = serverState.facing;

    for (const inp of pendingInputs) {
      this.applyInput(inp);
      this.jump = inp.jump;
      if (inp.dash) this.Dash = true;
      this.predict(mapRects);
      this.dashPredict();
    }
  }

  // --- drawing -------------------------------------------------------------
  _tinted(facing) {
    if (!ready(IMG.man)) return null;
    if (!this._tintCache[facing]) {
      this._tintCache[facing] = makeTinted(IMG.man, this.color, facing === 1, PLAYER_W, PLAYER_H);
    }
    return this._tintCache[facing];
  }

  _drawBody(ctx, x, y, alpha) {
    const sprite = this._tinted(this.facing);
    ctx.globalAlpha = alpha;
    if (sprite) {
      ctx.drawImage(sprite, x, y);
    } else {
      ctx.fillStyle = `rgb(${this.color[0]},${this.color[1]},${this.color[2]})`;
      ctx.fillRect(x, y, PLAYER_W, PLAYER_H);
    }
    ctx.globalAlpha = 1;
  }

  _drawSword(ctx, x, y) {
    // facing 0 (right): offset (+10, +5); facing 1 (left): offset (-30, +5)
    const ox = this.facing === 0 ? x + 10 : x - 30;
    const oy = y + 5;
    if (ready(IMG.sword)) {
      const w = 16 * 2,
        h = 10 * 2;
      ctx.save();
      ctx.translate(ox + w / 2, oy + h / 2);
      // pygame rotates 16deg CCW; canvas positive is CW, so negate.
      ctx.rotate(this.facing === 0 ? (-16 * Math.PI) / 180 : (16 * Math.PI) / 180);
      if (this.facing === 1) ctx.scale(-1, 1);
      ctx.drawImage(IMG.sword, -w / 2, -h / 2, w, h);
      ctx.restore();
    } else {
      // fallback: a little blade line
      ctx.strokeStyle = "#dddddd";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(this.facing === 0 ? x + PLAYER_W : x, y + 12);
      ctx.lineTo(this.facing === 0 ? x + PLAYER_W + 22 : x - 22, y + 4);
      ctx.stroke();
    }
  }

  draw(ctx, scroll) {
    const rx = this.renderPos[0] + scroll[0];
    const ry = this.renderPos[1] + scroll[1];

    // main sprite + (mirror of applyTints: spawn an afterimage while dashing)
    this._drawBody(ctx, rx, ry, 1.0);
    if (this.dashCount > 0) {
      this.afterImages.push([this.renderPos[0], this.renderPos[1], 255]);
    }

    // fading afterimages (mirror of AfterImage())
    for (let i = this.afterImages.length - 1; i >= 0; i--) {
      const a = this.afterImages[i];
      this._drawBody(ctx, a[0] + scroll[0], a[1] + scroll[1], a[2] / 255);
      a[2] -= 10;
      if (a[2] <= 0) this.afterImages.splice(i, 1);
    }

    this._drawSword(ctx, rx, ry);
  }
}

// =============================================================================
// Camera — mirror of client_objs/Camera.py
// =============================================================================
const camera = {
  scroll: [0, 0],
  follow(entity) {
    this.scroll[0] -= (entity.renderPos[0] + this.scroll[0] - W / 2) / 10;
    this.scroll[1] -= (entity.renderPos[1] + this.scroll[1] - H / 2) / 10;
  },
};

// =============================================================================
// Network — mirror of client_objs/Network.py
// =============================================================================
const Network = {
  sio: null,
  clientId: "",
  playerDict: {},
  map: [],
  stateBuffer: [], // array of {t, players}
  clockOffset: null,
  latestLocalState: null,
  connected: false,

  serverTimeNow() {
    if (this.clockOffset === null) return null;
    return Date.now() / 1000 + this.clockOffset;
  },

  connect() {
    // Force WebSocket: polling-then-upgrade can leave a high-rate input stream
    // stuck on HTTP long-polling, which batches terribly and adds latency.
    const sio = io(SERVER_URL, { transports: ["websocket"] });
    this.sio = sio;

    sio.on("connect", () => {
      this.connected = true;
      console.log("connected, transport =", sio.io.engine.transport.name);
    });
    sio.on("disconnect", () => {
      this.connected = false;
      console.log("disconnected");
    });

    sio.on("id", (data) => {
      this.clientId = data;
      console.log("id", data);
    });

    sio.on("init", (data) => {
      for (const k in data) {
        const v = data[k];
        const p = new Player(v.pos, v.id);
        if (v.color) p.color = v.color;
        this.playerDict[k] = p;
      }
      console.log("added all current players", Object.keys(this.playerDict));
    });

    sio.on("player", (data) => {
      const p = new Player(data.pos, data.id);
      if (data.color) p.color = data.color;
      this.playerDict[data.id] = p;
      console.log("added new player", data.id);
    });

    sio.on("load_map", (data) => {
      // server sends list-of-lists of single chars; tolerate list-of-strings too
      this.map = data.map((row) => (typeof row === "string" ? row.split("") : row));
    });

    sio.on("remove", (sid) => {
      delete this.playerDict[sid];
    });

    sio.on("state", (data) => {
      const serverT = data.t;
      const players = data.players;

      const localT = Date.now() / 1000;
      const observed = serverT - localT;
      if (this.clockOffset === null) this.clockOffset = observed;
      else this.clockOffset = 0.95 * this.clockOffset + 0.05 * observed;

      this.stateBuffer.push({ t: serverT, players });
      if (this.stateBuffer.length > STATE_BUFFER_MAX) this.stateBuffer.shift();

      if (this.clientId && players[this.clientId]) {
        this.latestLocalState = players[this.clientId];
      }
    });
  },
};

// =============================================================================
// Map collision rects (blocks marked "1") — mirror of build_map_rects()
// =============================================================================
function buildMapRects(grid) {
  const rects = [];
  for (let y = 0; y < grid.length; y++) {
    const row = grid[y];
    for (let x = 0; x < row.length; x++) {
      if (row[x] === "1") rects.push({ x: x * BLOCK, y: y * BLOCK, w: BLOCK, h: BLOCK });
    }
  }
  return rects;
}

// =============================================================================
// Pause menu — faithful port of client_objs/menus.py + helpers/utils.py.
// Drawn in screen space (1200x720) on top of the dimmed game, exactly as
// Pause(screen, fonts) does. Coordinates are copied verbatim from menus.py.
// =============================================================================
const White = "rgb(255,255,255)";

// helpers.utils.load_text: render text with its top-left at pos.
function loadText(ctx, msg, color, pos, size) {
  ctx.font = `${size}px joystix, monospace`;
  ctx.fillStyle = color;
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(msg, pos[0], pos[1]);
}

// pygame.draw.line(surf, color, a, b, thickness)
function drawLine(ctx, seg, thickness) {
  ctx.strokeStyle = White;
  ctx.lineWidth = thickness;
  ctx.beginPath();
  ctx.moveTo(seg[0][0], seg[0][1]);
  ctx.lineTo(seg[1][0], seg[1][1]);
  ctx.stroke();
}

function rectsCollide(a, b) {
  return colliderect(a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]);
}

// Draw a 40x40 key icon at (x,y), rotated like pygame.transform.rotate (CCW
// positive). Canvas rotates CW, so we negate the angle. Square icons keep their
// 40x40 box under 90/180 rotations, so top-left stays (x,y) as in the blits.
function drawIcon(ctx, img, x, y, w, h, ccwDeg, fallbackLabel) {
  if (ready(img)) {
    ctx.save();
    ctx.translate(x + w / 2, y + h / 2);
    ctx.rotate((-ccwDeg * Math.PI) / 180);
    ctx.drawImage(img, -w / 2, -h / 2, w, h);
    ctx.restore();
  } else {
    ctx.strokeStyle = White;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    if (fallbackLabel) {
      ctx.fillStyle = White;
      ctx.font = "14px joystix, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(fallbackLabel, x + w / 2, y + h / 2);
      ctx.textAlign = "left";
    }
  }
}

class Slider {
  constructor(pos, currentPosition) {
    this.pos = pos;
    this.rect = [pos[0] + currentPosition, pos[1], 23, 23];
    this.range = 200;
    this.rail = [pos[0], pos[1] + 5, this.range, 15];
  }
  draw(ctx) {
    ctx.fillStyle = White;
    ctx.fillRect(this.rect[0], this.rect[1], this.rect[2], this.rect[3]);
    ctx.fillRect(this.rail[0], this.rail[1], this.rail[2], this.rail[3]);
  }
  move(mouse, mouseRect) {
    if (rectsCollide(this.rect, mouseRect) && mouse.down) {
      if (mouse.x < this.rail[0] + this.rect[2] / 2) {
        this.rect[0] = this.rail[0];
      } else if (mouse.x > this.rail[0] + this.range - this.rect[2] / 2) {
        this.rect[0] = this.rail[0] + 200 - 23;
      } else {
        this.rect[0] = mouse.x - 10;
      }
    }
    const distanceAlong = this.rect[0] - this.rail[0];
    return Math.floor((distanceAlong / this.range) * 113);
  }
}

class MenuItem {
  constructor(startPos, text, textPos, fontSize) {
    this.text = text;
    this.textPos = textPos;
    this.startPos = startPos;
    this.fontSize = fontSize;

    this.topLine = [
      [startPos[0], startPos[1]],
      [startPos[0] + 300, startPos[1]],
    ];
    this.bottomLine = [
      [startPos[0], startPos[1] + 35],
      [startPos[0] + 290, startPos[1] + 35],
    ];
    this.connector = [
      [this.bottomLine[1][0], this.bottomLine[1][1]],
      [this.topLine[1][0], this.topLine[1][1]],
    ];

    this.rect = [startPos[0], startPos[1], 300, 35]; // hover hitbox (not drawn)
    this.thickness = 3;
    this.active = false;

    this.SFX_volume = new Slider([800, 300], 100);
    this.music_volume = new Slider([800, 380], 120);
  }

  draw(ctx) {
    drawLine(ctx, this.topLine, this.thickness);
    drawLine(ctx, this.bottomLine, this.thickness);
    drawLine(ctx, this.connector, this.thickness);
    loadText(ctx, this.text, White, this.textPos, this.fontSize);
  }

  update(ctx, mouse, mouseRect) {
    if (!this.active) return;

    if (this.text === "Disconnect") {
      if (!disconnected) {
        Network.sio.disconnect();
        disconnected = true;
      }
    }

    if (this.text === "Options") {
      loadText(ctx, "SFX Volume", White, [500, 300], this.fontSize);
      this.SFX_volume.draw(ctx);
      this.SFX_volume.move(mouse, mouseRect);

      loadText(ctx, "Music Volume", White, [500, 380], this.fontSize);
      this.music_volume.draw(ctx);
      this.music_volume.move(mouse, mouseRect);

      loadText(ctx, "Toggle Fullscreen", White, [500, 460], this.fontSize);
    }

    if (this.text === "Controls") {
      drawIcon(ctx, IMG.arrow, 1000, 222, 40, 40, 90, "<"); // arrow_left
      loadText(ctx, "Move Left", White, [640, 230], this.fontSize);

      drawIcon(ctx, IMG.arrow, 1000, 292, 40, 40, -90, ">"); // arrow_right
      loadText(ctx, "Move Right", White, [640, 300], this.fontSize);

      drawIcon(ctx, IMG.space, 1000, 362, 120, 40, 0, "SPACE"); // space_bar
      loadText(ctx, "Jump", White, [640, 370], this.fontSize);

      drawIcon(ctx, IMG.ctrl, 1000, 432, 40, 40, 0, "CTRL"); // ctrl
      loadText(ctx, "Dash", White, [640, 440], this.fontSize);

      drawIcon(ctx, IMG.arrow, 1000, 502, 40, 40, 180, "v"); // arrow_down
      loadText(ctx, "Down Attack", White, [640, 510], this.fontSize);
    }
  }
}

const mouse = { x: 0, y: 0, down: false };
let menuItems = null;
let menuDt = 0;
let disconnected = false;

function animateItem(item, size) {
  if (item.thickness !== size) {
    if (menuDt % 2 === 0) {
      if (size - item.thickness > 0) item.thickness += 1;
      else if (size - item.thickness < 0) item.thickness -= 1;
    }
  }
}

function drawPause(ctx) {
  if (!menuItems) {
    menuItems = [
      new MenuItem([0, 445], "Controls", [155, 450], 19),
      new MenuItem([0, 495], "Options", [170, 500], 19),
      new MenuItem([0, 545], "Disconnect", [130, 550], 19),
    ];
  }
  menuDt += 1;

  // helpers.utils.Dimmer.dim: black at alpha 64 (64/255 ~= 0.251) over the screen
  ctx.fillStyle = "rgba(0,0,0,0.251)";
  ctx.fillRect(0, 0, W, H);

  const mouseRect = [mouse.x, mouse.y, 10, 10];
  loadText(ctx, "PAUSED", White, [500, 100], 35); // fonts[1] is size 35

  for (const item of menuItems) {
    item.draw(ctx);
    item.update(ctx, mouse, mouseRect);
    if (rectsCollide(item.rect, mouseRect)) {
      animateItem(item, 10);
      if (mouse.down) {
        switch (item.text) {
          case "Controls":
            menuItems[0].active = true;
            menuItems[1].active = false;
            menuItems[2].active = false;
            break;
          case "Options":
            menuItems[0].active = false;
            menuItems[1].active = true;
            menuItems[2].active = false;
            break;
          case "Disconnect":
            menuItems[0].active = false;
            menuItems[1].active = false;
            menuItems[2].active = true;
            break;
        }
      }
    } else {
      animateItem(item, 3);
    }
  }
}

// =============================================================================
// Input — record key state; the physics tick samples it (mirror of client.py
// event loop). dash is a one-shot fired on the keydown transition only.
// =============================================================================
const held = { left: false, right: false, jump: false };
let dashPressed = false;
let paused = false;

window.addEventListener("keydown", (e) => {
  switch (e.code) {
    case "ArrowLeft":
      held.left = true;
      e.preventDefault();
      break;
    case "ArrowRight":
      held.right = true;
      e.preventDefault();
      break;
    case "Space":
      held.jump = true;
      e.preventDefault();
      break;
    case "ControlLeft":
      if (!e.repeat) dashPressed = true; // ignore auto-repeat; pygame KEYDOWN fires once
      e.preventDefault();
      break;
    case "Escape":
      paused = !paused;
      break;
    case "KeyF":
      toggleFullscreen();
      break;
  }
});

window.addEventListener("keyup", (e) => {
  switch (e.code) {
    case "ArrowLeft":
      held.left = false;
      break;
    case "ArrowRight":
      held.right = false;
      break;
    case "Space":
      held.jump = false;
      break;
  }
});

function toggleFullscreen() {
  if (!document.fullscreenElement) canvas.requestFullscreen?.();
  else document.exitFullscreen?.();
}

// =============================================================================
// Main loop — mirror of client.py's while-run loop
// =============================================================================
const canvas = document.querySelector("canvas");
canvas.width = W;
canvas.height = H;
const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false; // crisp pixel-art scaling (pygame uses nearest)

// Map browser mouse coords to the canvas's internal 1200x720 space (the canvas is
// CSS-scaled), so the pause menu's hit-testing matches pygame.mouse.get_pos().
function updateMouse(e) {
  const r = canvas.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) * W) / r.width;
  mouse.y = ((e.clientY - r.top) * H) / r.height;
}
canvas.addEventListener("mousemove", updateMouse);
canvas.addEventListener("mousedown", (e) => {
  updateMouse(e);
  if (e.button === 0) mouse.down = true;
});
window.addEventListener("mouseup", (e) => {
  if (e.button === 0) mouse.down = false;
});

let mapRects = null;
let nextPredictTime = null;
let tickSeq = 0;
const pendingInputs = []; // queue: per-tick inputs awaiting server ack (replayed in reconcile)
let outbound = []; // batched, flushed to the server
let frameCount = 0;

function drawMap() {
  for (let y = 0; y < Network.map.length; y++) {
    const row = Network.map[y];
    for (let x = 0; x < row.length; x++) {
      const block = row[x];
      if (block === "1" || block === "c") {
        const px = x * BLOCK + camera.scroll[0];
        const py = y * BLOCK + camera.scroll[1];
        if (ready(IMG.dirt)) ctx.drawImage(IMG.dirt, px, py, BLOCK, BLOCK);
        else {
          ctx.fillStyle = "#6b4a2b";
          ctx.fillRect(px, py, BLOCK, BLOCK);
        }
      }
    }
  }
}

function drawOverlay() {
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  // The pygame client shows no HUD; only surface a small status line before we're
  // connected (or after a Disconnect), so the playing view stays clean.
  if (!Network.connected) {
    ctx.font = "16px joystix, monospace";
    ctx.fillStyle = "#f99";
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(disconnected ? "disconnected" : `connecting to ${SERVER_URL} …`, 12, 24);
  }

  if (paused) drawPause(ctx);
}

function frame() {
  requestAnimationFrame(frame);

  // build collision rects once the map has arrived
  if (mapRects === null && Network.map.length) mapRects = buildMapRects(Network.map);

  const local = Network.clientId ? Network.playerDict[Network.clientId] : null;

  // --- Local player: sample input at a fixed 60 Hz, reconcile against server ---
  // Pause is a visual overlay only (see client.py): the sim keeps running and input
  // keeps being sampled/sent underneath it.
  if (local && mapRects) {
    const now = performance.now() / 1000;
    if (nextPredictTime === null) nextPredictTime = now;

    let steps = 0;
    while (nextPredictTime <= now && steps < MAX_PHYSICS_STEPS_PER_FRAME) {
      tickSeq += 1;
      const inp = {
        seq: tickSeq,
        left: held.left,
        right: held.right,
        jump: held.jump,
        dash: dashPressed,
      };
      pendingInputs.push(inp);
      outbound.push(inp);
      dashPressed = false; // one-shot: a dash press fires on a single tick
      nextPredictTime += PHYSICS_DT;
      steps += 1;
    }
    // hit the step cap and still behind: abandon backlog, reconcile re-bases us
    if (steps === MAX_PHYSICS_STEPS_PER_FRAME && nextPredictTime < now) {
      nextPredictTime = now + PHYSICS_DT;
    }

    // send accumulated inputs as one batch a few times per second
    frameCount += 1;
    if (outbound.length && (frameCount % SEND_EVERY === 0 || outbound.length >= 6)) {
      Network.sio.emit("input", outbound);
      outbound = [];
    }

    if (Network.latestLocalState !== null) {
      local.reconcile(Network.latestLocalState, pendingInputs, mapRects);
    }
    local.renderPos = [local.pos[0], local.pos[1]];
  }

  // --- Remote players: interpolate using the server clock ---
  const serverNow = Network.serverTimeNow();
  if (serverNow !== null) {
    const renderTime = serverNow - INTERP_DELAY;

    while (Network.stateBuffer.length >= 2 && Network.stateBuffer[1].t <= renderTime) {
      Network.stateBuffer.shift();
    }

    if (Network.stateBuffer.length >= 2) {
      const { t: t0, players: s0 } = Network.stateBuffer[0];
      const { t: t1, players: s1 } = Network.stateBuffer[1];
      const alpha = t1 !== t0 ? clamp((renderTime - t0) / (t1 - t0), 0, 1) : 0;

      // iterate the newer snapshot so a just-joined player renders immediately
      for (const k in s1) {
        if (k === Network.clientId) continue; // local player handled by prediction
        const p = Network.playerDict[k];
        if (!p) continue;
        p.dashCount = s1[k].dashCount;
        p.facing = s1[k].facing;
        p.pos = [s1[k].pos[0], s1[k].pos[1]];
        if (s0[k]) p.renderPos = lerp(s0[k].pos, s1[k].pos, alpha);
        else p.renderPos = [s1[k].pos[0], s1[k].pos[1]];
      }
    }
  }

  // --- Render ---------------------------------------------------------------
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "rgb(50,50,50)";
  ctx.fillRect(0, 0, W, H);

  if (local) camera.follow(local);

  // world is drawn in surf-space, scaled 1.5x and centered (screen = offset + zoom*surf)
  ctx.setTransform(ZOOM, 0, 0, ZOOM, OFFSET_X, OFFSET_Y);

  if (ready(IMG.bg)) ctx.drawImage(IMG.bg, 0, 0, W * 0.9, H * 0.9);

  drawMap();
  for (const id in Network.playerDict) Network.playerDict[id].draw(ctx, camera.scroll);

  drawOverlay();
}

// =============================================================================
// Boot
// =============================================================================
Network.connect();
requestAnimationFrame(frame);
