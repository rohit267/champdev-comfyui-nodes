import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const API = "/champdev/fm";
const STYLE_ID = "champ-fm-style";

function toast(severity, summary, detail) {
  try {
    app.extensionManager.toast.add({ severity, summary, detail, life: 4000 });
  } catch (e) {
    if (severity === "error") window.alert(`${summary}${detail ? ": " + detail : ""}`);
  }
}

async function jget(path, params) {
  const qs = new URLSearchParams(params).toString();
  const r = await api.fetchApi(`${API}${path}?${qs}`);
  return r.json();
}

async function jpost(path, body) {
  const r = await api.fetchApi(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

function fileUrl(path, download) {
  const qs = new URLSearchParams({ path });
  if (download) qs.set("download", "1");
  return api.apiURL(`${API}/file?${qs.toString()}`);
}

function thumbUrl(path) {
  return api.apiURL(`${API}/thumbnail?${new URLSearchParams({ path, size: "96" })}`);
}

function fmtSize(n) {
  if (n == null) return "—";
  if (n === 0) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
}

function fmtDate(ts) {
  return ts ? new Date(ts * 1000).toLocaleString() : "—";
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "style") Object.assign(e.style, v);
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    e.append(c.nodeType ? c : document.createTextNode(c));
  }
  return e;
}

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const s = el("style", { id: STYLE_ID });
  s.textContent = `
.champ-fm{display:flex;flex-direction:column;width:100%;height:100%;
  background:#1e1e1e;color:#ddd;font-size:12px;border-radius:6px;overflow:hidden}
.champ-fm button{background:#3a3a3a;color:#ddd;border:1px solid #555;border-radius:4px;
  padding:3px 7px;cursor:pointer;font-size:12px}
.champ-fm button:hover{background:#484848}
.champ-fm button:disabled{opacity:.4;cursor:default}
.champ-fm button.danger{color:#ff7a7a;border-color:#7a3a3a}
.champ-fm-bar{display:flex;gap:4px;align-items:center;padding:5px;border-bottom:1px solid #333;flex-wrap:wrap}
.champ-fm-path{flex:1;min-width:80px;background:#111;color:#ddd;border:1px solid #444;
  border-radius:4px;padding:3px 6px}
.champ-fm-filter{background:#111;color:#ddd;border:1px solid #444;border-radius:4px;padding:2px 6px}
.champ-fm-body{flex:1;display:flex;min-height:0}
.champ-fm-list{flex:1;overflow:auto}
.champ-fm-list table{width:100%;border-collapse:collapse}
.champ-fm-list th{position:sticky;top:0;background:#262626;text-align:left;
  padding:4px 8px;cursor:pointer;border-bottom:1px solid #333;font-weight:500}
.champ-fm-list td{padding:3px 8px;border-bottom:1px solid #2a2a2a;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.champ-fm-row{cursor:pointer}
.champ-fm-row:hover{background:#2c2c2c}
.champ-fm-row.sel{background:#33415a}
.champ-fm-name{display:flex;align-items:center;gap:6px;max-width:240px}
.champ-fm-name img{width:20px;height:20px;object-fit:cover;border-radius:3px;background:#333}
.champ-fm-side{width:170px;border-left:1px solid #333;padding:8px;overflow:auto;flex-shrink:0}
.champ-fm-side .ph{width:100%;height:120px;background:#111;border-radius:4px;display:flex;
  align-items:center;justify-content:center;color:#666;font-size:28px;overflow:hidden}
.champ-fm-side .ph img{max-width:100%;max-height:100%}
.champ-fm-side dl{margin:8px 0 0;font-size:11px;color:#aaa;line-height:1.5}
.champ-fm-side dt{color:#888}
.champ-fm-side dd{margin:0 0 5px;color:#ddd;word-break:break-all}
.champ-fm-empty{padding:16px;color:#777;text-align:center}
.champ-fm-overlay{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:10000;
  display:flex;align-items:center;justify-content:center}
.champ-fm-overlay img,.champ-fm-overlay video{max-width:90vw;max-height:90vh}
.champ-fm-overlay .close{position:absolute;top:16px;right:24px;font-size:28px;color:#fff;cursor:pointer}
.champ-fm.drag{outline:2px dashed #5a8;outline-offset:-6px}
  `;
  document.head.append(s);
}

