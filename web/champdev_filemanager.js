import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const API = "/champdev/fm";
const STYLE_ID = "champ-fm-style";
const PAGE = 20; // rows (and thumbnails) materialized per "page"

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
.champ-fm:focus{outline:none}
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
.champ-fm-list{flex:1;overflow:auto;min-height:0}
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
.champ-fm-more{padding:8px;text-align:center;color:#888;cursor:pointer;border-bottom:1px solid #2a2a2a}
.champ-fm-more:hover{color:#ddd}
.champ-fm-divider{width:6px;flex-shrink:0;cursor:col-resize;background:#2a2a2a}
.champ-fm-divider:hover{background:#3a6ea5}
.champ-fm-side{border-left:1px solid #333;padding:8px;overflow:auto;flex-shrink:0;
  display:flex;flex-direction:column;box-sizing:border-box}
.champ-fm-side .ph{width:100%;flex:1;min-height:240px;background:#111;border-radius:4px;display:flex;
  align-items:center;justify-content:center;color:#666;font-size:48px;overflow:hidden}
.champ-fm-side .ph.clk{cursor:zoom-in}
.champ-fm-side .ph img{max-width:100%;max-height:100%;object-fit:contain}
.champ-fm-side .ph video{max-width:100%;max-height:100%}
.champ-fm-side .ph audio{width:100%}
.champ-fm-side dl{margin:8px 0 0;font-size:11px;color:#aaa;line-height:1.5}
.champ-fm-side dt{color:#888}
.champ-fm-side dd{margin:0 0 5px;color:#ddd;word-break:break-all}
.champ-fm-empty{padding:16px;color:#777;text-align:center}
.champ-fm-overlay{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:10000;
  display:flex;align-items:center;justify-content:center}
.champ-fm-overlay img,.champ-fm-overlay video{max-width:90vw;max-height:90vh}
.champ-fm-overlay .close{position:absolute;top:16px;right:24px;font-size:28px;color:#fff;cursor:pointer}
.champ-fm-overlay .cap{position:absolute;bottom:18px;left:0;right:0;text-align:center;
  color:#eee;font-size:13px;text-shadow:0 1px 3px #000;pointer-events:none}
.champ-fm-overlay .nav{position:absolute;top:50%;transform:translateY(-50%);font-size:46px;
  color:#fff;cursor:pointer;user-select:none;padding:0 18px;opacity:.6}
.champ-fm-overlay .nav:hover{opacity:1}
.champ-fm-overlay .nav.prev{left:8px}
.champ-fm-overlay .nav.next{right:8px}
.champ-fm.drag{outline:2px dashed #5a8;outline-offset:-6px}
  `;
  document.head.append(s);
}

const ICONS = { folder: "📁", image: "🖼", video: "🎬", audio: "🎵", text: "📄", other: "📦" };

const isPreviewable = (e) => e.kind === "image" || e.kind === "video" || e.kind === "audio";

// Fullscreen viewer. `list` is the current visible entries; ←/→ cycle through the
// previewable members of that list (wrapping). Falls back to a single item.
function openViewer(entry, list) {
  if (!isPreviewable(entry)) {
    window.open(fileUrl(entry.path), "_blank");
    return;
  }
  let media = (list && list.length ? list : [entry]).filter(isPreviewable);
  let idx = media.findIndex((e) => e.path === entry.path);
  if (idx < 0) {
    media = [entry];
    idx = 0;
  }

  const overlay = el("div", { class: "champ-fm-overlay" });
  const cap = el("div", { class: "cap" });
  const prev = el("div", { class: "nav prev", title: "Previous (←)" }, "‹");
  const next = el("div", { class: "nav next", title: "Next (→)" }, "›");
  let mediaEl = null;

  const draw = () => {
    const cur = media[idx];
    const url = fileUrl(cur.path);
    let m;
    if (cur.kind === "image") m = el("img", { src: url });
    else if (cur.kind === "video") m = el("video", { src: url, controls: "", autoplay: "" });
    else m = el("audio", { src: url, controls: "", autoplay: "" });
    if (mediaEl) mediaEl.replaceWith(m);
    else overlay.insertBefore(m, cap);
    mediaEl = m;
    cap.textContent = media.length > 1 ? `${cur.name}  ·  ${idx + 1} / ${media.length}` : cur.name;
  };
  const step = (d) => {
    idx = (idx + d + media.length) % media.length;
    draw();
  };
  const close = () => {
    overlay.remove();
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e) => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") { step(1); e.preventDefault(); }
    else if (e.key === "ArrowLeft") { step(-1); e.preventDefault(); }
  };

  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  prev.addEventListener("click", (e) => { e.stopPropagation(); step(-1); });
  next.addEventListener("click", (e) => { e.stopPropagation(); step(1); });
  document.addEventListener("keydown", onKey);

  overlay.append(cap, el("div", { class: "close", onclick: close }, "✕"));
  if (media.length > 1) overlay.append(prev, next);
  document.body.append(overlay);
  draw();
}

function createFileManager(initialPath, showHidden) {
  const state = {
    cwd: initialPath || "",
    parent: null,
    entries: [],
    view: [], // current filtered+sorted list (full, not windowed)
    selected: new Set(),
    focused: null,
    showHidden: !!showHidden,
    sort: "name",
    sortDir: "asc",
    filter: "",
    shown: PAGE, // how many of `view` are currently rendered
    sideWidth: 320,
  };

  const root = el("div", { class: "champ-fm" });
  root.tabIndex = 0;

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

  // --- body: list + resizable divider + side pane ---
  const listWrap = el("div", { class: "champ-fm-list" });
  const side = el("div", { class: "champ-fm-side" });
  side.style.width = state.sideWidth + "px";
  const divider = el("div", { class: "champ-fm-divider", title: "Drag to resize preview" });
  root.append(el("div", { class: "champ-fm-body" }, listWrap, divider, side));

  divider.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startW = side.offsetWidth;
    const onMove = (ev) => {
      const w = Math.max(180, Math.min(720, startW + (startX - ev.clientX)));
      side.style.width = w + "px";
      state.sideWidth = w;
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });

  // auto-load more rows as the list scrolls near the bottom
  listWrap.addEventListener("scroll", () => {
    if (listWrap.scrollTop + listWrap.clientHeight >= listWrap.scrollHeight - 48) loadMore();
  });

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
    state.shown = PAGE;
    listWrap.scrollTop = 0;
    render();
  }

  function loadMore() {
    if (state.shown < state.view.length) {
      state.shown += PAGE;
      render();
    }
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
    if (entry.kind === "image") {
      const img = el("img", { src: fileUrl(entry.path) });
      img.addEventListener("error", () => ph.replaceChildren(document.createTextNode(ICONS.image)));
      ph.append(img);
      ph.classList.add("clk");
      ph.addEventListener("click", () => openViewer(entry, state.view));
    } else if (entry.kind === "video") {
      ph.append(el("video", { src: fileUrl(entry.path), controls: "" }));
      ph.classList.add("clk");
      ph.addEventListener("click", (ev) => { if (ev.target === ph) openViewer(entry, state.view); });
    } else if (entry.kind === "audio") {
      ph.append(el("audio", { src: fileUrl(entry.path), controls: "" }));
    } else {
      ph.append(document.createTextNode(ICONS[entry.kind] || ICONS.other));
    }

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

  function selectOnly(entry) {
    state.selected.clear();
    state.selected.add(entry.path);
    state.focused = entry;
  }

  function rowFor(entry) {
    const nameCell = el("div", { class: "champ-fm-name" });
    if (entry.kind === "image") {
      const thumb = el("img", { src: thumbUrl(entry.path), loading: "lazy" });
      thumb.addEventListener("error", () => thumb.replaceWith(el("span", {}, ICONS.image)));
      nameCell.append(thumb);
    } else {
      nameCell.append(el("span", {}, ICONS[entry.kind] || ICONS.other));
    }
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
        state.focused = entry;
      } else {
        selectOnly(entry);
      }
      root.focus({ preventScroll: true }); // so ↑/↓ work after a click
      render();
    });
    tr.addEventListener("dblclick", () => {
      if (entry.is_dir) load(entry.path);
      else if (isPreviewable(entry)) openViewer(entry, state.view);
      else window.open(fileUrl(entry.path), "_blank");
    });
    return tr;
  }

  function visibleEntries() {
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
    return items;
  }

  function render() {
    pathInput.value = state.cwd;
    upBtn.disabled = !state.parent;

    const items = visibleEntries();
    state.view = items;
    const windowed = items.slice(0, state.shown);

    const header = (label, key) =>
      el("th", { onclick: () => {
        if (state.sort === key) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        else { state.sort = key; state.sortDir = "asc"; }
        state.shown = PAGE;
        render();
      } }, label + (state.sort === key ? (state.sortDir === "asc" ? " ▲" : " ▼") : ""));

    const tbody = el("tbody");
    for (const e of windowed) tbody.append(rowFor(e));

    listWrap.replaceChildren(
      el("table", {},
        el("thead", {}, el("tr", {},
          header("Name", "name"), header("Size", "size"),
          header("Type", "kind"), header("Modified", "mtime"))),
        tbody)
    );

    if (!items.length) {
      listWrap.append(el("div", { class: "champ-fm-empty" }, "Empty folder"));
    } else if (items.length > windowed.length) {
      const remaining = items.length - windowed.length;
      listWrap.append(el("div", { class: "champ-fm-more", onclick: loadMore },
        `Showing ${windowed.length} of ${items.length} — click or scroll for ${Math.min(PAGE, remaining)} more`));
    }

    showProps(state.focused);
    updateActionState();
  }

  // ---- keyboard navigation (list has focus) ----
  root.addEventListener("keydown", (e) => {
    if (document.querySelector(".champ-fm-overlay")) return; // viewer owns the keys
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return; // typing in a field
    const nav = e.key === "ArrowDown" || e.key === "ArrowUp";
    if (!nav && e.key !== "Enter") return;

    const items = state.view;
    if (!items.length) return;
    let i = state.focused ? items.findIndex((x) => x.path === state.focused.path) : -1;

    if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      const cur = items[i] || items[0];
      if (!cur) return;
      if (cur.is_dir) load(cur.path);
      else openViewer(cur, items);
      return;
    }

    if (i < 0) i = e.key === "ArrowDown" ? 0 : items.length - 1;
    else i = e.key === "ArrowDown" ? Math.min(items.length - 1, i + 1) : Math.max(0, i - 1);
    selectOnly(items[i]);
    if (i >= state.shown) state.shown = Math.ceil((i + 1) / PAGE) * PAGE;
    e.preventDefault();
    e.stopPropagation();
    render();
    const selRow = listWrap.querySelector(".champ-fm-row.sel");
    if (selRow) selRow.scrollIntoView({ block: "nearest" });
  });

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
    if (sel.length === 1) openViewer(sel[0], state.view);
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
    state.shown = PAGE;
    listWrap.scrollTop = 0;
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
      const fmWidget = this.addDOMWidget("champ_fm", "div", fm.root, { serialize: false, hideOnZoom: false });
      this.size = [640, 520];

      // Without this, ComfyUI sizes the DOM widget (and the node) to its content
      // — every table row — so the node grows "very long" and the inner list can
      // never scroll. Derive the widget's height from the NODE's height instead
      // of its content: the file list becomes a bounded, scrollable box, and the
      // user resizes it by resizing the node. ~86px is reserved for the title and
      // the start_path / show_hidden widgets above us.
      const node = this;
      fmWidget.computeSize = function (width) {
        return [width, Math.max(220, (node.size?.[1] || 520) - 86)];
      };

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
