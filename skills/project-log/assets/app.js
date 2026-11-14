/* project-log page script. Renders every tab from the JSON embedded by build.py.
   Entry HTML (e.html, so_what_html, glossary html) is produced and escaped by build.py;
   everything else is escaped here with esc(). */
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("plog-data").textContent);
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var TAB_LABEL = { overview: "Overview", timeline: "Timeline", results: "Results", side: "Side projects",
    loops: "Open loops", next: "Next steps", digests: "Digests", glossary: "Glossary", changelog: "Changelog" };
  var HIDDEN_IN_TIMELINE = { term: 1, session: 1 };

  /* ---------------- helpers ---------------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function dayNum(d) { var p = d.split("-"); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 864e5; }
  function fmtDay(d, withYear) {
    var p = d.split("-");
    var s = (+p[2]) + " " + MONTHS[+p[1] - 1];
    return withYear || p[0] !== D.today.slice(0, 4) ? s + " " + p[0] : s;
  }
  function fmtStamp(ts) {
    var tz = ts.slice(19);
    return fmtDay(ts.slice(0, 10), true) + ", " + ts.slice(11, 16) + (tz ? " (UTC" + (tz === "Z" ? "" : tz) + ")" : "");
  }
  function ageDays(d) { return Math.max(0, dayNum(D.today) - dayNum(d)); }
  /* position within the day, so a bug at 16:47 sits right of a milestone at 15:55 */
  function dayPos(e) { var f = 0.5; if (e.time) { f = (+e.time.slice(0, 2) + e.time.slice(3, 5) / 60) / 24; } return dayNum(e.date) + f; }
  var smooth = { behavior: "smooth", block: "center" };
  /* opened from disk: relative links to figure files and Plotly's PNG button work */
  var LOCAL = location.protocol === "file:";

  var THREAD = {}; D.threads.forEach(function (t) { THREAD[t.id] = t; });
  var BYID = {}; D.entries.forEach(function (e) { BYID[e.id] = e; });
  var RESULTS = D.entries.filter(function (e) { return e.result; });
  var BYRID = {}; RESULTS.forEach(function (e) { BYRID[e.result.id] = e; });
  var newestFirst = D.entries.slice().reverse();

  function threadChip(id) {
    var t = THREAD[id];
    if (!t) return "";
    return '<span class="thr' + (t.kind === "side" ? " side" : "") + '">' + esc(t.name) + "</span>";
  }
  function entryLink(id) {
    var e = BYID[id];
    return e ? '<a href="#' + esc(id) + '" data-entry="' + esc(id) + '">' + esc(e.title) + "</a>" : esc(id);
  }
  function resultLink(rid) {
    return BYRID[rid] ? '<a href="#' + esc(rid) + '" data-result="' + esc(rid) + '">' + esc(rid) + "</a>" : esc(rid);
  }
  function stateBadge(e) {
    if (!e.status) return "";
    return '<span class="state ' + e.status + '">' + e.status + "</span>";
  }

  /* ---------------- header ---------------- */
  document.title = D.project.title;
  $("#eyebrow").textContent = D.project.eyebrow;
  $("#title").textContent = D.project.title;
  if (D.project.lede) $("#lede").textContent = D.project.lede; else $("#lede").hidden = true;
  var st = D.stamp;
  $("#stamp").innerHTML =
    "<span>Updated " + esc(fmtStamp(st.built_at)) + "</span>" +
    "<span>" + st.n_entries + " log entries</span>" +
    (st.git_commit ? '<span>Repo at <span class="mono">' + esc(st.git_commit) + "</span>" +
      (st.git_dirty ? ' <span class="dirty" title="Code or docs outside project-log/ had uncommitted changes at build time">+ uncommitted changes</span>' : "") + "</span>" : "") +
    (st.log_uncommitted ? '<span class="dirty" title="Entries or project.yaml not yet in git, so the other machine cannot see them">' + st.log_uncommitted + " log file" + (st.log_uncommitted > 1 ? "s" : "") + " not committed</span>" : "") +
    "<span>Template v" + esc(st.template_version) + "</span>";
  if (D.draft) {
    var bn = document.createElement("div");
    bn.className = "draftbar pad";
    bn.innerHTML = '<div class="wrap"><b>Draft for review.</b> ' + D.draft + " imported entries have not been checked yet. Entries marked “imported” are reconstructed from earlier notes: check titles, types, threads and links, then approve them.</div>";
    document.body.insertBefore(bn, document.body.firstChild);
  }
  $("#footnote").innerHTML = "Built by project-log from " + st.n_entries + " entries in <span class=\"mono\">project-log/entries/</span>. " +
    "Entries are append-only: corrections are new entries that point back. Entries marked “imported” were reconstructed from earlier notes and have a date but no time.";

  /* ---------------- tabs ---------------- */
  var tabs = D.project.tabs.filter(function (t) { return TAB_LABEL[t]; });
  var counts = {
    timeline: D.entries.filter(function (e) { return !HIDDEN_IN_TIMELINE[e.type]; }).length,
    results: RESULTS.length,
    side: D.threads.filter(function (t) { return t.kind === "side"; }).length,
    loops: D.entries.filter(function (e) { return e.status === "open" && e.type !== "plan"; }).length
  };
  $("#tablist").innerHTML = tabs.map(function (t) {
    return '<button type="button" role="tab" id="tab-' + t + '" data-tab="' + t + '" aria-selected="false">' + TAB_LABEL[t] +
      (counts[t] ? '<span class="count">' + counts[t] + "</span>" : "") + "</button>";
  }).join("");
  function showTab(id, keepScroll) {
    if (tabs.indexOf(id) < 0) id = tabs[0];
    $all("nav.tabs button").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.tab === id ? "true" : "false"); });
    $all("section.tab").forEach(function (s) { s.hidden = s.dataset.panel !== id; });
    if (!keepScroll) window.scrollTo({ top: 0 });
    renderOpenFigures();
  }
  $all("nav.tabs button").forEach(function (b) { b.addEventListener("click", function () { showTab(b.dataset.tab); }); });

  /* ---------------- result card ---------------- */
  function resultCard(e, prefix, withBody) {
    var r = e.result, p = e.prov || {}, t = THREAD[e.thread];
    var keys = (r.key_numbers || []).map(function (k) { return "<span>" + esc(k.label) + " <b>" + esc(k.value) + "</b></span>"; }).join("");
    var data = (p.data || []).map(function (d) {
      return esc(d.name ? d.name + (d.version ? " " + d.version : "") : d.path) + (d.sha256 ? ' <span title="sha256 ' + esc(d.sha256) + '">#' + esc(d.sha256.slice(0, 8)) + "</span>" : "");
    }).join("<br>");
    var prov = '<dl class="prov">' +
      (p.scripts ? "<dt>Script</dt><dd>" + p.scripts.map(esc).join("<br>") + "</dd>" : "") +
      (r.script ? "<dt>Figure script</dt><dd>" + esc(r.script) + "</dd>" : "") +
      (p.git_commit ? "<dt>" + (p.run ? "Analysis commit" : "Commit") + "</dt><dd>" + esc(p.git_commit) + (p.git_dirty ? ' <span class="dirty">+ uncommitted</span>' : "") + "</dd>" : "") +
      (p.run && p.run.repo_git_commit ? "<dt>Run commit</dt><dd>" + esc(String(p.run.repo_git_commit).slice(0, 7)) + (p.run.started_at ? "<br>started " + esc(String(p.run.started_at).replace("T", " ").slice(0, 16)) + (/Z$/.test(String(p.run.started_at)) ? " UTC" : "") : "") + "</dd>" : "") +
      "<dt>Recorded</dt><dd>" + esc(e.time ? e.date + " " + e.time : e.date) + (p.machine ? " · " + esc(p.machine) : "") + "</dd>" +
      (data ? "<dt>Data</dt><dd>" + data + "</dd>" : "") +
      (p.run_manifest ? "<dt>Run manifest</dt><dd>" + esc(p.run_manifest) + "</dd>" : "") +
      "</dl>";
    return '<details class="rcard" id="' + prefix + "-" + esc(r.id) + '" data-rid="' + esc(r.id) + '">' +
      "<summary>" +
      '<span class="rid">' + esc(r.id) + (t ? " · " + esc(t.name) : "") + "</span>" +
      '<span class="rtitle">' + esc(e.title) + "</span>" +
      '<span class="rsw"><b>So what:</b> ' + r.so_what_html + "</span>" +
      (keys ? '<span class="keys">' + keys + "</span>" : "") +
      '<span class="open-hint"><span class="closed-label">' + (r.figure_key ? "Open the figure" : "Show provenance") + '</span><span class="open-label">Close</span></span>' +
      "</summary>" +
      '<div class="rbody' + (r.figure_key ? "" : " nofig") + '">' +
      (withBody ? '<div class="prose">' + e.html + "</div>" : "") +
      (r.figure_key ? '<div class="figbox" data-fig="' + esc(r.figure_key) + '"></div>' : "") +
      (r.static_href && LOCAL ? '<a class="static-link" href="' + esc(r.static_href) + '">Static figure (' + esc(r.static_href.split(".").pop().toUpperCase()) + ") for slides and papers</a>" : "") +
      prov + "</div></details>";
  }

  /* ---------------- figures (Plotly, themed from CSS tokens) ---------------- */
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function themedLayout(layout) {
    var L = JSON.parse(JSON.stringify(layout || {}));
    var ink = token("--ink"), muted = token("--muted"), line = token("--line");
    L.paper_bgcolor = "rgba(0,0,0,0)";
    L.plot_bgcolor = "rgba(0,0,0,0)";
    L.font = Object.assign({ family: token("--body") || "sans-serif", size: 13 }, L.font || {}, { color: ink });
    L.colorway = L.colorway || [token("--accent"), token("--s2"), token("--side"), token("--decision"), token("--bug"), token("--prog")];
    L.legend = Object.assign({ orientation: "h", y: -0.2 }, L.legend || {});
    L.hoverlabel = Object.assign({ bgcolor: ink, font: { color: token("--bg") } }, L.hoverlabel || {});
    L.margin = L.margin || { l: 60, r: 20, t: 30, b: 60 };
    L.autosize = true; delete L.width;
    Object.keys(L).forEach(function (k) {
      if (/^[xy]axis\d*$/.test(k) || k === "xaxis" || k === "yaxis") {
        L[k] = Object.assign({}, L[k], { gridcolor: line, linecolor: line, zerolinecolor: line, tickfont: { color: muted } });
        if (L[k].title) L[k].title = Object.assign({}, typeof L[k].title === "string" ? { text: L[k].title } : L[k].title, { font: { color: muted } });
      }
    });
    if (!L.xaxis) L.xaxis = { gridcolor: line, linecolor: line, tickfont: { color: muted } };
    if (!L.yaxis) L.yaxis = { gridcolor: line, linecolor: line, tickfont: { color: muted } };
    if (L.title && typeof L.title === "object") L.title.font = Object.assign({}, L.title.font, { color: ink });
    return L;
  }
  function drawFigure(box) {
    var fig = D.figures[box.dataset.fig];
    if (!fig) return;
    if (fig.image) {   // a picture made by another tool (e.g. R): shown as it is
      box.classList.add("figimg");
      box.innerHTML = '<img src="' + fig.image + '" alt="' + esc(fig.alt || "") + '" loading="lazy">';
      box.dataset.drawn = "img";
      return;
    }
    if (typeof Plotly === "undefined") { box.innerHTML = '<p class="err">The chart library did not load.</p>'; return; }
    var drop = ["lasso2d", "select2d"];
    if (!LOCAL) drop.push("toImage");   // hosted viewers cannot download files
    Plotly.react(box, fig.data || [], themedLayout(fig.layout), { responsive: true, displaylogo: false, modeBarButtonsToRemove: drop });
    box.dataset.drawn = "1";
  }
  function renderOpenFigures() {
    $all("details.rcard[open] .figbox, .keyfig .figbox").forEach(function (b) {
      if (b.offsetParent !== null) {
        if (!b.dataset.drawn) drawFigure(b);
        else if (b.dataset.drawn !== "img" && typeof Plotly !== "undefined") Plotly.Plots.resize(b);
      }
    });
  }
  document.addEventListener("toggle", function (ev) {
    var d = ev.target;
    if (d.matches && d.matches("details.rcard") && d.open) {
      var box = $(".figbox", d);
      if (box && !box.dataset.drawn) drawFigure(box);
    }
  }, true);
  function redrawAll() { $all(".figbox[data-drawn]").forEach(drawFigure); }
  try { window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () { redrawAll(); drawGantt(); }); } catch (e) { /* old browsers */ }
  new MutationObserver(function () { redrawAll(); drawGantt(); }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  /* ---------------- overview ---------------- */
  function renderOverview() {
    var host = $('section[data-panel="overview"]');
    var html = "";
    var sum = D.overview.summary;
    var LABELS = ["Where we are", "What we learned", "What’s next"];
    if (!sum.length) {
      html += '<div class="block"><div class="summary plain"><p class="muted">No summary yet. Claude writes three short cards of bullets into project.yaml (overview.summary) before each build.</p></div></div>';
    } else {
      html += '<div class="block"><div class="summary">' + sum.map(function (p, i) {
        return '<div class="sum"><h3>' + esc(p.label || LABELS[i] || "") + "</h3>" + p.html + "</div>";
      }).join("") + "</div></div>";
    }
    if (D.overview.tiles.length) {
      html += '<div class="tiles">' + D.overview.tiles.map(function (t) {
        var link = String(t.link || ""), a = "";
        if (/^R\d+$/.test(link)) a = '<a href="#' + esc(link) + '" data-result="' + esc(link) + '">Result ' + esc(link) + " →</a>";
        else if (link.indexOf("thread:") === 0) a = '<a href="#timeline" data-thread="' + esc(link.slice(7)) + '">' + esc((THREAD[link.slice(7)] || {}).name || link) + " →</a>";
        else if (link.indexOf("tab:") === 0) a = '<a href="#' + esc(link.slice(4)) + '" data-tab-link="' + esc(link.slice(4)) + '">' + esc(TAB_LABEL[link.slice(4)] || link) + " →</a>";
        else if (BYID[link]) a = '<a href="#' + esc(link) + '" data-entry="' + esc(link) + '">Details →</a>';
        return '<div class="tile"><span class="big">' + esc(t.value) + "</span><p>" + esc(t.label) + "</p>" + (a || "<span></span>") + "</div>";
      }).join("") + "</div>";
    }
    // what changed
    var ch = D.changed, list = ch.entries.map(function (id) { return BYID[id]; }).filter(function (e) { return e && !HIDDEN_IN_TIMELINE[e.type]; });
    var heading = ch.first_build ? "Where things stand" : "What changed since the last update";
    var sub = ch.first_build ? "First build of this page. The most recent entries:" : "Since " + esc(fmtStamp(ch.since));
    if (ch.first_build) list = newestFirst.filter(function (e) { return !HIDDEN_IN_TIMELINE[e.type]; }).slice(0, 6);
    html += '<div class="block"><header><h2>' + heading + '</h2><p class="hint">' + sub + "</p></header>" +
      (list.length ? '<ul class="changes">' + list.slice().reverse().map(function (e) {
        return '<li><span class="pill" data-k="' + e.cat + '">' + esc(e.label) + "</span><span>" + entryLink(e.id) + "</span></li>";
      }).join("") + "</ul>" : '<p class="empty">Nothing new since the last build.</p>') + "</div>";
    // gantt
    html += '<div class="block"><header class="col"><h2>Project at a glance</h2><p class="hint">One row per thread. Click a row to see its steps in the timeline.</p></header>' +
      '<div class="gantt"><svg id="gantt" role="img" aria-label="Gantt chart of the project threads"></svg>' +
      '<div class="glegend">' +
      '<span><svg width="22" height="10" aria-hidden="true"><rect width="22" height="10" rx="3" fill="var(--main)"/></svg>Main work</span>' +
      '<span><svg width="22" height="10" aria-hidden="true"><rect width="22" height="10" rx="3" fill="var(--side)"/></svg>Side project</span>' +
      '<span><svg width="12" height="12" aria-hidden="true"><rect x="2" y="2" width="8" height="8" transform="rotate(45 6 6)" fill="var(--ink)"/></svg>Milestone or result</span>' +
      '<span><svg width="10" height="14" aria-hidden="true"><rect x="3" y="0" width="4" height="14" rx="1" fill="var(--bug)"/></svg>Bug or blocker</span>' +
      '<span><svg width="22" height="10" aria-hidden="true"><rect width="22" height="10" rx="3" fill="url(#hatchMain)" stroke="var(--main)"/></svg>Still active</span>' +
      "</div></div></div>";
    // optional key figure (overview.figure in project.yaml)
    var kf = D.overview.figure && BYRID[D.overview.figure];
    if (kf && kf.result.figure_key) {
      html += '<div class="block"><header class="col"><h2>' + esc(kf.title) + '</h2><p class="hint">Key figure · ' +
        '<a href="#' + esc(kf.result.id) + '" data-result="' + esc(kf.result.id) + '">' + esc(kf.result.id) + " in the timeline →</a></p></header>" +
        '<div class="card keyfig"><div class="figbox" data-fig="' + esc(kf.result.figure_key) + '"></div>' +
        '<p class="rsw"><b>So what:</b> ' + kf.result.so_what_html + "</p></div></div>";
    }
    // decisions
    var qs = D.entries.filter(function (e) { return e.type === "question" && e.status === "open"; });
    html += '<div class="block"><header><h2>Needs a decision</h2></header>' +
      (qs.length ? '<ul class="cards">' + qs.map(function (e) {
        return '<li class="card"><span class="q">' + entryLink(e.id) + '</span><div class="ctx prose">' + e.html + '</div><span class="meta">' + threadChip(e.thread) + "<span>Raised " + esc(fmtDay(e.date)) + "</span></span></li>";
      }).join("") + "</ul>" : '<p class="empty">No open questions right now.</p>') + "</div>";
    host.innerHTML = html;
    drawGantt();
  }

  function drawGantt() {
    var svg = document.getElementById("gantt");
    if (!svg) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var NS = "http://www.w3.org/2000/svg";
    function el(tag, a, p) { var e = document.createElementNS(NS, tag); for (var k in a) e.setAttribute(k, a[k]); (p || svg).appendChild(e); return e; }
    var rows = [];
    D.threads.forEach(function (t) {
      var es = D.entries.filter(function (e) { return e.thread === t.id; });
      if (!es.length) return;
      rows.push({ t: t, start: es[0].date, end: es[es.length - 1].date,
        ms: es.filter(function (e) { return e.type === "milestone" || e.type === "result"; }),
        bugs: es.filter(function (e) { return e.type === "bug" || e.type === "blocker"; }) });
    });
    if (!rows.length) { svg.setAttribute("viewBox", "0 0 1000 40"); var t0 = el("text", { x: 8, y: 24 }); t0.textContent = "No threads with entries yet."; return; }
    var d0 = Math.min.apply(null, rows.map(function (r) { return dayNum(r.start); })) - 2;
    var today = dayNum(D.today), d1 = Math.max(today, Math.max.apply(null, rows.map(function (r) { return dayNum(r.end); }))) + 2;
    var LW = 200, X0 = LW + 8, X1 = 988, RH = 30, TOP = 32;
    function sx(d) { return X0 + (X1 - X0) * (d - d0) / (d1 - d0); }
    var groups = [["MAIN WORK", rows.filter(function (r) { return r.t.kind !== "side"; })], ["SIDE PROJECTS", rows.filter(function (r) { return r.t.kind === "side"; })]];
    var y = TOP, layout = [];
    groups.forEach(function (g) {
      if (!g[1].length) return;
      layout.push(["g", g[0], y]); y += 22;
      g[1].forEach(function (r) { layout.push(["r", r, y]); y += RH; });
      y += 6;
    });
    var H = y + 4;
    svg.setAttribute("viewBox", "0 0 1000 " + H);
    // ticks: weekly Mondays, or month starts for long projects
    var span = d1 - d0, ticks = [], daily = span <= 24;
    if (daily) {
      for (var dd = Math.ceil(d0); dd <= d1; dd++) { if ((dd - Math.ceil(d0)) % (span <= 12 ? 1 : 2) === 0) ticks.push(dd); }
    } else if (span <= 120) {
      for (var d = Math.ceil(d0); d <= d1; d++) { if (new Date(d * 864e5).getUTCDay() === 1) ticks.push(d); }
      if (span > 60) ticks = ticks.filter(function (_, i) { return i % 2 === 0; });
    } else {
      for (var m = Math.ceil(d0); m <= d1; m++) { if (new Date(m * 864e5).getUTCDate() === 1) ticks.push(m); }
    }
    ticks.forEach(function (d) {
      var x = sx(d);
      if (Math.abs(x - sx(today + 0.5)) < 70 || x > X1 - 24 || x < X0 + 24) return;
      el("line", { x1: x, x2: x, y1: TOP - 6, y2: H - 4, stroke: "var(--line)", "stroke-width": 1 });
      var dt = new Date(d * 864e5), lab = daily ? dt.getUTCDate() + " " + MONTHS[dt.getUTCMonth()]
        : span <= 120 ? "Mon " + dt.getUTCDate() + " " + MONTHS[dt.getUTCMonth()] : MONTHS[dt.getUTCMonth()] + " " + dt.getUTCFullYear();
      var tx = el("text", { x: x, y: 16, "text-anchor": "middle" }); tx.textContent = lab;
    });
    var tX = sx(today + 0.5);
    el("line", { x1: tX, x2: tX, y1: TOP - 6, y2: H - 4, stroke: "var(--ink)", "stroke-width": 1.2, "stroke-dasharray": "3 3" });
    var tt = el("text", { x: tX, y: 16, "text-anchor": "middle", style: "fill:var(--ink);font-weight:600" }); tt.textContent = "today";
    layout.forEach(function (L) {
      if (L[0] === "g") { var gt = el("text", { x: 0, y: L[2] + 14, "class": "grp" }); gt.textContent = L[1]; return; }
      var r = L[1], yy = L[2], side = r.t.kind === "side", col = side ? "var(--side)" : "var(--main)";
      var g = el("g", { "class": "row", tabindex: "0", role: "button", "aria-label": r.t.name + ": show in the timeline" });
      el("rect", { "class": "hov", x: 0, y: yy, width: 1000, height: RH, rx: 6, fill: "transparent" }, g);
      var lb = el("text", { x: 8, y: yy + 19, "class": "rowlab" }, g);
      lb.textContent = r.t.name.length > 28 ? r.t.name.slice(0, 27) + "…" : r.t.name;
      var xs = sx(dayNum(r.start)), xe = sx(dayNum(r.end) + 1);
      el("rect", { x: xs, y: yy + 9, width: Math.max(6, xe - xs), height: 12, rx: 3, fill: col }, g);
      if (r.t.status === "active" && xe < tX) el("rect", { x: xe, y: yy + 9, width: tX - xe, height: 12, rx: 3, fill: "url(#" + (side ? "hatchSide" : "hatchMain") + ")", stroke: col }, g);
      r.bugs.forEach(function (e) {
        var bx = sx(dayPos(e));
        var b = el("rect", { x: bx - 2, y: yy + 5, width: 4, height: 20, rx: 1, fill: "var(--bug)" }, g);
        el("title", {}, b).textContent = fmtDay(e.date) + ": " + e.title;
      });
      r.ms.forEach(function (e) {
        var mx = sx(dayPos(e));
        var p = el("rect", { x: mx - 5, y: yy + 10, width: 10, height: 10, transform: "rotate(45 " + mx + " " + (yy + 15) + ")", fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 1.5 }, g);
        el("title", {}, p).textContent = fmtDay(e.date) + ": " + e.title;
      });
      g.addEventListener("click", function () { goThread(r.t.id); });
      g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); goThread(r.t.id); } });
    });
  }

  /* ---------------- timeline ---------------- */
  var KINDS = [["all", "All"], ["result", "Result"], ["bug", "Bug or blocker"], ["detour", "Detour or correction"], ["decision", "Decision"], ["open", "Follow-up or plan"], ["progress", "Progress"]];
  var kindF = "all", threadF = null;
  function evItem(e) {
    var refs = e.refs || {}, bits = [];
    if (refs.resolves) bits.push("Closes: " + refs.resolves.map(entryLink).join(", "));
    if (refs.corrects) bits.push("Corrects: " + refs.corrects.map(entryLink).join(", "));
    if (refs.related) bits.push("Related: " + refs.related.map(entryLink).join(", "));
    if (refs.results) bits.push("Results: " + refs.results.map(resultLink).join(", "));
    if (refs.papers) bits.push("Papers: " + refs.papers.map(function (p) { return '<a href="#digests" data-tab-link="digests">' + esc(BYID[p] ? BYID[p].title : p) + "</a>"; }).join(", "));
    if (refs.commits) bits.push("Commits: " + refs.commits.map(function (c) { return '<span class="mono">' + esc(c) + "</span>"; }).join(", "));
    if (e.resolved_by) bits.push("Closed by: " + entryLink(e.resolved_by));
    var banner = e.corrected_by.length ? '<p class="banner">Corrected later: ' + e.corrected_by.map(entryLink).join(", ") + "</p>" : "";
    return '<li class="ev" id="' + esc(e.id) + '" data-k="' + e.cat + '" data-th="' + esc(e.thread || "") + '">' +
      '<div class="when"><b>' + esc(fmtDay(e.date)) + "</b>" + (e.time ? esc(e.time) : "") + (e.imported ? '<span class="imp">imported</span>' : "") + "</div>" +
      '<div class="evbody"><div class="evhead"><span class="pill" data-k="' + e.cat + '">' + esc(e.label) + "</span>" +
      (e.verdict ? '<span class="verdict">' + esc(e.verdict.replace(/-/g, " ")) + "</span>" : "") + stateBadge(e) + threadChip(e.thread) + "</div>" +
      "<h3>" + esc(e.title) + "</h3>" + banner +
      (e.html ? '<div class="prose">' + e.html + "</div>" : "") +
      (e.paper ? '<div class="prose"><p><b>Finding:</b> ' + esc(e.paper.finding || e.paper.citation) + "</p>" +
        (e.paper.why_it_matters ? "<p><b>Why it matters here:</b> " + esc(e.paper.why_it_matters) + "</p>" : "") +
        '<p><a href="#digests" data-tab-link="digests">Full digest card →</a></p></div>' : "") +
      (bits.length ? '<p class="refs">' + bits.join("<span aria-hidden=\"true\">·</span>") + "</p>" : "") +
      (e.result ? resultCard(e, "tl", false) : "") +
      "</div></li>";
  }
  function renderTimeline() {
    var host = $('section[data-panel="timeline"]');
    var list = newestFirst.filter(function (e) { return !HIDDEN_IN_TIMELINE[e.type]; });
    host.innerHTML = '<div class="block col"><header><h2>Timeline</h2><p class="hint">Why each step was taken and what was done, newest first. Results open in place.</p></header>' +
      '<div class="filters" role="group" aria-label="Filter by kind">' + KINDS.map(function (k) {
        return '<button type="button" id="f-' + k[0] + '" data-f="' + k[0] + '"' + (k[0] !== "all" ? ' data-k="' + k[0] + '"' : "") + ' aria-pressed="' + (k[0] === "all") + '">' + (k[0] !== "all" ? "<i></i>" : "") + k[1] + "</button>";
      }).join("") + "</div>" +
      '<div class="threadbar" id="threadbar" hidden><span id="threadname"></span><button type="button" id="clearThread">Show all threads</button></div></div>' +
      (list.length ? '<ol class="tl">' + list.map(evItem).join("") + "</ol>" : '<p class="empty col">No entries yet.</p>');
    $all(".filters button", host).forEach(function (b) {
      b.addEventListener("click", function () {
        kindF = b.dataset.f;
        $all(".filters button", host).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        applyFilters();
      });
    });
    $("#clearThread").addEventListener("click", function () { threadF = null; applyFilters(); });
  }
  function applyFilters() {
    $all("li.ev").forEach(function (li) {
      li.hidden = !((kindF === "all" || li.dataset.k === kindF) && (!threadF || li.dataset.th === threadF));
    });
    $("#threadbar").hidden = !threadF;
    if (threadF) $("#threadname").textContent = "Showing only: " + (THREAD[threadF] || {}).name;
  }
  function resetFilters() {
    kindF = "all"; threadF = null;
    $all('section[data-panel="timeline"] .filters button').forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.f === "all" ? "true" : "false"); });
    applyFilters();
  }
  function goThread(id) { showTab("timeline"); resetFilters(); threadF = id; applyFilters(); }
  function flash(el) { el.classList.add("flash"); setTimeout(function () { el.classList.remove("flash"); }, 1800); }
  function goEntry(id, instant) {
    showTab("timeline", true); resetFilters();
    var li = document.getElementById(id);
    if (!li) return;
    li.scrollIntoView(instant ? { block: "center" } : smooth); flash(li);
  }
  function goResult(rid, instant) {
    showTab("timeline", true); resetFilters();
    var d = document.getElementById("tl-" + rid);
    if (!d) return;
    d.open = true; d.scrollIntoView(instant ? { block: "center" } : smooth); flash(d);
  }

  /* ---------------- results ---------------- */
  function renderResults() {
    var host = $('section[data-panel="results"]');
    var ths = D.threads.filter(function (t) { return RESULTS.some(function (e) { return e.thread === t.id; }); });
    host.innerHTML = '<div class="block col"><header><h2>Results</h2><p class="hint">Every result with its figure and where it came from, newest first.</p></header>' +
      (ths.length > 1 ? '<div class="filters" role="group" aria-label="Filter results by thread"><button type="button" id="rf-all" data-rt="" aria-pressed="true">All threads</button>' +
        ths.map(function (t) { return '<button type="button" id="rf-' + esc(t.id) + '" data-rt="' + esc(t.id) + '" aria-pressed="false">' + esc(t.name) + "</button>"; }).join("") + "</div>" : "") +
      "</div>" +
      (RESULTS.length ? '<div class="block" style="gap:14px;max-width:1040px">' + RESULTS.slice().reverse().map(function (e) {
        return '<div class="rwrap" data-th="' + esc(e.thread || "") + '">' + resultCard(e, "rs", true) + "</div>";
      }).join("") + "</div>" : '<p class="empty col">No results logged yet.</p>');
    $all("[data-rt]", host).forEach(function (b) {
      b.addEventListener("click", function () {
        $all("[data-rt]", host).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        $all(".rwrap", host).forEach(function (w) { w.hidden = !!b.dataset.rt && w.dataset.th !== b.dataset.rt; });
      });
    });
  }

  /* ---------------- side projects ---------------- */
  function renderSide() {
    var host = $('section[data-panel="side"]');
    var sides = D.threads.filter(function (t) { return t.kind === "side"; });
    host.innerHTML = '<div class="block col"><header><h2>Side projects</h2><p class="hint">Work that branched off the main line. Each one has its own row in the Gantt chart.</p></header></div>' +
      (sides.length ? '<div class="side-grid">' + sides.map(function (t) {
        var es = D.entries.filter(function (e) { return e.thread === t.id && !HIDDEN_IN_TIMELINE[e.type]; });
        var open = es.filter(function (e) { return e.status === "open"; }).length;
        var last = es.slice(-3).reverse();
        return '<div class="card side-card"><div class="meta"><span class="state ' + (t.status === "active" ? "open" : "") + '">' + esc(t.status) + "</span>" +
          (es.length ? "<span>" + esc(fmtDay(es[0].date)) + " – " + esc(fmtDay(es[es.length - 1].date)) + "</span>" : "") +
          "<span>" + es.length + " entries" + (open ? ", " + open + " open" : "") + "</span></div>" +
          "<h3>" + esc(t.name) + "</h3>" + (t.goal ? '<p class="ctx">' + esc(t.goal) + "</p>" : "") +
          (last.length ? "<ol>" + last.map(function (e) { return "<li>" + entryLink(e.id) + ' <span class="muted">' + esc(fmtDay(e.date)) + "</span></li>"; }).join("") + "</ol>" : "") +
          '<button type="button" data-thread="' + esc(t.id) + '">Show in the timeline</button></div>';
      }).join("") + "</div>" : '<p class="empty col">No side projects. Add a thread with kind: side in project.yaml.</p>');
  }

  /* ---------------- open loops / next steps ---------------- */
  function loopCard(e) {
    var closed = e.status === "closed";
    return '<li class="card loop' + (closed ? " closed" : "") + '" data-k="' + e.cat + '"><span class="box" aria-hidden="true"></span>' +
      '<div style="display:grid;gap:4px;min-width:0"><span class="q">' + entryLink(e.id) + '</span><span class="meta"><span class="pill" data-k="' + e.cat + '">' + esc(e.label) + "</span>" + threadChip(e.thread) +
      "<span>Raised " + esc(fmtDay(e.date)) + "</span>" + (closed && e.resolved_by ? "<span>Closed by " + entryLink(e.resolved_by) + "</span>" : "") + "</span></div>" +
      (closed ? "<span></span>" : '<span class="age">open ' + ageDays(e.date) + " d</span>") + "</li>";
  }
  function renderLoops() {
    var host = $('section[data-panel="loops"]');
    var loops = D.entries.filter(function (e) { return e.status && e.type !== "plan"; });
    var open = loops.filter(function (e) { return e.status === "open"; }), closed = loops.filter(function (e) { return e.status === "closed"; }).reverse();
    host.innerHTML = '<div class="block col"><header><h2>Open loops</h2><p class="hint">Follow-ups, blockers and questions that are not closed yet, oldest first.</p></header>' +
      (open.length ? '<ul class="cards">' + open.map(loopCard).join("") + "</ul>" : '<p class="empty">Nothing open. Everything raised so far has been closed.</p>') +
      (closed.length ? '<details class="closed-list"><summary>Closed (' + closed.length + ")</summary><ul class=\"cards\">" + closed.map(loopCard).join("") + "</ul></details>" : "") + "</div>";
  }
  function renderNext() {
    var host = $('section[data-panel="next"]');
    var plans = D.entries.filter(function (e) { return e.type === "plan" && e.status === "open"; });
    var byThread = {};
    plans.forEach(function (e) { (byThread[e.thread || ""] = byThread[e.thread || ""] || []).push(e); });
    var html = '<div class="block col"><header><h2>Next steps</h2><p class="hint">Planned work that has not happened yet, by thread.</p></header>';
    if (!plans.length) html += '<p class="empty">No planned steps logged.</p>';
    D.threads.concat([{ id: "", name: "Other" }]).forEach(function (t) {
      var ps = byThread[t.id];
      if (!ps) return;
      html += "<h3>" + esc(t.name) + '</h3><ul class="cards">' + ps.map(function (e) {
        return '<li class="card"><span class="q">' + entryLink(e.id) + '</span>' + (e.html ? '<div class="ctx prose">' + e.html + "</div>" : "") +
          '<span class="meta"><span>Planned ' + esc(fmtDay(e.date)) + "</span>" + ((e.refs || {}).related ? "<span>Depends on " + e.refs.related.map(entryLink).join(", ") + "</span>" : "") + "</span></li>";
      }).join("") + "</ul>";
    });
    host.innerHTML = html + "</div>";
  }

  /* ---------------- digests ---------------- */
  function renderDigests() {
    var host = $('section[data-panel="digests"]');
    var sessions = newestFirst.filter(function (e) { return e.type === "session"; });
    var papers = newestFirst.filter(function (e) { return e.type === "paper"; });
    function citedBy(p) {
      var keys = [p.id, (p.paper.doi || "").toLowerCase(), "doi:" + (p.paper.doi || "").toLowerCase()];
      return D.entries.filter(function (e) { return ((e.refs || {}).papers || []).some(function (x) { return keys.indexOf(String(x).toLowerCase()) >= 0; }); });
    }
    var html = '<div class="block col"><header><h2>Session digests</h2><p class="hint">One short paragraph per work session, written at wrap-up.</p></header>' +
      (sessions.length ? '<ul class="cards">' + sessions.map(function (e) {
        return '<li class="card session"><span class="meta"><span>' + esc(fmtDay(e.date, true)) + (e.time ? " · " + esc(e.time) : "") + "</span>" + threadChip(e.thread) + "</span><h3>" + esc(e.title) + '</h3><div class="prose">' + e.html + "</div></li>";
      }).join("") + "</ul>" : '<p class="empty">No session digests yet.</p>') + "</div>";
    html += '<div class="block col"><header><h2>Papers</h2><p class="hint">What each paper found, why it matters here, and where to look in it.</p></header>' +
      (papers.length ? '<ul class="cards">' + papers.map(function (e) {
        var p = e.paper, links = [];
        if (p.doi) links.push('<a href="https://doi.org/' + esc(p.doi.replace(/^doi:/i, "")) + '" target="_blank" rel="noopener">DOI</a>');
        if (p.url && /^https?:\/\//i.test(p.url)) links.push('<a href="' + esc(p.url) + '" target="_blank" rel="noopener">Full text</a>');
        var cites = citedBy(e);
        return '<li class="card paper" id="' + esc(e.id) + '"><h3 class="q">' + esc(e.title) + '</h3><p class="cite">' + esc(p.citation) + "</p><dl>" +
          (p.finding ? "<dt>Finding</dt><dd>" + esc(p.finding) + "</dd>" : "") +
          (p.why_it_matters ? "<dt>Why it matters here</dt><dd>" + esc(p.why_it_matters) + "</dd>" : "") +
          (p.where_to_look ? "<dt>Where to look</dt><dd>" + esc(p.where_to_look) + "</dd>" : "") +
          (p.search_phrase ? "<dt>Search the PDF for</dt><dd><q>" + esc(p.search_phrase) + "</q></dd>" : "") +
          (cites.length ? "<dt>Cited in</dt><dd>" + cites.map(function (c) { return entryLink(c.id); }).join(", ") + "</dd>" : "") +
          "</dl>" + (e.html ? '<div class="prose">' + e.html + "</div>" : "") + (links.length ? '<p class="links">' + links.join("") + "</p>" : "") + "</li>";
      }).join("") + "</ul>" : '<p class="empty">No paper digests yet.</p>') + "</div>";
    host.innerHTML = html;
  }

  /* ---------------- glossary ---------------- */
  function renderGlossary() {
    var host = $('section[data-panel="glossary"]');
    var keys = Object.keys(D.glossary).sort(function (a, b) { return D.glossary[a].term.localeCompare(D.glossary[b].term); });
    host.innerHTML = '<div class="block col"><header><h2>Glossary</h2><p class="hint">Every term is explained the first time it appears. Hover any dotted word on the page to see its entry.</p></header>' +
      (keys.length ? '<dl class="gloss">' + keys.map(function (k) {
        var g = D.glossary[k];
        return '<div id="g-' + esc(k.replace(/\s+/g, "-")) + '"><dt>' + esc(g.term) + (g.aliases.length ? "<small>also: " + g.aliases.map(esc).join(", ") + "</small>" : "") + "</dt><dd>" + g.html +
          (g.first ? '<span class="first">First used in ' + entryLink(g.first) + "</span>" : "") + "</dd></div>";
      }).join("") + "</dl>" : '<p class="empty">No terms defined yet.</p>') + "</div>";
  }

  /* ---------------- changelog ---------------- */
  function renderChangelog() {
    var host = $('section[data-panel="changelog"]');
    var rows = D.builds.slice().reverse();
    function n(list) { return list && list.length ? list.length : "–"; }
    host.innerHTML = '<div class="block col"><header><h2>Changelog</h2><p class="hint">One row per rebuild of this page. Edits to published entries are listed so nothing changes silently.</p></header></div>' +
      '<div class="tablewrap"><table><thead><tr><th>Built</th><th>Repo commit</th><th>Entries</th><th>Added</th><th>Closed</th><th>Corrected</th><th>Edited after publishing</th></tr></thead><tbody>' +
      rows.map(function (b) {
        return "<tr><td>" + esc(fmtStamp(b.built_at)) + '</td><td class="mono">' + esc(b.git_commit || "–") + (b.git_dirty ? ' <span class="dirty">+</span>' : "") + "</td><td>" + b.n_entries +
          "</td><td>" + n(b.added) + "</td><td>" + n(b.closed) + "</td><td>" + n(b.corrected) + "</td><td>" +
          (b.edited && b.edited.length ? b.edited.map(entryLink).join(", ") : "–") + "</td></tr>";
      }).join("") + "</tbody></table></div>";
  }

  /* ---------------- glossary tooltip ---------------- */
  var tip = $("#tip");
  function showTip(el) {
    var key = D.alias[el.dataset.term] || el.dataset.term, g = D.glossary[key];
    if (!g) return;
    tip.innerHTML = "<b>" + esc(g.term) + "</b>" + esc(g.text);
    tip.hidden = false;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(Math.max(8, r.left), window.innerWidth - w - 8);
    var top = r.top - h - 8 < 8 ? r.bottom + 8 : r.top - h - 8;
    tip.style.left = left + "px"; tip.style.top = top + "px";
  }
  function hideTip() { tip.hidden = true; }
  document.addEventListener("mouseover", function (e) { var t = e.target.closest && e.target.closest(".term"); if (t) showTip(t); });
  document.addEventListener("mouseout", function (e) { if (e.target.closest && e.target.closest(".term")) hideTip(); });
  document.addEventListener("focusin", function (e) { if (e.target.classList && e.target.classList.contains("term")) showTip(e.target); });
  document.addEventListener("focusout", function (e) { if (e.target.classList && e.target.classList.contains("term")) hideTip(); });
  window.addEventListener("scroll", hideTip, { passive: true });

  /* ---------------- global link handling ---------------- */
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-entry],[data-result],[data-thread],[data-tab-link]");
    if (!a || a.closest("svg")) return;
    ev.preventDefault();
    if (a.dataset.entry) goEntry(a.dataset.entry);
    else if (a.dataset.result) goResult(a.dataset.result);
    else if (a.dataset.thread) goThread(a.dataset.thread);
    else if (a.dataset.tabLink) showTab(a.dataset.tabLink);
  });

  /* ---------------- boot ---------------- */
  renderOverview(); renderTimeline(); renderResults(); renderSide(); renderLoops(); renderNext(); renderDigests(); renderGlossary(); renderChangelog();
  var h = decodeURIComponent((location.hash || "").slice(1));
  if (TAB_LABEL[h]) showTab(h);
  else if (BYRID[h]) { showTab(tabs[0]); goResult(h, true); }
  else if (BYID[h]) { showTab(tabs[0]); goEntry(h, true); }
  else showTab(tabs[0]);
})();
