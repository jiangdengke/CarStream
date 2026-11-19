"use strict";

const pageUrl = new URL(location.href);
if (pageUrl.searchParams.has("ui")) {
  // Remove the retired UI-check marker without reloading the player.
  pageUrl.searchParams.delete("ui");
  history.replaceState(history.state, "", pageUrl.pathname + pageUrl.search + pageUrl.hash);
}

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
  if (session.videoFrameCallback !== null && video.cancelVideoFrameCallback) {
    video.cancelVideoFrameCallback(session.videoFrameCallback);
  }
  if (session.peer) session.peer.close();
  if (session.socket) session.socket.close();
  video.srcObject = null;
  if (!retry) watchingRequested = false;
  connectButton.disabled = watchingRequested;
  disconnectButton.disabled = !watchingRequested;
  statusText.textContent = reason;
  if (watchingRequested) {
    statusText.textContent += ` ${reconnectDelay / 1000} 秒后自动重连...`;
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

function observePresentedFrames(session) {
  if (!video.requestVideoFrameCallback) return;
  session.usesVideoFrameCallbacks = true;
  const recordPresentedFrame = () => {
    if (session !== currentSession) return;
    session.presentedFrames += 1;
    session.videoFrameCallback = video.requestVideoFrameCallback(recordPresentedFrame);
  };
  session.videoFrameCallback = video.requestVideoFrameCallback(recordPresentedFrame);
}

function readVideoProgress(session) {
  if (session.usesVideoFrameCallbacks) return session.presentedFrames;
  // Firefox can keep the playback-quality counter at zero for a live MediaStream.
  const decodedFrames = video.getVideoPlaybackQuality?.().totalVideoFrames;
  return decodedFrames > 0 ? decodedFrames : video.currentTime;
}

async function checkVideoProgress(session) {
  if (session !== currentSession || session.peer?.connectionState !== "connected") return;
  if (session.checkingVideoProgress) return;
  let decodedFrames = null;
  session.checkingVideoProgress = true;
  try {
    if (session.peer.getStats) {
      const reports = await session.peer.getStats();
      for (const report of reports.values()) {
        if (report.type === "inbound-rtp" && report.kind === "video"
            && typeof report.framesDecoded === "number") {
          decodedFrames = report.framesDecoded;
          break;
        }
      }
    }
  } catch {
    // Presentation monitoring still works when receiver statistics are unavailable.
  } finally {
    session.checkingVideoProgress = false;
  }
  if (session !== currentSession || session.peer?.connectionState !== "connected") return;
  const now = performance.now();
  if (session.playbackBlocked || (video.paused && video.readyState >= 2)) {
    session.lastProgressAt = now;
    session.playbackStartedAt = null;
    return;
  }
  const progress = readVideoProgress(session);
  // A browser may suppress presentation callbacks while it continues decoding.
  const decoderAdvanced = decodedFrames !== null && decodedFrames > session.lastDecodedFrames;
  if (decodedFrames !== null) session.lastDecodedFrames = decodedFrames;
  if (progress !== session.lastVideoProgress || decoderAdvanced) {
    session.lastVideoProgress = progress;
    session.lastProgressAt = now;
    session.playbackStartedAt ??= now;
    // A single recovered frame is not enough to reset repeated-failure backoff.
    if (now - session.playbackStartedAt >= 10000) reconnectDelay = 1000;
  } else if (now - session.lastProgressAt >= 15000) {
    stopSession(session, "画面已停滞。");
  }
}

async function handleMessage(session, message) {
  if (session !== currentSession) return;
  if (message.type === "error") {
    const invalidToken = message.message === "Invalid access token";
    stopSession(session, invalidToken ? "访问令牌不正确，请重新输入。" : "视频连接异常。", !invalidToken);
    return;
  }
  if (message.type === "ready") {
    sourceText.hidden = message.source !== "test";
    sourceText.textContent = message.source === "test"
      ? "测试画面，非真实摄像头"
      : "";
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
      observePresentedFrames(session);
      video.play().catch((error) => {
        if (session !== currentSession) return;
        if (error.name === "NotAllowedError") {
          session.playbackBlocked = true;
          statusText.textContent = "已连接，请点击视频播放。";
        } else {
          stopSession(session, "视频播放失败。");
        }
      });
    };
    session.peer.onconnectionstatechange = () => {
      if (session !== currentSession) return;
      const state = session.peer.connectionState;
      statusText.textContent = {
        new: "正在连接...",
        connecting: "正在连接...",
        connected: "已连接",
        disconnected: "连接已中断，正在恢复...",
        failed: "视频连接失败。",
        closed: "已停止观看",
      }[state];
      if (state === "connected") {
        clearTimeout(session.timeout);
        session.lastProgressAt = performance.now();
      }
      if (state === "failed") stopSession(session, "视频连接失败。");
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
    lastDecodedFrames: 0,
    checkingVideoProgress: false,
    presentedFrames: 0,
    usesVideoFrameCallbacks: false,
    videoFrameCallback: null,
    lastProgressAt: performance.now(),
    playbackStartedAt: null,
    playbackBlocked: false,
  };
  currentSession = session;
  connectButton.disabled = true;
  disconnectButton.disabled = false;
  statusText.textContent = "正在连接...";
  const websocketScheme = location.protocol === "https:" ? "wss:" : "ws:";
  session.socket = new WebSocket(`${websocketScheme}//${location.host}/ws`);
  session.timeout = setTimeout(() => stopSession(session, "连接超时。"), 65000);
  session.videoMonitor = setInterval(() => checkVideoProgress(session), 2000);
  session.socket.onopen = () => {
    if (session !== currentSession) return;
    session.socket.send(JSON.stringify({type: "auth", token: tokenInput.value}));
  };
  session.socket.onmessage = (event) => {
    // Serialize SDP/ICE processing; async onmessage callbacks otherwise overlap.
    session.messages = session.messages
      .then(() => handleMessage(session, JSON.parse(event.data)))
      .catch(() => stopSession(session, "视频连接异常。"));
  };
  session.socket.onerror = () => stopSession(session, "连接失败。");
  session.socket.onclose = () => stopSession(session, "连接已断开。");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (watchingRequested) return;
  if (!window.RTCPeerConnection) {
    statusText.textContent = "当前浏览器不支持视频连接，请更换新版浏览器。";
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

disconnectButton.addEventListener("click", () => stopWatching("已停止观看"));
window.addEventListener("pagehide", () => stopWatching("已停止观看"));