const ICONS = { folder: "📁", image: "🖼", video: "🎬", audio: "🎵", text: "📄", other: "📦" };

function openViewer(entry) {
  const overlay = el("div", { class: "champ-fm-overlay" });
  const onKey = (e) => {
    if (e.key === "Escape") close();
  };
  const close = () => {
    overlay.remove();
    document.removeEventListener("keydown", onKey);
  };
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", onKey);

  let media;
  const url = fileUrl(entry.path);
  if (entry.kind === "image") media = el("img", { src: url });
  else if (entry.kind === "video") media = el("video", { src: url, controls: "", autoplay: "" });
  else if (entry.kind === "audio") media = el("audio", { src: url, controls: "", autoplay: "" });
  else {
    window.open(url, "_blank");
    return;
  }
  overlay.append(media, el("div", { class: "close", onclick: close }, "✕"));
  document.body.append(overlay);
}

function createFileManager(initialPath, showHidden) {
  const state = {
    cwd: initialPath || "",
    parent: null,
    entries: [],
    selected: new Set(),
    focused: null,
    showHidden: !!showHidden,
    sort: "name",
    sortDir: "asc",
    filter: "",
  };

  const root = el("div", { class: "champ-fm" });

  // --- toolbar ---
  const upBtn = el("button", { title: "Up one level" }, "⬆");
  const pathInput = el("input", { class: "champ-fm-path", type: "text", placeholder: "/path/to/folder" });
  const refreshBtn = el("button", { title: "Refresh" }, "⟳");
  const hiddenChk = el("input", { type: "checkbox", title: "Show hidden" });
  hiddenChk.checked = state.showHidden;
  root.append(
    el("div", { class: "champ-fm-bar" }, upBtn, pathInput, refreshBtn,
      el("label", { style: { display: "flex", alignItems: "center", gap: "3px" } }, hiddenChk, "hidden"))
  );

  // --- action bar ---
  const actBar = el("div", { class: "champ-fm-bar" });
  const actions = {};
  const addAction = (key, label, title, handler, danger) => {
    const b = el("button", danger ? { title, class: "danger" } : { title }, label);
    b.addEventListener("click", handler);
    actions[key] = b;
    actBar.append(b);
  };
  root.append(actBar);

  // --- body: list + side pane ---
  const listWrap = el("div", { class: "champ-fm-list" });
  const side = el("div", { class: "champ-fm-side" });
  root.append(el("div", { class: "champ-fm-body" }, listWrap, side));

  // ---- data ----
  async function load(path) {
    const target = path != null ? path : state.cwd;
    const res = await jget("/list", { path: target, show_hidden: state.showHidden, sort: state.sort });
    if (res.error) {
      toast("error", "Cannot open folder", res.error);
      return;
    }
    state.cwd = res.cwd;
    state.parent = res.parent;
    state.entries = res.entries;
    state.selected.clear();
    state.focused = null;
    render();
  }

  function selectedEntries() {
    return state.entries.filter((e) => state.selected.has(e.path));
  }

  function updateActionState() {
    const sel = selectedEntries();
    const one = sel.length === 1;
    const any = sel.length >= 1;
    actions.preview.disabled = !(one && sel[0].kind !== "folder" && sel[0].kind !== "other");
    actions.download.disabled = !(one && !sel[0].is_dir);
    actions.rename.disabled = !one;
    actions.move.disabled = !any;
    actions.copy.disabled = !any;
    actions.del.disabled = !any;
    actions.props.disabled = !one;
  }

  function showProps(entry) {
    side.replaceChildren();
    if (!entry) {
      side.append(el("div", { style: { color: "#777" } }, "No selection"));
      return;
    }
    const ph = el("div", { class: "ph" });
    if (entry.kind === "image") ph.append(el("img", { src: thumbUrl(entry.path) }));
    else ph.append(document.createTextNode(ICONS[entry.kind] || ICONS.other));

    const dl = el("dl");
    const add = (k, v) => dl.append(el("dt", {}, k), el("dd", {}, v));
    add("Name", entry.name);
    add("Type", entry.is_dir ? "folder" : entry.kind + (entry.ext ? " (" + entry.ext + ")" : ""));
    if (!entry.is_dir) add("Size", fmtSize(entry.size));
    add("Modified", fmtDate(entry.mtime));
    add("Path", entry.path);
    side.append(ph, dl);

    if (entry.kind === "image" && !entry.is_dir) {
      jget("/properties", { path: entry.path }).then((p) => {
        if (p.width && dl.isConnected) add("Dimensions", `${p.width} × ${p.height}`);
      });
    }
  }

  function rowFor(entry) {
    const nameCell = el("div", { class: "champ-fm-name" });
    if (entry.kind === "image") nameCell.append(el("img", { src: thumbUrl(entry.path), loading: "lazy" }));
    else nameCell.append(el("span", {}, ICONS[entry.kind] || ICONS.other));
    nameCell.append(el("span", { style: { overflow: "hidden", textOverflow: "ellipsis" } }, entry.name));

    const tr = el("tr", { class: "champ-fm-row" + (state.selected.has(entry.path) ? " sel" : "") },
      el("td", {}, nameCell),
      el("td", {}, entry.is_dir ? "—" : fmtSize(entry.size)),
      el("td", {}, entry.is_dir ? "folder" : entry.kind),
      el("td", {}, fmtDate(entry.mtime)));

    tr.addEventListener("click", (ev) => {
      if (ev.ctrlKey || ev.metaKey) {
        if (state.selected.has(entry.path)) state.selected.delete(entry.path);
        else state.selected.add(entry.path);
      } else {
        state.selected.clear();
        state.selected.add(entry.path);
      }
      state.focused = entry;
      render();
    });
    tr.addEventListener("dblclick", () => {
      if (entry.is_dir) load(entry.path);
      else if (["image", "video", "audio"].includes(entry.kind)) openViewer(entry);
      else window.open(fileUrl(entry.path), "_blank");
    });
    return tr;
  }

  function render() {
    pathInput.value = state.cwd;
    upBtn.disabled = !state.parent;

    let items = state.entries.slice();
    if (state.filter) {
      const f = state.filter.toLowerCase();
      items = items.filter((e) => e.name.toLowerCase().includes(f));
    }
    const dir = state.sortDir === "desc" ? -1 : 1;
    items.sort((a, b) => {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;
      let av, bv;
      if (state.sort === "size") { av = a.size; bv = b.size; }
      else if (state.sort === "mtime") { av = a.mtime; bv = b.mtime; }
      else if (state.sort === "kind") { av = a.kind; bv = b.kind; }
      else { av = a.name.toLowerCase(); bv = b.name.toLowerCase(); }
      return av < bv ? -dir : av > bv ? dir : 0;
    });

    const header = (label, key) =>
      el("th", { onclick: () => {
        if (state.sort === key) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        else { state.sort = key; state.sortDir = "asc"; }
        render();
      } }, label + (state.sort === key ? (state.sortDir === "asc" ? " ▲" : " ▼") : ""));

    const tbody = el("tbody");
    for (const e of items) tbody.append(rowFor(e));

    listWrap.replaceChildren(
      el("table", {},
        el("thead", {}, el("tr", {},
          header("Name", "name"), header("Size", "size"),
          header("Type", "kind"), header("Modified", "mtime"))),
        tbody)
    );
    if (!items.length) listWrap.append(el("div", { class: "champ-fm-empty" }, "Empty folder"));

    showProps(state.focused);
    updateActionState();
  }

  // ---- uploads ----
  async function uploadFiles(fileList) {
    if (!fileList || !fileList.length) return;
    const fd = new FormData();
    fd.append("dest", state.cwd); // dest MUST be first (multipart is read in order)
    for (const f of fileList) fd.append("files", f, f.name);
    const r = await api.fetchApi(`${API}/upload`, { method: "POST", body: fd });
    const res = await r.json();
    if (res.error) toast("error", "Upload failed", res.error);
    else toast("success", "Uploaded", `${res.results.length} file(s)`);
    load();
  }

  // ---- action handlers ----
  addAction("preview", "👁 Preview", "Preview", () => {
    const sel = selectedEntries();
    if (sel.length === 1) openViewer(sel[0]);
  });
  addAction("upload", "⬆ Upload", "Upload files here", () => {
    const inp = el("input", { type: "file", multiple: "" });
    inp.addEventListener("change", () => uploadFiles(inp.files));
    inp.click();
  });
  addAction("download", "⬇ Download", "Download", () => {
    const sel = selectedEntries();
    if (sel.length === 1 && !sel[0].is_dir) {
      const a = el("a", { href: fileUrl(sel[0].path, true), download: sel[0].name });
      document.body.append(a);
      a.click();
      a.remove();
    }
  });
  addAction("rename", "✎ Rename", "Rename", async () => {
    const sel = selectedEntries();
    if (sel.length !== 1) return;
    const name = window.prompt("New name:", sel[0].name);
    if (!name || name === sel[0].name) return;
    const res = await jpost("/rename", { path: sel[0].path, new_name: name });
    if (res.error) toast("error", "Rename failed", res.error);
    load();
  });
  addAction("move", "↪ Move", "Move to…", async () => {
    const sel = selectedEntries();
    if (!sel.length) return;
    const dest = window.prompt("Move to folder:", state.cwd);
    if (!dest) return;
    const res = await jpost("/move", { paths: sel.map((e) => e.path), dest, copy: false });
    reportResults("Move", res);
    load();
  });
  addAction("copy", "⧉ Copy", "Copy to…", async () => {
    const sel = selectedEntries();
    if (!sel.length) return;
    const dest = window.prompt("Copy to folder:", state.cwd);
    if (!dest) return;
    const res = await jpost("/move", { paths: sel.map((e) => e.path), dest, copy: true });
    reportResults("Copy", res);
    load();
  });
  addAction("mkdir", "+ Folder", "New folder", async () => {
    const name = window.prompt("New folder name:");
    if (!name) return;
    const res = await jpost("/mkdir", { path: state.cwd, name });
    if (res.error) toast("error", "Create folder failed", res.error);
    load();
  });
  addAction("del", "🗑 Delete", "Delete", async () => {
    const sel = selectedEntries();
    if (!sel.length) return;
    if (!window.confirm(`Delete ${sel.length} item(s)? This cannot be undone.`)) return;
    const res = await jpost("/delete", { paths: sel.map((e) => e.path) });
    reportResults("Delete", res);
    load();
  }, true);
  addAction("props", "ℹ Properties", "Properties", () => {
    const sel = selectedEntries();
    if (sel.length === 1) {
      state.focused = sel[0];
      showProps(sel[0]);
    }
  });

  function reportResults(label, res) {
    if (res.error) {
      toast("error", `${label} failed`, res.error);
      return;
    }
    const fails = (res.results || []).filter((r) => !r.ok);
    if (fails.length) toast("warn", `${label}: ${fails.length} failed`, fails[0].error);
    else toast("success", label, "Done");
  }

  // ---- wire toolbar ----
  upBtn.addEventListener("click", () => state.parent && load(state.parent));
  refreshBtn.addEventListener("click", () => load());
  pathInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") load(pathInput.value.trim());
  });
  hiddenChk.addEventListener("change", () => {
    state.showHidden = hiddenChk.checked;
    load();
  });

  // filter box lives in the action bar
  const filterInput = el("input", { class: "champ-fm-filter", type: "text", placeholder: "filter…" });
  filterInput.addEventListener("input", () => {
    state.filter = filterInput.value;
    render();
  });
  actBar.append(filterInput);

  // ---- drag & drop upload ----
  root.addEventListener("dragover", (e) => {
    e.preventDefault();
    root.classList.add("drag");
  });
  root.addEventListener("dragleave", (e) => {
    if (e.target === root) root.classList.remove("drag");
  });
  root.addEventListener("drop", (e) => {
    e.preventDefault();
    root.classList.remove("drag");
    if (e.dataTransfer?.files?.length) uploadFiles(e.dataTransfer.files);
  });

  return { root, load };
}

app.registerExtension({
  name: "champdev.filemanager",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "ChampdevFM") return;
    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onCreated?.apply(this, arguments);
      ensureStyle();
      const startWidget = this.widgets?.find((w) => w.name === "start_path");
      const hiddenWidget = this.widgets?.find((w) => w.name === "show_hidden");
      const fm = createFileManager(startWidget?.value || "", hiddenWidget?.value);
      this.addDOMWidget("champ_fm", "div", fm.root, { serialize: false, hideOnZoom: false });
      this.size = [480, 480];
      fm.load(startWidget?.value || "");
      if (startWidget) {
        const cb = startWidget.callback;
        startWidget.callback = function () {
          cb?.apply(this, arguments);
          fm.load(startWidget.value);
        };
      }
      return r;
    };
  },
});
