import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { unlockWithDialog } from "./champdev_auth.js";

const VENDOR = new URL("./vendor/", import.meta.url).href;

function loadXterm() {
  if (window.__champTermAssets) return window.__champTermAssets;
  window.__champTermAssets = new Promise((resolve, reject) => {
    if (!document.getElementById("champ-term-css")) {
      const link = document.createElement("link");
      link.id = "champ-term-css";
      link.rel = "stylesheet";
      link.href = VENDOR + "xterm.css";
      document.head.append(link);
    }
    const s1 = document.createElement("script");
    s1.src = VENDOR + "xterm.js";
    s1.onerror = () => reject(new Error("failed to load xterm.js"));
    s1.onload = () => {
      const s2 = document.createElement("script");
      s2.src = VENDOR + "addon-fit.js";
      s2.onerror = () => reject(new Error("failed to load addon-fit.js"));
      s2.onload = () => resolve();
      document.head.append(s2);
    };
    document.head.append(s1);
  });
  return window.__champTermAssets;
}

function wsUrl(params) {
  const u = new URL(api.apiURL("/champdev/terminal/ws"), window.location.origin);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  return u.href;
}

function widgetValue(node, name) {
  return node.widgets?.find((w) => w.name === name)?.value ?? "";
}

async function authStatus() {
  try {
    const r = await api.fetchApi("/champdev/auth/status");
    const res = await r.json();
    return !!res.authed;
  } catch (e) {
    return false;
  }
}

async function setupTerminal(node) {
  const root = document.createElement("div");
  root.style.cssText =
    "display:flex;flex-direction:column;width:100%;height:100%;background:#1e1e1e;border-radius:6px;overflow:hidden";

  const bar = document.createElement("div");
  bar.style.cssText =
    "display:flex;gap:6px;padding:4px 6px;border-bottom:1px solid #333;flex:0 0 auto";
  const restart = document.createElement("button");
  restart.textContent = "⟳ Restart";
  restart.style.cssText =
    "background:#3a3a3a;color:#ddd;border:1px solid #555;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px";
  const status = document.createElement("span");
  status.style.cssText = "color:#888;font-size:12px;align-self:center";
  bar.append(restart, status);

  const host = document.createElement("div");
  host.style.cssText = "flex:1 1 auto;min-height:0;padding:4px";
  root.append(bar, host);

  // Lock overlay: shown until the password unlocks the session. The backend
  // also refuses to spawn a shell without auth.
  const lockOverlay = document.createElement("div");
  lockOverlay.style.cssText =
    "position:absolute;inset:0;display:flex;flex-direction:column;gap:10px;align-items:center;" +
    "justify-content:center;background:rgba(30,30,30,.92);z-index:10;border-radius:6px;color:#ddd";
  const lockMsg = document.createElement("div");
  lockMsg.textContent = "🔒 Unlock to use terminal";
  const lockBtn = document.createElement("button");
  lockBtn.textContent = "Unlock";
  lockBtn.style.cssText =
    "background:#3a3a3a;color:#ddd;border:1px solid #555;border-radius:4px;padding:4px 14px;cursor:pointer;font-size:13px";
  lockOverlay.append(lockMsg, lockBtn);
  root.style.position = "relative";
  root.append(lockOverlay);

  async function ensureUnlocked() {
    if (await authStatus()) return true;
    status.textContent = "locked";
    lockOverlay.style.display = "flex";
    return false;
  }

  lockBtn.addEventListener("click", async () => {
    lockBtn.disabled = true;
    lockBtn.textContent = "…";
    const ok = await unlockWithDialog("Password (from the telemetry dashboard):");
    lockBtn.disabled = false;
    lockBtn.textContent = "Unlock";
    if (ok) {
      lockOverlay.style.display = "none";
      status.textContent = "connecting…";
      connect();
    }
  });

  node.addDOMWidget("champ_term", "div", root, { serialize: false, hideOnZoom: false });
  node.size = [620, 400];

  await loadXterm();

  const term = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: "monospace",
    theme: { background: "#1e1e1e" },
  });
  const fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
  term.open(host);

  let ws = null;

  const sendResize = () => {
    try {
      fit.fit();
    } catch (e) {
      /* host not measurable yet */
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
    }
  };

  const connect = () => {
    try {
      fit.fit();
    } catch (e) {
      /* ignore */
    }
    status.textContent = "connecting…";
    ws = new WebSocket(
      wsUrl({
        cols: term.cols || 80,
        rows: term.rows || 24,
        shell: widgetValue(node, "shell"),
        cwd: widgetValue(node, "start_dir"),
      })
    );
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      status.textContent = "connected";
      term.focus();
      sendResize();
    };
    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") {
        try {
          const m = JSON.parse(ev.data);
          if (m.type === "exit") {
            term.write(`\r\n\x1b[33m[process exited: ${m.code}${m.error ? " — " + m.error : ""}]\x1b[0m\r\n`);
            status.textContent = "ended";
          }
        } catch (e) {
          /* ignore */
        }
      } else {
        term.write(new Uint8Array(ev.data));
      }
    };
    ws.onerror = () => {
      term.write("\r\n\x1b[31m[connection error]\x1b[0m\r\n");
      status.textContent = "error";
    };
    ws.onclose = () => {
      if (!["error", "ended"].includes(status.textContent)) {
        status.textContent = "disconnected";
      }
      // If the session expired mid-use, fall back to the lock overlay.
      authStatus().then((authed) => {
        if (!authed) {
          lockOverlay.style.display = "flex";
          status.textContent = "locked";
        }
      });
    };
  };

  term.onData((d) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "input", data: d }));
    }
  });

  const ro = new ResizeObserver(() => sendResize());
  ro.observe(host);

  restart.addEventListener("click", () => {
    try {
      ws?.close();
    } catch (e) {
      /* ignore */
    }
    term.reset();
    ensureUnlocked().then((ok) => ok && connect());
  });

  ensureUnlocked().then((ok) => ok && connect());

  node.__champTerm = {
    dispose() {
      try {
        ro.disconnect();
      } catch (e) {
        /* ignore */
      }
      try {
        ws?.close();
      } catch (e) {
        /* ignore */
      }
      try {
        term.dispose();
      } catch (e) {
        /* ignore */
      }
    },
  };
}

app.registerExtension({
  name: "champdev.terminal",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "ChampdevTerminal") return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onCreated?.apply(this, arguments);
      setupTerminal(this).catch((err) =>
        console.error("[champdev terminal] init failed:", err)
      );
      return r;
    };

    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () {
      this.__champTerm?.dispose();
      return onRemoved?.apply(this, arguments);
    };
  },
});
