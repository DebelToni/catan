const socket = io();
const RESOURCE_TYPES = ["lumber", "brick", "wool", "grain", "ore"];
const RESOURCE_LABELS = {lumber: "Lumber", brick: "Brick", wool: "Wool", grain: "Grain", ore: "Ore"};
const DEV_LABELS = {knight: "Knight", road_building: "Road Building", year_of_plenty: "Year of Plenty", monopoly: "Monopoly", victory_point: "Victory Point"};
const TERRAIN_COLORS = {forest: "#2d6a4f", pasture: "#90be6d", field: "#e9c46a", hill: "#bc6c25", mountain: "#8d99ae", desert: "#d4a373"};
const ASSET_NAMES = [
  "terrain_forest", "terrain_pasture", "terrain_field", "terrain_hill", "terrain_mountain", "terrain_desert", "terrain_sea",
  "resource_lumber", "resource_brick", "resource_wool", "resource_grain", "resource_ore",
  "icon_robber", "number_token",
  "dev_knight", "dev_road_building", "dev_year_of_plenty", "dev_monopoly", "dev_victory_point", "card_back_development",
  "port_3to1", "port_lumber", "port_brick", "port_wool", "port_grain", "port_ore",
  "largest_army", "longest_road", "dice_1", "dice_2", "dice_3", "dice_4", "dice_5", "dice_6"
];

let colors = [];
let state = null;
let gameId = (document.body.dataset.gameId || new URLSearchParams(location.search).get("game") || "").toUpperCase();
let playerId = null;
let selectedAction = null;
let pendingRobberHexId = null;
let lastRollKey = "";
let profile = readJson("catanProfile", {name: "", color: "red"});
let savedPlayers = readJson("catanPlayers", {});
let createColor = profile.color || "red";
let joinColor = profile.color || "blue";

const assets = {};
for (const name of ASSET_NAMES) {
  const image = new Image();
  image.src = `/static/assets/${name}.png`;
  assets[name] = image;
}

const el = (id) => document.getElementById(id);
const home = el("home");
const game = el("game");
const canvas = el("boardCanvas");
const ctx = canvas.getContext("2d");
const view = {x: 0, y: 0, scale: 88, fittedGame: null};
const pointer = {down: false, moved: false, x: 0, y: 0, startX: 0, startY: 0, hover: null};

socket.on("server_info", (data) => {
  colors = data.colors || [];
  renderColorPickers();
});
socket.on("game_created", ({game_id, player_id}) => {
  gameId = game_id;
  playerId = player_id;
  savePlayerForGame(gameId, playerId);
  history.pushState(null, "", `/game/${gameId}`);
  showGame();
});
socket.on("joined_game", ({game_id, player_id}) => {
  gameId = game_id;
  playerId = player_id;
  savePlayerForGame(gameId, playerId);
  history.pushState(null, "", `/game/${gameId}`);
  showGame();
});
socket.on("state", (newState) => {
  state = newState;
  if (state.you) playerId = state.you.id;
  showGame();
  renderAll();
  const roll = state.last_roll;
  const rollKey = roll ? `${roll.turn}:${roll.die1}:${roll.die2}` : "";
  if (roll && rollKey !== lastRollKey) {
    lastRollKey = rollKey;
    animateDice(roll);
  }
});
socket.on("error_message", ({message}) => toast(message));

window.addEventListener("load", () => {
  setupForms();
  setupCanvas();
  setupControls();
  refreshOpenGames();
  setInterval(refreshOpenGames, 5000);
  if (gameId) {
    el("joinForm").game_id.value = gameId;
    const saved = savedPlayers[gameId];
    if (saved) {
      playerId = saved;
      socket.emit("join_game", {game_id: gameId, player_id: playerId, name: profile.name || "Player", color: profile.color || joinColor});
    }
  }
});

