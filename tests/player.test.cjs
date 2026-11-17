const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {resolve} = require("node:path");
const {test} = require("node:test");
const {runInNewContext} = require("node:vm");

const playerSource = readFileSync(resolve(__dirname, "../carstream/static/player.js"), "utf8");

function createPlayer() {
  let currentMilliseconds = 0;
  let nextTimerIdentifier = 1;
  const timers = new Map();
  const elements = new Map();
  const sockets = [];
  const peers = [];
  const windowListeners = new Map();

  for (const selector of ["#connect-form", "#token", "#connect", "#disconnect", "#status", "#source", "#video"]) {
    elements.set(selector, {
      listeners: new Map(),
      value: "test-access-token",
      textContent: "",
      disabled: false,
      currentTime: 0,
      paused: false,
      readyState: 0,
      srcObject: null,
      play: () => Promise.resolve(),
      addEventListener(eventName, listener) { this.listeners.set(eventName, listener); },
    });
  }

  function scheduleTimer(callback, delay, interval = null) {
    const timerIdentifier = nextTimerIdentifier++;
    timers.set(timerIdentifier, {callback, deadline: currentMilliseconds + delay, interval});
    return timerIdentifier;
  }

  class FakeWebSocket {
    constructor() {
      this.messages = [];
      this.closed = false;
      sockets.push(this);
    }
    send(message) { this.messages.push(JSON.parse(message)); }
    close() { this.closed = true; this.onclose?.(); }
    async receive(payload) {
      this.onmessage({data: JSON.stringify(payload)});
      await flushMessages();
    }
  }

  class FakePeerConnection {
    constructor() {
      this.connectionState = "new";
      peers.push(this);
    }
    close() { this.closed = true; }
    connect() {
      this.connectionState = "connected";
      this.onconnectionstatechange();
    }
  }

  async function flushMessages() {
    for (let iterationNumber = 0; iterationNumber < 10; iterationNumber++) await Promise.resolve();
  }

  runInNewContext(playerSource, {
    document: {querySelector: (selector) => elements.get(selector)},
    window: {
      RTCPeerConnection: FakePeerConnection,
      addEventListener: (eventName, listener) => windowListeners.set(eventName, listener),
    },
    location: {protocol: "http:", host: "localhost:18080"},
    RTCPeerConnection: FakePeerConnection,
    WebSocket: FakeWebSocket,
    performance: {now: () => currentMilliseconds},
    setTimeout: (callback, delay) => scheduleTimer(callback, delay),
    clearTimeout: (timerIdentifier) => timers.delete(timerIdentifier),
    setInterval: (callback, delay) => scheduleTimer(callback, delay, delay),
    clearInterval: (timerIdentifier) => timers.delete(timerIdentifier),
  });

  function advanceTime(milliseconds) {
    const targetMilliseconds = currentMilliseconds + milliseconds;
    while (true) {
      const nextTimer = [...timers.entries()]
        .filter(([_identifier, timer]) => timer.deadline <= targetMilliseconds)
        .sort((firstEntry, secondEntry) => firstEntry[1].deadline - secondEntry[1].deadline)[0];
      if (!nextTimer) break;
      const [timerIdentifier, timer] = nextTimer;
      currentMilliseconds = timer.deadline;
      if (timer.interval === null) timers.delete(timerIdentifier);
      else timer.deadline += timer.interval;
      timer.callback();
    }
    currentMilliseconds = targetMilliseconds;
  }

  function submit() {
    elements.get("#connect-form").listeners.get("submit")({preventDefault() {}});
  }

  async function connect() {
    submit();
    const socket = sockets.at(-1);
    socket.onopen();
    await socket.receive({type: "ready", source: "rtsp", iceServers: [], iceTransportPolicy: "all"});
    peers.at(-1).connect();
    return socket;
  }

  return {
    elements, sockets, peers, advanceTime, submit, connect, flushMessages,
    disconnect: () => elements.get("#disconnect").listeners.get("click")(),
    hide: () => windowListeners.get("pagehide")(),
  };
}

