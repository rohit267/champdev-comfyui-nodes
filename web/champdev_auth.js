import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// In-UI password dialog. window.prompt() is silently blocked in some
// embedded/headless contexts, so we render our own modal instead.
export function promptPassword(message) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99999;" +
      "display:flex;align-items:center;justify-content:center";
    const box = document.createElement("div");
    box.style.cssText =
      "background:#2a2a2a;border:1px solid #555;border-radius:8px;padding:18px 20px;" +
      "display:flex;flex-direction:column;gap:12px;min-width:320px;max-width:90vw;" +
      "color:#ddd;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.5)";
    const label = document.createElement("div");
    label.textContent = message || "Password (from the telemetry dashboard):";
    label.style.cssText = "color:#ddd;font-size:13px";
    const input = document.createElement("input");
    input.type = "password";
    input.placeholder = "password";
    input.style.cssText =
      "background:#111;border:1px solid #444;border-radius:4px;padding:6px 8px;" +
      "color:#ddd;font-size:13px;outline:none";
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:flex-end;gap:8px";
    const cancel = document.createElement("button");
    cancel.textContent = "Cancel";
    cancel.style.cssText =
      "background:#3a3a3a;color:#ddd;border:1px solid #555;border-radius:4px;padding:4px 12px;cursor:pointer";
    const ok = document.createElement("button");
    ok.textContent = "Unlock";
    ok.style.cssText =
      "background:#3a6ea5;color:#fff;border:1px solid #4a7ab5;border-radius:4px;padding:4px 12px;cursor:pointer";
    row.append(cancel, ok);

    const done = (val) => {
      overlay.remove();
      resolve(val);
    };
    cancel.addEventListener("click", () => done(null));
    ok.addEventListener("click", () => done(input.value || null));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") done(input.value || null);
      else if (e.key === "Escape") done(null);
    });
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) done(null);
    });

    box.append(label, input, row);
    overlay.append(box);
    document.body.append(overlay);
    input.focus();
  });
}

// Opens the dialog, POSTs the password, and reports success.
export async function unlockWithDialog(message) {
  const password = await promptPassword(message);
  if (!password) return false;
  try {
    const r = await api.fetchApi("/champdev/auth/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const res = await r.json();
    if (res.error || !r.ok) {
      app.extensionManager?.toast?.add?.({
        severity: "error",
        summary: "Unlock failed",
        detail: res.error || `HTTP ${r.status}`,
        life: 4000,
      });
      return false;
    }
    return true;
  } catch (e) {
    app.extensionManager?.toast?.add?.({
      severity: "error",
      summary: "Unlock failed",
      detail: String(e),
      life: 4000,
    });
    return false;
  }
}