function setupForms() {
  el("createForm").name.value = profile.name || "";
  el("joinForm").name.value = profile.name || "";
  if (gameId) el("joinForm").game_id.value = gameId;
  el("createForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const name = form.name.value.trim() || "Player";
    profile = {name, color: createColor};
    writeJson("catanProfile", profile);
    socket.emit("create_game", {
      name,
      color: createColor,
      settings: {
        points_to_win: form.points_to_win.value,
        hand_limit: form.hand_limit.value,
        turn_timer_seconds: form.turn_timer_seconds.value,
        random_map: form.random_map.checked,
        friendly_robber: form.friendly_robber.checked,
        map_seed: form.map_seed.value.trim(),
      },
    });
  });
  el("joinForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const name = form.name.value.trim() || "Player";
    const targetGame = form.game_id.value.trim().toUpperCase();
    profile = {name, color: joinColor};
    writeJson("catanProfile", profile);
    socket.emit("join_game", {game_id: targetGame, name, color: joinColor, player_id: savedPlayers[targetGame]});
  });
}

function renderColorPickers() {
  if (!colors.length) return;
  if (!colors.some((color) => color.id === createColor)) createColor = colors[0].id;
  if (!colors.some((color) => color.id === joinColor)) joinColor = colors[Math.min(1, colors.length - 1)].id;
  drawColorPicker(el("createColors"), createColor, (id) => { createColor = id; renderColorPickers(); });
  drawColorPicker(el("joinColors"), joinColor, (id) => { joinColor = id; renderColorPickers(); });
}

function drawColorPicker(container, selected, onPick) {
  container.innerHTML = "";
  for (const color of colors) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `color-choice ${selected === color.id ? "selected" : ""}`;
    button.style.background = color.hex;
    button.title = color.name;
    button.addEventListener("click", () => onPick(color.id));
    container.appendChild(button);
  }
}

async function refreshOpenGames() {
  try {
    const response = await fetch("/api/games");
    const games = await response.json();
    const container = el("openGames");
    if (!container || state) return;
    container.innerHTML = games.slice(0, 6).map((item) => `
      <div class="open-game">
        <div><strong>${item.id}</strong><div class="subtle">${item.phase} · ${item.players} players</div></div>
        <button type="button" data-join-open="${item.id}">Use</button>
      </div>
    `).join("");
    container.querySelectorAll("[data-join-open]").forEach((button) => {
      button.addEventListener("click", () => { el("joinForm").game_id.value = button.dataset.joinOpen; });
    });
  } catch (_) {}
}

function setupControls() {
  el("copyLinkBtn").addEventListener("click", async () => {
    const url = `${location.origin}/game/${gameId}`;
    await navigator.clipboard.writeText(url);
    toast("Copied share link.");
  });
  el("fitBoardBtn").addEventListener("click", () => { fitBoard(true); drawBoard(); });
  el("bankTradeBtn").addEventListener("click", () => emit("bank_trade", {give: el("bankGive").value, receive: el("bankReceive").value}));
  el("offerBtn").addEventListener("click", () => emit("create_trade_offer", {give: readInputs("offerGive"), receive: readInputs("offerReceive")}));
  el("discardBtn").addEventListener("click", () => emit("discard", {resources: readInputs("discard")}));
  el("chatBtn").addEventListener("click", sendChat);
  el("chatInput").addEventListener("keydown", (event) => { if (event.key === "Enter") sendChat(); });
  fillResourceSelects();
  renderInputGrid(el("offerGive"), "offerGive");
  renderInputGrid(el("offerReceive"), "offerReceive");
}

function fillResourceSelects() {
  for (const select of [el("bankGive"), el("bankReceive")]) {
    select.innerHTML = RESOURCE_TYPES.map((resource) => `<option value="${resource}">${RESOURCE_LABELS[resource]}</option>`).join("");
  }
  el("bankReceive").value = "grain";
}

function sendChat() {
  const input = el("chatInput");
  emit("chat", {text: input.value});
  input.value = "";
}

function emit(event, payload = {}) {
  if (!gameId || !playerId) return toast("Join a game first.");
  socket.emit(event, {game_id: gameId, player_id: playerId, ...payload});
}

function showGame() {
  home.classList.add("hidden");
  game.classList.remove("hidden");
  requestAnimationFrame(() => { resizeCanvas(); fitBoard(); drawBoard(); });
}

function renderAll() {
  if (!state) return;
  el("gameTitle").textContent = `Game ${state.game_id}`;
  el("phaseText").textContent = `${state.phase}${state.turn_stage && state.turn_stage !== state.phase ? ` · ${state.turn_stage}` : ""}`;
  if (view.fittedGame !== state.game_id) fitBoard(true);
  renderPlayers();
  renderTurn();
  renderHand();
  renderDiscard();
  renderRobberPanel();
  renderTrades();
  renderLog();
  drawBoard();
}