test("one Connect retries signaling failures with capped backoff and no duplicate attempts", async () => {
  const player = createPlayer();
  await player.connect();
  const delays = [1000, 2000, 4000, 8000, 16000, 30000, 30000];
  for (const delay of delays) {
    const socket = player.sockets.at(-1);
    const previousCount = player.sockets.length;
    socket.onerror();
    socket.onclose();
    player.advanceTime(delay - 1);
    assert.equal(player.sockets.length, previousCount);
    player.advanceTime(1);
    assert.equal(player.sockets.length, previousCount + 1);
    assert.equal(player.elements.get("#disconnect").disabled, false);
  }
});

test("media errors retry, but an invalid token stops retries until another Connect", async () => {
  const player = createPlayer();
  const socket = await player.connect();
  await socket.receive({type: "error", message: "Media pipeline failed"});
  player.advanceTime(1000);
  assert.equal(player.sockets.length, 2);
  await player.sockets.at(-1).receive({type: "error", message: "Invalid access token"});
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 2);
  assert.equal(player.elements.get("#connect").disabled, false);
  player.submit();
  assert.equal(player.sockets.length, 3);
});

test("Disconnect cancels pending recovery and closes an active attempt", async () => {
  const player = createPlayer();
  await player.connect();
  player.sockets[0].onclose();
  player.disconnect();
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 1);
  await player.connect();
  player.disconnect();
  assert.equal(player.sockets[1].closed, true);
  assert.equal(player.peers[1].closed, true);
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 2);
});

test("continuous playback survives minutes, but a connected frozen picture recovers", async () => {
  const player = createPlayer();
  await player.connect();
  const video = player.elements.get("#video");
  let decodedFrames = 0;
  video.getVideoPlaybackQuality = () => ({totalVideoFrames: decodedFrames});
  video.readyState = 4;
  for (let elapsedSeconds = 0; elapsedSeconds < 300; elapsedSeconds += 2) {
    video.currentTime += 2;
    decodedFrames += 40;
    player.advanceTime(2000);
  }
  assert.equal(player.sockets.length, 1);
  video.currentTime += 18;
  player.advanceTime(18000);
  assert.equal(player.sockets.length, 2);
  assert.equal(player.peers[0].closed, true);
});

test("sustained playback resets failure backoff, while a brief recovered frame does not", async () => {
  const player = createPlayer();
  await player.connect();
  player.sockets[0].onclose();
  player.advanceTime(1000);
  await player.connect();
  player.elements.get("#video").currentTime = 1;
  player.advanceTime(2000);
  player.sockets[1].onclose();
  player.advanceTime(1999);
  assert.equal(player.sockets.length, 2);
  player.advanceTime(1);
  await player.connect();
  for (let elapsedSeconds = 0; elapsedSeconds < 14; elapsedSeconds += 2) {
    player.elements.get("#video").currentTime += 2;
    player.advanceTime(2000);
  }
  player.sockets[2].onclose();
  player.advanceTime(1000);
  assert.equal(player.sockets.length, 4);
});

test("user pause and autoplay rejection do not cause repeated reconnections", async () => {
  const player = createPlayer();
  await player.connect();
  const video = player.elements.get("#video");
  video.readyState = 4;
  video.paused = true;
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 1);
  video.paused = false;
  video.readyState = 0;
  video.play = () => Promise.reject(Object.assign(new Error("autoplay blocked"), {name: "NotAllowedError"}));
  player.peers[0].ontrack({streams: [{}]});
  await player.flushMessages();
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 1);
  assert.match(player.elements.get("#status").textContent, /Press play/);
  video.listeners.get("playing")();
  player.advanceTime(18000);
  assert.equal(player.sockets.length, 2);
});

test("late play rejection cannot overwrite a disconnected or replacement session", async () => {
  const player = createPlayer();
  await player.connect();
  let rejectPlayback;
  player.elements.get("#video").play = () => new Promise((_resolve, reject) => { rejectPlayback = reject; });
  player.peers[0].ontrack({streams: [{}]});
  player.disconnect();
  rejectPlayback(new Error("play interrupted"));
  await player.flushMessages();
  assert.equal(player.elements.get("#status").textContent, "Disconnected.");
});

test("initial connection timeout recovers, while leaving the page cancels recovery", () => {
  const player = createPlayer();
  player.submit();
  player.advanceTime(66000);
  assert.equal(player.sockets.length, 2);
  player.hide();
  player.advanceTime(120000);
  assert.equal(player.sockets.length, 2);
  assert.equal(player.sockets[1].closed, true);
});
