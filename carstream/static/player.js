"use strict";

const form = document.querySelector("#connect-form");
const tokenInput = document.querySelector("#token");
const connectButton = document.querySelector("#connect");
const disconnectButton = document.querySelector("#disconnect");
const statusText = document.querySelector("#status");
const sourceText = document.querySelector("#source");
const video = document.querySelector("#video");
let currentSession = null;
let watchingRequested = false;
let reconnectTimer = null;
let reconnectDelay = 1000;

function stopSession(session, reason, retry = true) {
  if (!session || session !== currentSession) return;
  currentSession = null;
  clearTimeout(session.timeout);
  clearInterval(session.videoMonitor);
  if (session.peer) session.peer.close();
  if (session.socket) session.socket.close();
  video.srcObject = null;
  if (!retry) watchingRequested = false;
  connectButton.disabled = watchingRequested;
  disconnectButton.disabled = !watchingRequested;
  statusText.textContent = reason;
  if (watchingRequested) {
    statusText.textContent += ` Reconnecting in ${reconnectDelay / 1000}s...`;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      startSession();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  }
}

function stopWatching(reason) {
  watchingRequested = false;
  clearTimeout(reconnectTimer);
  reconnectTimer = null;
  reconnectDelay = 1000;
  if (currentSession) stopSession(currentSession, reason, false);
  connectButton.disabled = false;
  disconnectButton.disabled = true;
  statusText.textContent = reason;
}

function checkVideoProgress(session) {
  if (session !== currentSession || session.peer?.connectionState !== "connected") return;
  const now = performance.now();
  if (session.playbackBlocked || (video.paused && video.readyState >= 2)) {
    session.lastProgressAt = now;
    session.playbackStartedAt = null;
    return;
  }
  const progress = video.getVideoPlaybackQuality
    ? video.getVideoPlaybackQuality().totalVideoFrames
    : video.currentTime;
  if (progress !== session.lastVideoProgress) {
    session.lastVideoProgress = progress;
    session.lastProgressAt = now;
    session.playbackStartedAt ??= now;
    // A single recovered frame is not enough to reset repeated-failure backoff.
    if (now - session.playbackStartedAt >= 10000) reconnectDelay = 1000;
  } else if (now - session.lastProgressAt >= 15000) {
    stopSession(session, "Video stopped advancing.");
  }
}

async function handleMessage(session, message) {
  if (session !== currentSession) return;
  if (message.type === "error") {
    stopSession(session, message.message, message.message !== "Invalid access token");
    return;
  }
  if (message.type === "ready") {
    sourceText.textContent = message.source === "test"
      ? "TEST PATTERN - not the actual camera"
      : "RTSP camera";
    session.peer = new RTCPeerConnection({
      iceServers: message.iceServers,
      iceTransportPolicy: message.iceTransportPolicy,
      bundlePolicy: "max-bundle",
    });
    session.peer.onicecandidate = (event) => {
      if (session !== currentSession || !event.candidate) return;
      session.socket.send(JSON.stringify({
        type: "ice",
        candidate: event.candidate.candidate,
        sdpMLineIndex: event.candidate.sdpMLineIndex,
      }));
    };
    session.peer.ontrack = (event) => {
      if (session !== currentSession) return;
      video.srcObject = event.streams[0] || new MediaStream([event.track]);
      video.play().catch((error) => {
        if (session !== currentSession) return;
        if (error.name === "NotAllowedError") {
          session.playbackBlocked = true;
          statusText.textContent = "Connected. Press play on the video.";
        } else {
          stopSession(session, "Video playback failed.");
        }
      });
    };
    session.peer.onconnectionstatechange = () => {
      if (session !== currentSession) return;
      const state = session.peer.connectionState;
      statusText.textContent = `WebRTC: ${state}`;
      if (state === "connected") {
        clearTimeout(session.timeout);
        session.lastProgressAt = performance.now();
      }
      if (state === "failed") stopSession(session, "WebRTC connection failed.");
    };
    return;
  }
  if (message.type === "ice") {
    const candidate = {candidate: message.candidate, sdpMLineIndex: message.sdpMLineIndex};
    if (session.peer && session.peer.remoteDescription) {
      await session.peer.addIceCandidate(candidate);
    } else {
      session.pendingCandidates.push(candidate);
    }
    return;
  }
  if (message.type === "offer") {
    await session.peer.setRemoteDescription({type: "offer", sdp: message.sdp});
    if (session !== currentSession) return;
    for (const candidate of session.pendingCandidates) {
      await session.peer.addIceCandidate(candidate);
    }
    session.pendingCandidates = [];
    const answer = await session.peer.createAnswer();
    await session.peer.setLocalDescription(answer);
    if (session !== currentSession) return;
    session.socket.send(JSON.stringify({type: "answer", sdp: session.peer.localDescription.sdp}));
  }
}

function startSession() {
  if (!watchingRequested || currentSession) return;
  const session = {
    peer: null,
    pendingCandidates: [],
    messages: Promise.resolve(),
    lastVideoProgress: 0,
    lastProgressAt: performance.now(),
    playbackStartedAt: null,
    playbackBlocked: false,
  };
  currentSession = session;
  connectButton.disabled = true;
  disconnectButton.disabled = false;
  statusText.textContent = "Connecting...";
  const websocketScheme = location.protocol === "https:" ? "wss:" : "ws:";
  session.socket = new WebSocket(`${websocketScheme}//${location.host}/ws`);
  session.timeout = setTimeout(() => stopSession(session, "Connection timed out."), 65000);
  session.videoMonitor = setInterval(() => checkVideoProgress(session), 2000);
  session.socket.onopen = () => {
    if (session !== currentSession) return;
    session.socket.send(JSON.stringify({type: "auth", token: tokenInput.value}));
  };
  session.socket.onmessage = (event) => {
    // Serialize SDP/ICE processing; async onmessage callbacks otherwise overlap.
    session.messages = session.messages
      .then(() => handleMessage(session, JSON.parse(event.data)))
      .catch((error) => stopSession(session, error.message));
  };
  session.socket.onerror = () => stopSession(session, "Signaling connection failed.");
  session.socket.onclose = () => stopSession(session, "Signaling connection closed.");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (watchingRequested) return;
  if (!window.RTCPeerConnection) {
    statusText.textContent = "WebRTC is unavailable in this browser. Use a current browser over HTTPS.";
    return;
  }
  watchingRequested = true;
  startSession();
});

video.addEventListener("playing", () => {
  if (currentSession) {
    currentSession.playbackBlocked = false;
    currentSession.lastProgressAt = performance.now();
  }
});

disconnectButton.addEventListener("click", () => stopWatching("Disconnected."));
window.addEventListener("pagehide", () => stopWatching("Disconnected."));