function renderPlayers() {
  const container = el("playersList");
  container.innerHTML = state.players.map((player) => `
    <div class="player-row ${player.id === state.current_player_id ? "current-player" : ""}">
      <span class="color-dot" style="background:${player.color_hex}"></span>
      <div class="player-name">${escapeHtml(player.name)} ${player.host ? "★" : ""}${player.connected ? "" : " · offline"}</div>
      <div class="player-stats">${player.public_vp}${player.total_vp != null && player.total_vp !== player.public_vp ? `/${player.total_vp}` : ""} VP · ${player.resource_count} cards · ${player.dev_count} dev · ${player.knights_played}⚔ · ${player.longest_road} roads</div>
    </div>
  `).join("");
}

function renderTurn() {
  const active = state.players.find((player) => player.id === state.current_player_id);
  const me = state.players.find((player) => player.id === playerId);
  const isActive = state.current_player_id === playerId;
  const controls = el("mainControls");
  controls.innerHTML = "";
  el("turnInfo").innerHTML = state.winner
    ? `<strong>${escapeHtml(state.players.find((p) => p.id === state.winner)?.name || "Winner")} wins.</strong>`
    : `<div>Active: <strong>${escapeHtml(active?.name || "Waiting")}</strong></div><div class="subtle">You: ${escapeHtml(me?.name || "not joined")}</div>`;

  if (state.phase === "lobby") {
    if (me?.host) addControl("Start game", () => emit("start_game"), "primary");
    addControl("Copy link", () => el("copyLinkBtn").click());
    el("actionHelp").textContent = "Players choose one of the 10 colors and the host starts when ready.";
    return;
  }

  if (state.phase === "setup") {
    const myTurn = state.setup?.player_id === playerId;
    if (myTurn) {
      selectedAction = state.setup.action;
      el("actionHelp").textContent = `Setup round ${state.setup.round}: click a ${state.setup.action}.`;
    } else {
      el("actionHelp").textContent = `Waiting for ${escapeHtml(active?.name || "the active player")} to place ${state.setup?.action || "a piece"}.`;
    }
    return;
  }

  if (!isActive) {
    el("actionHelp").textContent = "Watch, trade if offered, and plan your next build.";
    return;
  }

  if (state.turn_stage === "must_roll") {
    addControl("Roll dice", () => emit("roll_dice"), "primary");
    selectedAction = null;
    el("actionHelp").textContent = "Roll to produce resources. Rolling 7 triggers discards and robber movement.";
  } else if (state.turn_stage === "main") {
    addActionControl("Road", "road");
    addActionControl("Settlement", "settlement");
    addActionControl("City", "city");
    addControl("Buy dev", () => emit("buy_dev_card"));
    addControl("End turn", () => emit("end_turn"), "primary");
    el("actionHelp").textContent = selectedAction ? `Click the board to place a ${selectedAction}.` : "Build, trade, buy/play development cards, then end turn.";
  } else if (state.turn_stage === "road_building") {
    selectedAction = "road";
    addActionControl(`Free road (${state.free_roads_remaining})`, "road");
    el("actionHelp").textContent = "Road Building: click two empty edges connected to your network.";
  } else if (state.turn_stage === "move_robber") {
    selectedAction = "robber";
    el("actionHelp").textContent = "Click a tile for the robber.";
  } else if (state.turn_stage === "discard") {
    selectedAction = null;
    el("actionHelp").textContent = "Waiting for required discards.";
  }

  function addControl(label, handler, klass = "") {
    const button = document.createElement("button");
    button.textContent = label;
    button.className = klass;
    button.addEventListener("click", handler);
    controls.appendChild(button);
  }
  function addActionControl(label, action) {
    const button = document.createElement("button");
    button.textContent = label;
    button.className = selectedAction === action ? "selected" : "";
    button.addEventListener("click", () => { selectedAction = selectedAction === action ? null : action; renderTurn(); drawBoard(); });
    controls.appendChild(button);
  }
}

function renderHand() {
  const resources = state.you?.resources || {};
  el("resourcesList").innerHTML = RESOURCE_TYPES.map((resource) => `
    <div class="resource-chip"><span><img src="/static/assets/resource_${resource}.png" alt=""> ${RESOURCE_LABELS[resource]}</span><strong>${resources[resource] || 0}</strong></div>
  `).join("");
  const cards = state.you?.dev_cards || [];
  el("devCards").innerHTML = cards.length ? cards.map((card) => renderDevCard(card)).join("") : `<p class="subtle">No development cards.</p>`;
  el("devCards").querySelectorAll("[data-play-dev]").forEach((button) => {
    button.addEventListener("click", () => playDev(button.dataset.playDev, button.dataset.devType));
  });
}

function renderDevCard(card) {
  const playable = state.current_player_id === playerId && state.turn_stage === "main" && card.type !== "victory_point" && card.bought_turn !== state.turn_number;
  return `<div class="dev-card">
    <span><img src="/static/assets/dev_${card.type}.png" alt=""> ${DEV_LABELS[card.type] || card.type}</span>
    ${card.type === "victory_point" ? "<small>auto VP</small>" : `<button data-play-dev="${card.id}" data-dev-type="${card.type}" ${playable ? "" : "disabled"}>Play</button>`}
  </div>`;
}

function playDev(cardId, type) {
  if (type === "year_of_plenty") {
    const answer = prompt("Choose exactly two resources, comma-separated. Example: lumber,ore or grain,grain");
    if (!answer) return;
    const resources = {};
    for (const name of answer.split(",").map((item) => item.trim().toLowerCase())) {
      if (!RESOURCE_TYPES.includes(name)) return toast(`Unknown resource: ${name}`);
      resources[name] = (resources[name] || 0) + 1;
    }
    emit("play_dev_card", {card_id: cardId, payload: {resources}});
  } else if (type === "monopoly") {
    const resource = prompt("Monopoly resource: lumber, brick, wool, grain, or ore")?.trim().toLowerCase();
    if (!RESOURCE_TYPES.includes(resource)) return toast("Choose a valid resource.");
    emit("play_dev_card", {card_id: cardId, payload: {resource}});
  } else {
    emit("play_dev_card", {card_id: cardId});
  }
}

function renderDiscard() {
  const required = state.pending_discards?.[playerId] || 0;
  el("discardPanel").classList.toggle("hidden", !required);
  if (!required) return;
  el("discardNeed").textContent = `Discard exactly ${required} cards.`;
  renderInputGrid(el("discardInputs"), "discard", state.you?.resources || {});
}

function renderRobberPanel() {
  const show = state.turn_stage === "move_robber" && state.pending_robber?.player_id === playerId;
  el("robberPanel").classList.toggle("hidden", !show);
  if (!show) {
    pendingRobberHexId = null;
    return;
  }
  renderRobberVictims();
}

function renderRobberVictims() {
  const container = el("robberVictims");
  if (!pendingRobberHexId) {
    container.innerHTML = `<p class="subtle">No tile selected yet.</p>`;
    return;
  }
  const victims = playersOnHex(pendingRobberHexId).filter((id) => id !== playerId && (state.players.find((p) => p.id === id)?.resource_count || 0) > 0);
  const buttons = victims.map((id) => {
    const player = state.players.find((item) => item.id === id);
    return `<button data-rob-victim="${id}">Steal from ${escapeHtml(player?.name || "player")}</button>`;
  }).join("");
  container.innerHTML = `<div class="button-grid">${buttons}<button data-rob-victim="">Move only</button></div>`;
  container.querySelectorAll("[data-rob-victim]").forEach((button) => {
    button.addEventListener("click", () => emit("move_robber", {hex_id: pendingRobberHexId, victim_id: button.dataset.robVictim || null}));
  });
}

function renderTrades() {
  const rates = state.you?.bank_rates || {};
  el("bankRates").textContent = RESOURCE_TYPES.map((resource) => `${RESOURCE_LABELS[resource]} ${rates[resource] || 4}:1`).join(" · ");
  el("offersList").innerHTML = (state.trade_offers || []).map((offer) => {
    const proposer = state.players.find((player) => player.id === offer.from_player_id);
    return `<div class="offer-card">
      <span><strong>${escapeHtml(proposer?.name || "Player")}</strong>: gives ${formatResources(offer.give)} for ${formatResources(offer.receive)}</span>
      ${offer.from_player_id === playerId ? `<button data-cancel-offer="${offer.id}">Cancel</button>` : `<button data-accept-offer="${offer.id}">Accept</button>`}
    </div>`;
  }).join("");
  el("offersList").querySelectorAll("[data-accept-offer]").forEach((button) => button.addEventListener("click", () => emit("accept_trade_offer", {offer_id: button.dataset.acceptOffer})));
  el("offersList").querySelectorAll("[data-cancel-offer]").forEach((button) => button.addEventListener("click", () => emit("cancel_trade_offer", {offer_id: button.dataset.cancelOffer})));
}

function renderLog() {
  const logLines = (state.chat || []).map((item) => `${item.name}: ${item.text}`).concat(state.log || []);
  el("logList").innerHTML = logLines.slice(-80).map((line) => `<div>${escapeHtml(line)}</div>`).join("");
}

function renderInputGrid(container, prefix, maxValues = null) {
  container.innerHTML = RESOURCE_TYPES.map((resource) => `
    <label>${RESOURCE_LABELS[resource].slice(0, 3)}<input data-prefix="${prefix}" data-resource="${resource}" type="number" min="0" ${maxValues ? `max="${maxValues[resource] || 0}"` : ""} value="0"></label>
  `).join("");
}

function readInputs(prefix) {
  const result = {};
  document.querySelectorAll(`[data-prefix="${prefix}"]`).forEach((input) => {
    result[input.dataset.resource] = Math.max(0, parseInt(input.value || "0", 10));
  });
  return result;
}

function setupCanvas() {
  const resizeObserver = new ResizeObserver(() => { resizeCanvas(); fitBoard(); drawBoard(); });
  resizeObserver.observe(canvas.parentElement);
  canvas.addEventListener("pointerdown", (event) => {
    pointer.down = true;
    pointer.moved = false;
    pointer.x = pointer.startX = event.clientX;
    pointer.y = pointer.startY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();
    pointer.hover = hitTest(event.clientX - rect.left, event.clientY - rect.top);
    if (pointer.down) {
      const dx = event.clientX - pointer.x;
      const dy = event.clientY - pointer.y;
      if (Math.hypot(event.clientX - pointer.startX, event.clientY - pointer.startY) > 4) pointer.moved = true;
      view.x += dx;
      view.y += dy;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    }
    drawBoard();
  });
  canvas.addEventListener("pointerup", (event) => {
    pointer.down = false;
    if (!pointer.moved) {
      const rect = canvas.getBoundingClientRect();
      handleBoardClick(event.clientX - rect.left, event.clientY - rect.top);
    }
  });
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouse = {x: event.clientX - rect.left, y: event.clientY - rect.top};
    const before = screenToWorld(mouse.x, mouse.y);
    const factor = Math.exp(-event.deltaY * 0.001);
    view.scale = clamp(view.scale * factor, 34, 220);
    const after = worldToScreen(before.x, before.y);
    view.x += mouse.x - after.x;
    view.y += mouse.y - after.y;
    drawBoard();
  }, {passive: false});
}

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function fitBoard(force = false) {
  if (!state?.board || (!force && view.fittedGame === state.game_id)) return;
  const rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const vertices = state.board.vertices;
  const xs = vertices.map((vertex) => vertex.x);
  const ys = vertices.map((vertex) => vertex.y);
  const minX = Math.min(...xs) - 1;
  const maxX = Math.max(...xs) + 1;
  const minY = Math.min(...ys) - 1;
  const maxY = Math.max(...ys) + 1;
  view.scale = Math.min(rect.width / (maxX - minX), rect.height / (maxY - minY)) * 0.94;
  view.x = rect.width / 2 - ((minX + maxX) / 2) * view.scale;
  view.y = rect.height / 2 - ((minY + maxY) / 2) * view.scale;
  view.fittedGame = state.game_id;
}

function drawBoard() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  if (!state?.board) return;
  const sea = assets.terrain_sea;
  if (sea.complete) {
    const pattern = ctx.createPattern(sea, "repeat");
    ctx.fillStyle = pattern || "#16384a";
  } else {
    ctx.fillStyle = "#16384a";
  }
  ctx.fillRect(0, 0, rect.width, rect.height);

  for (const hex of state.board.hexes) drawHex(hex);
  drawPorts();
  drawRoads();
  drawBuildings();
  drawRobber();
  drawHover();
}

function drawHex(hex) {
  const points = hex.vertices.map((id) => worldToScreenVertex(id));
  pathPolygon(points);
  ctx.save();
  ctx.clip();
  const image = assets[`terrain_${hex.terrain}`];
  const center = worldToScreen(hex.x, hex.y);
  const radius = view.scale * 1.02;
  if (image?.complete) ctx.drawImage(image, center.x - radius, center.y - radius, radius * 2, radius * 2);
  else {
    ctx.fillStyle = TERRAIN_COLORS[hex.terrain] || "#999";
    ctx.fill();
  }
  ctx.restore();
  ctx.strokeStyle = "rgba(255,255,255,.22)";
  ctx.lineWidth = Math.max(1, view.scale * 0.018);
  ctx.stroke();
  if (hex.number) drawNumberToken(hex, center);
}

function drawNumberToken(hex, center) {
  const radius = clamp(view.scale * 0.25, 15, 28);
  const token = assets.number_token;
  if (token.complete) ctx.drawImage(token, center.x - radius, center.y - radius, radius * 2, radius * 2);
  else {
    ctx.fillStyle = "#f7f0d0";
    ctx.beginPath(); ctx.arc(center.x, center.y, radius, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = [6, 8].includes(hex.number) ? "#c1121f" : "#3b2f2f";
  ctx.font = `800 ${Math.round(radius * 0.9)}px system-ui`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(hex.number, center.x, center.y - radius * 0.08);
  const dots = {2:1, 3:2, 4:3, 5:4, 6:5, 8:5, 9:4, 10:3, 11:2, 12:1}[hex.number] || 0;
  ctx.fillStyle = [6, 8].includes(hex.number) ? "#c1121f" : "#5c4438";
  const start = center.x - (dots - 1) * 3;
  for (let i = 0; i < dots; i++) {
    ctx.beginPath(); ctx.arc(start + i * 6, center.y + radius * 0.48, 1.7, 0, Math.PI * 2); ctx.fill();
  }
}

function drawPorts() {
  ctx.font = `700 ${clamp(view.scale * 0.12, 11, 16)}px system-ui`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (const port of state.board.ports || []) {
    const edge = edgeById(port.edge_id);
    if (!edge) continue;
    const a = vertexById(edge.vertices[0]);
    const b = vertexById(edge.vertices[1]);
    const mid = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2};
    const length = Math.hypot(mid.x, mid.y) || 1;
    const out = {x: mid.x / length, y: mid.y / length};
    const start = worldToScreen(mid.x, mid.y);
    const end = worldToScreen(mid.x + out.x * 0.55, mid.y + out.y * 0.55);
    ctx.strokeStyle = "rgba(255,255,255,.55)";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke();
    ctx.fillStyle = "rgba(7,13,18,.78)";
    roundRect(end.x - 28, end.y - 13, 56, 26, 9); ctx.fill();
    ctx.fillStyle = "#f4f1de";
    ctx.fillText(port.kind === "3:1" ? "3:1" : `2:${shortResource(port.kind)}`, end.x, end.y);
  }
}

function drawRoads() {
  for (const [edgeId, ownerId] of Object.entries(state.pieces.roads || {})) {
    const edge = edgeById(edgeId);
    const owner = state.players.find((player) => player.id === ownerId);
    if (!edge || !owner) continue;
    const a = worldToScreenVertex(edge.vertices[0]);
    const b = worldToScreenVertex(edge.vertices[1]);
    ctx.strokeStyle = "rgba(0,0,0,.55)";
    ctx.lineWidth = clamp(view.scale * 0.18, 9, 20);
    ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    ctx.strokeStyle = owner.color_hex;
    ctx.lineWidth = clamp(view.scale * 0.12, 6, 14);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }
}

function drawBuildings() {
  for (const [vertexId, building] of Object.entries(state.pieces.buildings || {})) {
    const owner = state.players.find((player) => player.id === building.player_id);
    if (!owner) continue;
    const p = worldToScreenVertex(vertexId);
    const size = building.type === "city" ? clamp(view.scale * 0.38, 24, 42) : clamp(view.scale * 0.3, 19, 34);
    ctx.save();
    ctx.fillStyle = owner.color_hex;
    ctx.strokeStyle = "rgba(0,0,0,.78)";
    ctx.lineWidth = 3;
    if (building.type === "city") drawCityShape(p.x, p.y, size);
    else drawSettlementShape(p.x, p.y, size);
    ctx.fill(); ctx.stroke();
    ctx.restore();
  }
}

function drawSettlementShape(x, y, size) {
  ctx.beginPath();
  ctx.moveTo(x, y - size * 0.5);
  ctx.lineTo(x + size * 0.48, y - size * 0.08);
  ctx.lineTo(x + size * 0.38, y + size * 0.5);
  ctx.lineTo(x - size * 0.38, y + size * 0.5);
  ctx.lineTo(x - size * 0.48, y - size * 0.08);
  ctx.closePath();
}

function drawCityShape(x, y, size) {
  ctx.beginPath();
  ctx.moveTo(x - size * 0.5, y + size * 0.42);
  ctx.lineTo(x - size * 0.5, y - size * 0.18);
  ctx.lineTo(x - size * 0.2, y - size * 0.18);
  ctx.lineTo(x - size * 0.2, y - size * 0.52);
  ctx.lineTo(x + size * 0.12, y - size * 0.52);
  ctx.lineTo(x + size * 0.12, y - size * 0.05);
  ctx.lineTo(x + size * 0.5, y - size * 0.05);
  ctx.lineTo(x + size * 0.5, y + size * 0.42);
  ctx.closePath();
}

function drawRobber() {
  const hex = state.board.hexes.find((item) => item.id === state.robber_hex_id);
  if (!hex) return;
  const p = worldToScreen(hex.x, hex.y);
  const size = clamp(view.scale * 0.45, 28, 52);
  const image = assets.icon_robber;
  if (image?.complete) ctx.drawImage(image, p.x - size / 2, p.y - size * 0.88, size, size);
  else {
    ctx.fillStyle = "#222";
    ctx.beginPath(); ctx.arc(p.x, p.y - size * .35, size * .32, 0, Math.PI * 2); ctx.fill();
  }
}

function drawHover() {
  if (!pointer.hover || !selectedAction) return;
  ctx.save();
  ctx.strokeStyle = "#f4a261";
  ctx.fillStyle = "rgba(244,162,97,.22)";
  ctx.lineWidth = 3;
  if (["settlement", "city"].includes(selectedAction) && pointer.hover.vertex) {
    const p = worldToScreenVertex(pointer.hover.vertex);
    ctx.beginPath(); ctx.arc(p.x, p.y, 18, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  } else if (selectedAction === "road" && pointer.hover.edge) {
    const edge = edgeById(pointer.hover.edge);
    const a = worldToScreenVertex(edge.vertices[0]);
    const b = worldToScreenVertex(edge.vertices[1]);
    ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  } else if (selectedAction === "robber" && pointer.hover.hex) {
    const hex = state.board.hexes.find((item) => item.id === pointer.hover.hex);
    pathPolygon(hex.vertices.map((id) => worldToScreenVertex(id))); ctx.fill(); ctx.stroke();
  }
  ctx.restore();
}

function handleBoardClick(x, y) {
  if (!state) return;
  const hit = hitTest(x, y);
  if (state.phase === "setup" && state.setup?.player_id === playerId) {
    const action = state.setup.action;
    const target = action === "road" ? hit.edge : hit.vertex;
    if (target) emit("build", {type: action, target_id: target});
    return;
  }
  if (state.turn_stage === "move_robber" && state.pending_robber?.player_id === playerId) {
    if (hit.hex) {
      pendingRobberHexId = hit.hex;
      renderRobberVictims();
      drawBoard();
    }
    return;
  }
  if (!selectedAction || state.current_player_id !== playerId) return;
  if (selectedAction === "road" && hit.edge) emit("build", {type: "road", target_id: hit.edge});
  if (selectedAction === "settlement" && hit.vertex) emit("build", {type: "settlement", target_id: hit.vertex});
  if (selectedAction === "city" && hit.vertex) emit("build", {type: "city", target_id: hit.vertex});
}

function hitTest(x, y) {
  const vertex = nearestVertex(x, y, 24);
  const edge = nearestEdge(x, y, 18);
  const hex = nearestHex(x, y);
  return {vertex, edge, hex};
}

function nearestVertex(x, y, threshold) {
  if (!state?.board) return null;
  let best = null;
  let bestDistance = threshold;
  for (const vertex of state.board.vertices) {
    const p = worldToScreen(vertex.x, vertex.y);
    const distance = Math.hypot(p.x - x, p.y - y);
    if (distance < bestDistance) { best = vertex.id; bestDistance = distance; }
  }
  return best;
}

function nearestEdge(x, y, threshold) {
  if (!state?.board) return null;
  let best = null;
  let bestDistance = threshold;
  for (const edge of state.board.edges) {
    const a = worldToScreenVertex(edge.vertices[0]);
    const b = worldToScreenVertex(edge.vertices[1]);
    const distance = distanceToSegment({x, y}, a, b);
    if (distance < bestDistance) { best = edge.id; bestDistance = distance; }
  }
  return best;
}

function nearestHex(x, y) {
  if (!state?.board) return null;
  let best = null;
  let bestDistance = Infinity;
  for (const hex of state.board.hexes) {
    const p = worldToScreen(hex.x, hex.y);
    const distance = Math.hypot(p.x - x, p.y - y);
    if (distance < bestDistance) { best = hex.id; bestDistance = distance; }
  }
  return bestDistance < view.scale * 0.92 ? best : null;
}

function distanceToSegment(p, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length2 = dx * dx + dy * dy;
  const t = length2 ? clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) / length2, 0, 1) : 0;
  const x = a.x + t * dx;
  const y = a.y + t * dy;
  return Math.hypot(p.x - x, p.y - y);
}

function playersOnHex(hexId) {
  const hex = state.board.hexes.find((item) => item.id === hexId);
  const ids = new Set();
  for (const vertexId of hex?.vertices || []) {
    const building = state.pieces.buildings[vertexId];
    if (building) ids.add(building.player_id);
  }
  return [...ids];
}

function vertexById(id) { return state.board.vertices.find((vertex) => vertex.id === id); }
function edgeById(id) { return state.board.edges.find((edge) => edge.id === id); }
function worldToScreenVertex(id) { const vertex = vertexById(id); return worldToScreen(vertex.x, vertex.y); }
function worldToScreen(x, y) { return {x: view.x + x * view.scale, y: view.y + y * view.scale}; }
function screenToWorld(x, y) { return {x: (x - view.x) / view.scale, y: (y - view.y) / view.scale}; }
function pathPolygon(points) { ctx.beginPath(); points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y)); ctx.closePath(); }
function roundRect(x, y, width, height, radius) { ctx.beginPath(); ctx.roundRect(x, y, width, height, radius); }
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function shortResource(resource) { return {lumber: "Lu", brick: "Br", wool: "Wo", grain: "Gr", ore: "Or"}[resource] || resource.slice(0, 2); }

function animateDice(roll) {
  const strip = el("diceStrip");
  const pairs = [];
  for (let index = 0; index < 11; index++) pairs.push([randDie(), randDie()]);
  pairs.push([roll.die1, roll.die2]);
  strip.innerHTML = pairs.map((pair, index) => dicePairHtml(pair, index === 0)).join("");
  let active = 0;
  const timer = setInterval(() => {
    const nodes = strip.querySelectorAll(".dice-pair");
    nodes.forEach((node) => node.classList.remove("active"));
    nodes[Math.min(active, nodes.length - 1)]?.classList.add("active");
    active += 1;
    if (active > pairs.length) clearInterval(timer);
  }, 70);
}

function dicePairHtml(pair, active = false) {
  return `<div class="dice-pair ${active ? "active" : ""}"><img src="/static/assets/dice_${pair[0]}.png" alt="${pair[0]}"><img src="/static/assets/dice_${pair[1]}.png" alt="${pair[1]}"></div>`;
}

function randDie() { return Math.floor(Math.random() * 6) + 1; }
function formatResources(resources) { return RESOURCE_TYPES.filter((resource) => resources[resource]).map((resource) => `${resources[resource]} ${RESOURCE_LABELS[resource]}`).join(", ") || "nothing"; }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char])); }
function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  el("toast").appendChild(node);
  setTimeout(() => node.remove(), 4200);
}
function readJson(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (_) { return fallback; } }
function writeJson(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
function savePlayerForGame(id, pid) { savedPlayers[id] = pid; writeJson("catanPlayers", savedPlayers); }
