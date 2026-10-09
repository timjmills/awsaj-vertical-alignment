/* Awsaj K-12 Vertical Alignment: Part 1 (collaborative standards audit)
   Static site. Standards come from data/*.json; ratings, history and comments live in Supabase
   and are written only through logged database functions (set_rating, add_comment, admin_*). */
(() => {
  "use strict";
  const CFG = window.VA_CONFIG;
  const GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];
  const DIV = { Elementary: ["K", "1", "2", "3", "4", "5"], Middle: ["6", "7", "8"], High: ["9", "10", "11", "12"] };
  const LEVEL = ["Not taught", "Introduced / exposed", "Taught in depth"];
  const LEVEL_SHORT = ["Not taught", "Introduced", "In depth"];
  const FW_NAME = { "WI-CC-MATH": "Wisconsin Math (CC)", "WI-CC-ELA": "Wisconsin ELA (CC)", "NGSS": "NGSS",
    "WI-SCI": "Wisconsin Science", "AERO-SCI": "AERO Science", "WI-SS": "Wisconsin Social Studies", "AERO-SS": "AERO Social Studies" };
  const COLORS = { none: "#FFFFFF", 0: "#E7EBEE", 1: "#8FCFD0", 2: "#0B6466", maroon: "#8A1538", line: "#E3E6EA", ink: "#1F2328" };

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const gl = (g) => (g === "K" ? "K" : "G" + g);
  const gname = (g) => (g === "K" ? "Kindergarten" : "Grade " + g);
  const divOf = (g) => Object.keys(DIV).find((d) => DIV[d].includes(g));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };

  const S = {
    meta: null, idx: {}, detail: {}, ratings: new Map(), events: [], comments: [], teams: [],
    team: null, view: "rate", lastSync: null, device: null, pending: null,
    f: { subject: "Math", framework: "", division: "all", grade: "5", strand: "", search: "" },
  };

  /* ---------------- data access ---------------- */
  const H = { apikey: CFG.supabaseKey, Authorization: "Bearer " + CFG.supabaseKey };
  async function getAll(path) {
    const out = [];
    for (let from = 0; ; from += 1000) {
      const r = await fetch(`${CFG.supabaseUrl}/rest/v1/${path}`, { headers: { ...H, "Range-Unit": "items", Range: `${from}-${from + 999}` } });
      if (!r.ok) throw new Error(await r.text());
      const rows = await r.json();
      out.push(...rows);
      if (rows.length < 1000) return out;
    }
  }
  async function rpc(fn, body) {
    const r = await fetch(`${CFG.supabaseUrl}/rest/v1/rpc/${fn}`, { method: "POST", headers: { ...H, "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) { let m = await r.text(); try { m = JSON.parse(m).message || m; } catch (e) { /* keep text */ } throw new Error(m); }
    return r.status === 204 ? null : r.json();
  }
  const rkey = (f, c, g) => `${f}|${c}|${g}`;
  function rating(f, c, g) { return S.ratings.get(rkey(f, c, g)); }

  async function loadRatings(full) {
    const q = !full && S.lastSync ? `ratings?select=*&updated_at=gt.${encodeURIComponent(S.lastSync)}` : "ratings?select=*";
    const rows = await getAll(q);
    if (full) S.ratings.clear();
    for (const r of rows) {
      S.ratings.set(rkey(r.framework, r.code, r.grade), r);
      if (!S.lastSync || r.updated_at > S.lastSync) S.lastSync = r.updated_at;
    }
    return rows.length;
  }
  async function loadEvents() { S.events = await getAll("rating_events?select=*&order=created_at.desc&limit=300"); }
  async function loadComments() { S.comments = await getAll("comments?select=*&order=created_at.desc"); }
  async function loadDetail(slug) {
    if (!S.detail[slug]) S.detail[slug] = await (await fetch(`data/detail_${slug}.json`)).json();
    return S.detail[slug];
  }

  /* ---------------- helpers over standards ---------------- */
  const subj = () => S.meta.subjects.find((s) => s.name === S.f.subject);
  const items = () => S.idx[subj().slug];
  const visibleGrades = () => (S.f.division === "all" ? GRADES : DIV[S.f.division]);
  function filtered({ ignoreDivision = false } = {}) {
    const q = S.f.search.trim().toLowerCase();
    const grades = visibleGrades();
    return items().filter((e) =>
      (!S.f.framework || e.f === S.f.framework) &&
      (!S.f.strand || e.s === S.f.strand) &&
      (ignoreDivision || S.f.division === "all" || e.pl.some((g) => grades.includes(g))) &&
      (!q || e.c.toLowerCase().includes(q) || e.t.toLowerCase().includes(q) || e.s.toLowerCase().includes(q)));
  }
  const levelsAcross = (e) => GRADES.map((g) => ({ g, r: rating(e.f, e.c, g) })).filter((x) => x.r);
  const canEdit = (g) => S.team && (S.team.name === "Vertical Alignment Committee" || S.team.grades.includes(g));
  function teamGrade() { return S.team && S.team.grades.length === 1 ? S.team.grades[0] : S.f.grade; }

  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2600);
  }
  function syncNote(msg) { $("#sync").textContent = msg; }

  async function setRating(e, g, level) {
    if (!S.team) { toast("Choose your team first (top right)."); $("#team").focus(); return; }
    if (!canEdit(g)) { toast(`Your team rates ${S.team.grades.map(gname).join(", ")}.`); return; }
    const k = rkey(e.f, e.c, g), before = S.ratings.get(k);
    S.ratings.set(k, { framework: e.f, code: e.c, grade: g, level, team: S.team.name, updated_at: new Date().toISOString() });
    rerender();
    try {
      await rpc("set_rating", { p_framework: e.f, p_code: e.c, p_grade: g, p_level: level, p_team: S.team.name, p_device: S.device });
      syncNote("Saved " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    } catch (err) {
      if (before) S.ratings.set(k, before); else S.ratings.delete(k);
      rerender(); toast("Could not save: " + err.message);
    }
  }

  /* ---------------- filters UI ---------------- */
  function fillSelect(sel, opts, value) {
    sel.innerHTML = opts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
    if (value !== undefined && opts.some(([v]) => v === value)) sel.value = value;
  }
  function refreshFilterOptions() {
    const subs = S.team && S.team.name !== "Vertical Alignment Committee" ? S.team.subjects : S.meta.subjects.map((s) => s.name);
    if (!subs.includes(S.f.subject)) S.f.subject = subs[0];
    fillSelect($("#f-subject"), subs.map((s) => [s, s]), S.f.subject);
    const fws = subj().frameworks;
    if (S.f.framework && !fws.includes(S.f.framework)) S.f.framework = "";
    fillSelect($("#f-framework"), [["", fws.length > 1 ? "All frameworks" : FW_NAME[fws[0]]], ...(fws.length > 1 ? fws.map((f) => [f, FW_NAME[f] || f]) : [])], S.f.framework);
    const strands = [...new Set(items().filter((e) => !S.f.framework || e.f === S.f.framework).map((e) => e.s).filter(Boolean))].sort();
    if (S.f.strand && !strands.includes(S.f.strand)) S.f.strand = "";
    fillSelect($("#f-strand"), [["", "All strands"], ...strands.map((s) => [s, s])], S.f.strand);
    const gs = visibleGrades();
    if (!gs.includes(S.f.grade)) S.f.grade = gs[0];
    fillSelect($("#f-grade"), gs.map((g) => [g, gname(g)]), S.f.grade);
    $("#f-division").value = S.f.division;
    $("#filters").dataset.view = S.view;
    $("#filters").dataset.committee = S.team && S.team.name === "Vertical Alignment Committee" ? "1" : "0";
  }

  /* ---------------- views ---------------- */
  function rerender() {
    const v = S.view;
    if (v === "rate") renderRate(); else if (v === "heatmap") renderHeatmap(); else if (v === "gaps") renderGaps();
    else if (v === "dashboard") renderDashboard(); else if (v === "ladder") renderLadder(); else renderActivity();
  }

  function segFor(e, g) {
    const r = rating(e.f, e.c, g);
    return `<div class="seg" role="group" aria-label="Rating for ${esc(e.c)} in ${esc(gname(g))}">` +
      [0, 1, 2].map((l) => `<button data-act="rate" data-k="${esc(e.f + "|" + e.c)}" data-g="${g}" data-l="${l}" aria-pressed="${r && r.level === l}">${LEVEL_SHORT[l]}</button>`).join("") + `</div>`;
  }
  function stdRow(e, g, note) {
    const r = rating(e.f, e.c, g);
    const tags = [];
    if (subj().frameworks.length > 1) tags.push(`<span class="tag">${esc(FW_NAME[e.f] || e.f)}</span>`);
    if (e.ee) { const ee = e.ee.split(";")[0].trim(); tags.push(`<span class="tag">${/^(M\.)?EE/.test(ee) || ee.startsWith("SS.EE") ? "" : "EE "}${esc(ee)}</span>`); }
    if (note) tags.push(`<span class="tag sg">${esc(note)}</span>`);
    return `<div class="std"><div><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}">${esc(e.c)}</button></div>
      <div><div class="txt">${esc(e.t)}${e.t.length >= 220 ? "…" : ""}</div><div class="tags">${tags.join("")}</div></div>
      <div>${segFor(e, g)}</div>${r ? `<div class="who">${esc(r.team)} · ${new Date(r.updated_at).toLocaleDateString()}</div>` : ""}</div>`;
  }
  function groupByStrand(list, g, noteFn) {
    let html = "", last = null;
    for (const e of list) {
      if (e.s !== last) { html += `<div class="strand">${esc(e.s || "Standards")}</div>`; last = e.s; }
      html += stdRow(e, g, noteFn && noteFn(e));
    }
    return html;
  }
  function progressBar(list, g) {
    const c = [0, 0, 0, 0];
    for (const e of list) { const r = rating(e.f, e.c, g); c[r ? r.level : 3]++; }
    const n = list.length || 1;
    const seg = (i, col) => (c[i] ? `<i style="width:${(c[i] / n) * 100}%;background:${col}"></i>` : "");
    return `<div class="progress"><div class="bar">${seg(2, COLORS[2])}${seg(1, COLORS[1])}${seg(0, "#C9D0D6")}</div>
      <span>${list.length - c[3]} of ${list.length} rated · ${c[2]} in depth</span></div>`;
  }

  function renderRate() {
    const el = $("#view-rate");
    if (!S.team) {
      el.innerHTML = `<div class="panel"><h2>Welcome</h2><p class="lede">Choose your team at the top right. You will see the standards for your grade, and you can mark each one as
        <b>Not taught</b>, <b>Introduced / exposed</b> or <b>Taught in depth</b>. Every change is saved straight away and recorded with your team name.</p></div>`;
      return;
    }
    const g = teamGrade();
    const all = filtered({ ignoreDivision: true });
    const placed = all.filter((e) => e.pl.includes(g));
    const band = all.filter((e) => !e.pl.includes(g) && e.sg && e.div.includes(divOf(g)));
    const committee = S.team.name === "Vertical Alignment Committee";
    el.innerHTML = `<div class="panel">
      <div class="rate-head"><div><h2>${esc(S.f.subject)} · ${esc(gname(g))}${S.team.grades.length === 1 && !committee ? "" : ""}</h2>
      <p class="lede">For each standard, choose how it is taught in ${esc(gname(g))} this year. Use what is really taught, even if the plans do not show it yet.</p></div>
      ${progressBar(placed.concat(band.filter((e) => rating(e.f, e.c, g))), g)}</div>
      ${committee ? `<p class="muted">Committee view: pick a grade with the Grade filter above.</p>` : ""}
      <div class="group-title"><h3>Standards suggested for ${esc(gname(g))} (${placed.length})</h3></div>
      ${placed.length ? groupByStrand(placed, g, (e) => (e.sg ? "Suggested placement" : "")) : `<div class="empty">No standards match these filters.</div>`}
      ${band.length ? `<div class="group-title"><h3>Other ${esc(divOf(g).toLowerCase())} school standards (${band.length})</h3>
        <span class="muted">Placement of these is a suggestion. Mark any that ${esc(gname(g))} actually teaches.</span></div>
        ${groupByStrand(band, g, (e) => "Suggested for " + e.pl.map(gname).join(", "))}` : ""}
    </div>`;
  }

  function renderHeatmap() {
    const el = $("#view-heatmap"), gs = visibleGrades(), list = filtered();
    if (!list.length) { el.innerHTML = `<div class="panel empty">No standards match these filters.</div>`; return; }
    let rows = "", last = null;
    for (const e of list) {
      const head = (subj().frameworks.length > 1 ? (FW_NAME[e.f] || e.f) + " · " : "") + (e.s || "");
      if (head !== last) { rows += `<tr class="strand-row"><td colspan="${gs.length + 1}">${esc(head)}</td></tr>`; last = head; }
      rows += `<tr><td class="rowh"><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}" title="${esc(e.t)}">${esc(e.c)}</button></td>` +
        gs.map((g) => {
          const r = rating(e.f, e.c, g), placed = e.pl.includes(g);
          const cls = ["cell", r ? "l" + r.level : "", placed ? "placed" : "", r && r.level > 0 && !placed ? "off" : ""].join(" ");
          return `<td><button class="${cls}" data-act="open" data-k="${esc(e.f + "|" + e.c)}" data-g="${g}" data-tip="1"
            aria-label="${esc(e.c)}, ${esc(gname(g))}: ${r ? LEVEL[r.level] : "not rated"}${placed ? ", suggested grade" : ""}"></button></td>`;
        }).join("") + `</tr>`;
    }
    const rated = list.filter((e) => levelsAcross(e).length).length;
    el.innerHTML = `<div class="panel"><h2>${esc(S.f.subject)} coverage, ${S.f.division === "all" ? "K-12" : esc(S.f.division) + " school"}</h2>
      <p class="lede">${list.length} standards. ${rated} have at least one rating. Each row is a standard and each column a grade. A maroon outline marks the grade the standard is suggested for; a dot marks a grade that reports teaching it somewhere else.</p></div>
      <div class="hm-wrap" id="hm"><table class="hm"><thead><tr><th class="rowh">Standard</th>${gs.map((g) => `<th>${gl(g)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function analyse(list) {
    const out = { noDepth: [], unrated: [], placedNot: [], repeat: [], elsewhere: [] };
    for (const e of list) {
      const lv = levelsAcross(e);
      if (!lv.length) { out.unrated.push(e); continue; }
      if (!lv.some((x) => x.r.level === 2)) out.noDepth.push(e);
      const deep = lv.filter((x) => x.r.level === 2);
      if (deep.length >= 2) out.repeat.push({ e, gs: deep.map((x) => x.g) });
      for (const x of lv) {
        if (e.pl.includes(x.g) && x.r.level === 0) out.placedNot.push({ e, g: x.g });
        if (!e.pl.includes(x.g) && x.r.level > 0) out.elsewhere.push({ e, g: x.g, l: x.r.level });
      }
    }
    return out;
  }
  function li(e, extra) { return `<li><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}">${esc(e.c)}</button> ${extra || ""} <span class="muted">${esc(e.t.slice(0, 90))}${e.t.length > 90 ? "…" : ""}</span></li>`; }
  function renderGaps() {
    const el = $("#view-gaps"), list = filtered(), a = analyse(list), n = list.length;
    const pct = (x) => (n ? Math.round((x / n) * 100) : 0);
    const sec = (title, desc, arr, fn, open) => `<details class="gap" ${open ? "open" : ""}><summary><span class="count">${arr.length}</span>${title}</summary>
      <p class="muted">${desc}</p><ul class="gap-list">${arr.slice(0, 400).map(fn).join("") || "<li class='muted'>None.</li>"}</ul></details>`;
    el.innerHTML = `<div class="panel"><h2>Gaps and repetition: ${esc(S.f.subject)}${S.f.division === "all" ? "" : ", " + esc(S.f.division) + " school"}</h2>
      <div class="summary"><p>${n} standards in view. ${n - a.unrated.length} (${pct(n - a.unrated.length)}%) have been rated by at least one grade.</p>
      <p>${a.noDepth.length} rated standards are not yet taught in depth in any grade${a.noDepth.length ? ", which makes them the clearest gaps" : ""}.
      ${a.repeat.length} are taught in depth in two or more grades: check that each grade builds on the one before rather than repeating it.</p>
      <p>${a.elsewhere.length} reports come from a grade other than the suggested one. These are the standards the committee may want to move.</p></div>
      ${sec("Not yet taught in depth anywhere", "Rated, but no grade reports teaching it in depth.", a.noDepth, (e) => li(e, `<span class="tag">${e.pl.map(gl).join(", ")}</span>`), true)}
      ${sec("Marked “not taught” in the suggested grade", "The grade the standard is suggested for says it is not taught there.", a.placedNot, (x) => li(x.e, `<span class="tag">${gl(x.g)}</span>`))}
      ${sec("Taught in a different grade", "A grade reports teaching a standard that is suggested for another grade.", a.elsewhere, (x) => li(x.e, `<span class="tag sg">${gl(x.g)} · ${LEVEL_SHORT[x.l]} (suggested ${x.e.pl.map(gl).join(", ")})</span>`), true)}
      ${sec("Taught in depth in more than one grade", "Possible repetition. Make sure the expectation rises each year.", a.repeat, (x) => li(x.e, `<span class="tag">${x.gs.map(gl).join(", ")}</span>`))}
      ${sec("Not rated yet", "No grade has rated these standards.", a.unrated, (e) => li(e, `<span class="tag">${e.pl.map(gl).join(", ")}</span>`))}
    </div>`;
  }

  function renderDashboard() {
    const el = $("#view-dashboard"), g = S.f.grade;
    const list = filtered({ ignoreDivision: true }).filter((e) => e.pl.includes(g));
    const counts = (arr) => { const c = [0, 0, 0, 0]; arr.forEach((e) => { const r = rating(e.f, e.c, g); c[r ? r.level : 3]++; }); return c; };
    const tot = counts(list), n = list.length || 1;
    const byStrand = {};
    list.forEach((e) => (byStrand[e.s || "Other"] ||= []).push(e));
    const strands = Object.entries(byStrand).map(([s, arr]) => ({ s, arr, c: counts(arr) }));
    strands.forEach((x) => (x.score = (x.c[2] + 0.5 * x.c[1]) / (x.arr.length - x.c[3] || 1)));
    const ratedStrands = strands.filter((x) => x.arr.length - x.c[3] > 0).sort((a, b) => b.score - a.score);
    const extra = filtered({ ignoreDivision: true }).filter((e) => !e.pl.includes(g) && (rating(e.f, e.c, g)?.level || 0) > 0);
    const bars = strands.map((x) => {
      const w = (i) => (x.c[i] / x.arr.length) * 100;
      return `<div>${esc(x.s)}</div><div class="sb" role="img" aria-label="${esc(x.s)}: ${x.c[2]} in depth, ${x.c[1]} introduced, ${x.c[0]} not taught, ${x.c[3]} not rated">
        ${[[2, COLORS[2]], [1, COLORS[1]], [0, "#C9D0D6"], [3, "#F2F4F6"]].map(([i, col]) => (x.c[i] ? `<i style="width:${w(i)}%;background:${col}" data-tip-text="${esc(x.s)}: ${x.c[i]} ${i === 3 ? "not rated" : LEVEL[i].toLowerCase()}"></i>` : "")).join("")}</div>
        <div class="num">${x.c[2]}/${x.arr.length}</div>`;
    }).join("");
    const strong = ratedStrands[0], weak = ratedStrands[ratedStrands.length - 1];
    el.innerHTML = `<div class="panel"><h2>${esc(gname(g))} · ${esc(S.f.subject)}</h2>
      <div class="tiles">
        <div class="tile"><div class="n">${list.length}</div><div class="l">standards suggested for this grade</div></div>
        <div class="tile"><div class="n">${Math.round(((list.length - tot[3]) / n) * 100)}%</div><div class="l">rated so far</div></div>
        <div class="tile"><div class="n">${tot[2]}</div><div class="l">taught in depth</div></div>
        <div class="tile"><div class="n">${tot[1]}</div><div class="l">introduced or exposed</div></div>
        <div class="tile"><div class="n">${tot[0]}</div><div class="l">not taught</div></div>
        <div class="tile"><div class="n">${extra.length}</div><div class="l">taught here but suggested for another grade</div></div>
      </div>
      <div class="summary">${list.length - tot[3] === 0 ? `<p>No ratings yet for ${esc(gname(g))}. Once the team rates its standards, this summary fills in.</p>` :
        `<p>${esc(gname(g))} has rated ${list.length - tot[3]} of ${list.length} ${esc(S.f.subject)} standards. ${tot[2]} are taught in depth and ${tot[1]} are introduced; ${tot[0]} are not taught this year.</p>
        ${strong && weak && strong !== weak ? `<p>Strongest coverage: <b>${esc(strong.s)}</b>. Most room to grow: <b>${esc(weak.s)}</b>.</p>` : ""}
        ${extra.length ? `<p>The team also teaches ${extra.length} standard${extra.length > 1 ? "s" : ""} suggested for other grades (see Gaps &amp; repetition).</p>` : ""}`}</div>
      <h3>Coverage by strand</h3><div class="strand-bars" id="dash-bars">${bars || "<div class='muted'>No standards.</div>"}</div></div>`;
  }

  function renderLadder() {
    const el = $("#view-ladder"), gs = visibleGrades();
    const strands = [...new Set(items().filter((e) => !S.f.framework || e.f === S.f.framework).map((e) => e.s).filter(Boolean))].sort();
    const g0 = teamGrade(), inG = filtered().filter((e) => e.pl.includes(g0));
    const strand = S.f.strand || (inG[0] && inG[0].s) || strands[0];
    const list = filtered().filter((e) => e.s === strand);
    const rungs = gs.map((g) => {
      const here = list.filter((e) => e.pl.includes(g));
      const moved = list.filter((e) => !e.pl.includes(g) && (rating(e.f, e.c, g)?.level || 0) > 0);
      const chip = (e, m) => { const r = rating(e.f, e.c, g); return `<button class="chip ${r ? "l" + r.level : ""}" data-act="open" data-k="${esc(e.f + "|" + e.c)}" style="${m ? "border-style:dashed" : ""}">${esc(e.c)}<small>${esc(e.t.slice(0, 60))}${e.t.length > 60 ? "…" : ""}</small></button>`; };
      return `<div class="rung"><h4>${esc(gname(g))} <span class="muted">(${here.length})</span></h4>${here.map((e) => chip(e)).join("")}${moved.length ? `<div class="muted" style="font-size:11px;margin:6px 0 4px">Also taught here</div>${moved.map((e) => chip(e, true)).join("")}` : ""}</div>`;
    }).join("");
    el.innerHTML = `<div class="panel"><h2>Progression: ${esc(strand || "")}</h2>
      <p class="lede">How one strand builds from grade to grade. Colour shows how each grade rates the standard. Pick another strand with the Strand filter.</p></div>
      <div class="ladder">${rungs}</div>`;
  }

  function renderActivity() {
    const el = $("#view-activity");
    const rows = S.events.slice(0, 200).map((ev) => `<tr class="${ev.undone ? "undone" : ""}"><td>${new Date(ev.created_at).toLocaleString()}</td><td>${esc(ev.team)}</td>
      <td><button class="code" data-act="open" data-k="${esc(ev.framework + "|" + ev.code)}">${esc(ev.code)}</button></td><td>${gl(ev.grade)}</td>
      <td>${ev.old_level == null ? "Not rated" : LEVEL_SHORT[ev.old_level]} → ${LEVEL_SHORT[ev.new_level]}</td>
      <td>${ev.undone ? "Undone" : `<button class="ghost" data-act="undo" data-id="${ev.id}">Undo</button>`}</td></tr>`).join("");
    const crow = S.comments.slice(0, 50).map((c) => `<tr><td>${new Date(c.created_at).toLocaleString()}</td><td>${esc(c.team)}${c.author ? " · " + esc(c.author) : ""}</td>
      <td><button class="code" data-act="open" data-k="${esc(c.framework + "|" + c.code)}">${esc(c.code)}</button></td><td colspan="2">${esc(c.body)}</td>
      <td><button class="ghost" data-act="hide" data-id="${c.id}">Hide</button></td></tr>`).join("");
    el.innerHTML = `<div class="panel"><h2>Recent changes</h2><p class="lede">Every rating change, newest first. Undo needs the committee passcode.</p>
      <table class="log"><thead><tr><th>When</th><th>Team</th><th>Standard</th><th>Grade</th><th>Change</th><th></th></tr></thead><tbody>${rows || "<tr><td colspan='6' class='muted'>No changes yet.</td></tr>"}</tbody></table></div>
      <div class="panel"><h2>Recent comments</h2><table class="log"><thead><tr><th>When</th><th>Team</th><th>Standard</th><th colspan="2">Comment</th><th></th></tr></thead><tbody>${crow || "<tr><td colspan='6' class='muted'>No comments yet.</td></tr>"}</tbody></table></div>`;
  }

  /* ---------------- detail popup ---------------- */
  function findItem(k) { const [f, c] = k.split("|"); return items().find((e) => e.f === f && e.c === c) || Object.values(S.idx).flat().find((e) => e.f === f && e.c === c); }
  async function openDetail(k) {
    const e = findItem(k); if (!e) return;
    const sub = S.meta.subjects.find((s) => S.idx[s.slug].includes(e));
    const det = await loadDetail(sub.slug);
    const d = det[`${e.f}|${e.c}|${e.pl[0]}`] || {};
    const desc = d.descriptors || {};
    const lvl = (o) => `<dl class="levels">${[["cc_advanced", "Advanced"], ["cc_at_target", "At target"], ["cc_approaching", "Approaching"], ["cc_emerging", "Emerging"]]
      .filter(([x]) => o[x]).map(([x, l]) => `<dt>${l}</dt><dd>${esc(o[x])}</dd>`).join("")}</dl>`;
    const strip = GRADES.map((g) => {
      const r = rating(e.f, e.c, g), placed = e.pl.includes(g);
      return `<div><button class="cell ${r ? "l" + r.level : ""} ${placed ? "placed" : ""}" data-act="cycle" data-k="${esc(k)}" data-g="${g}"
        aria-label="${esc(gname(g))}: ${r ? LEVEL[r.level] : "not rated"}${canEdit(g) ? ". Click to change" : ""}" title="${esc(gname(g))}: ${r ? LEVEL[r.level] + " (" + esc(r.team) + ")" : "not rated"}"></button>${gl(g)}</div>`;
    }).join("");
    const pg = GRADES.indexOf(e.pl[0]);
    const rel = (g) => (g ? items().filter((x) => x.f === e.f && x.s === e.s && x.pl.includes(g)).slice(0, 6) : []);
    const relList = (g) => { const r = rel(g); return r.length ? r.map((x) => `<li><button class="code" data-act="open" data-k="${esc(x.f + "|" + x.c)}">${esc(x.c)}</button> <span class="muted">${esc(x.t.slice(0, 80))}…</span></li>`).join("") : "<li class='muted'>None in this strand.</li>"; };
    const comments = S.comments.filter((c) => c.framework === e.f && c.code === e.c);
    const hist = S.events.filter((ev) => ev.framework === e.f && ev.code === e.c).slice(0, 12);
    $("#d-eyebrow").textContent = `${FW_NAME[e.f] || e.f} · ${e.s || ""}`;
    $("#d-title").textContent = e.c;
    $("#d-body").innerHTML = `
      <p class="stdtext">${esc(d.text || e.t)}</p>
      <p class="muted">Suggested for ${e.pl.map(gname).join(", ")}${e.sg ? " (a suggestion: teachers confirm the grade in Part 1)" : ""}${d.course ? " · " + esc(d.course) : ""}${d.cluster ? " · " + esc(d.cluster) : ""}</p>
      <div class="box"><h3>How each grade teaches it</h3><div class="strip">${strip}</div>
        <p class="muted" style="margin:8px 0 0">${S.team ? "Click your grade's square to change its rating." : "Choose your team to rate."}</p></div>
      ${d.descriptor_flag ? `<div class="flagbox"><b>Committee review:</b> ${esc(d.descriptor_flag)}. A suggested version is shown beside the school descriptor.</div>` : ""}
      <div class="grid2" style="margin-top:14px">
        <div class="box"><h3>"I can" levels ${d.descriptor_source === "draft" ? '<span class="tag flag">draft</span>' : '<span class="tag">school</span>'}</h3>${lvl(desc)}</div>
        <div class="box"><h3>Essential Element ${esc(e.ee || "")}</h3><p>${esc(d.ee_text || "No Essential Element for this standard.")}</p>
          ${desc.ee_at_target && !String(desc.ee_at_target).startsWith("Not applicable") ? `<dl class="levels"><dt>EE at target</dt><dd>${esc(desc.ee_at_target)}</dd></dl>` : ""}</div>
      </div>
      ${d.descriptors_suggested ? `<div class="box" style="margin-top:14px"><h3>Suggested "I can" levels <span class="tag flag">draft</span></h3>${lvl(d.descriptors_suggested)}</div>` : ""}
      <div class="grid2 related" style="margin-top:14px">
        <div class="box"><h3>Same strand, grade before</h3><ul class="gap-list" style="columns:1">${relList(GRADES[pg - 1])}</ul></div>
        <div class="box"><h3>Same strand, grade after</h3><ul class="gap-list" style="columns:1">${relList(GRADES[pg + 1])}</ul></div>
      </div>
      ${(d.crosswalk || []).length ? `<p class="muted" style="margin-top:12px">Related codes in other frameworks: ${d.crosswalk.map(esc).join(", ")}</p>` : ""}
      <div class="grid2" style="margin-top:14px">
        <div class="box"><h3>Comments</h3><ul class="comments">${comments.map((c) => `<li>${esc(c.body)}<div class="meta">${esc(c.team)}${c.author ? " · " + esc(c.author) : ""} · ${new Date(c.created_at).toLocaleDateString()}</div></li>`).join("") || "<li class='muted'>No comments yet.</li>"}</ul>
          <label class="muted" for="c-body" style="display:block;margin-top:8px">Add a comment${S.team ? "" : " (choose your team first)"}</label>
          <textarea id="c-body" maxlength="2000" ${S.team ? "" : "disabled"}></textarea>
          <input id="c-author" placeholder="Your name (optional)" style="margin-top:6px;width:100%" ${S.team ? "" : "disabled"}>
          <div class="row-end"><button data-act="comment" data-k="${esc(k)}" ${S.team ? "" : "disabled"}>Post comment</button></div></div>
        <div class="box"><h3>History</h3><ul class="comments">${hist.map((ev) => `<li>${gl(ev.grade)}: ${ev.old_level == null ? "Not rated" : LEVEL_SHORT[ev.old_level]} → ${LEVEL_SHORT[ev.new_level]}<div class="meta">${esc(ev.team)} · ${new Date(ev.created_at).toLocaleString()}${ev.undone ? " · undone" : ""}</div></li>`).join("") || "<li class='muted'>No changes yet.</li>"}</ul>
          <h3 style="margin-top:12px">Curriculum evidence</h3><p class="muted">Where this standard appears in the 2025-26 and 2026-27 plans will show here once Part 2 is running.</p></div>
      </div>
      <p class="muted" style="margin-top:12px;font-size:12px">Source: ${esc(d.source || "")}</p>`;
    $("#detail").dataset.k = k;
    if (!$("#detail").open) $("#detail").showModal();
  }

  /* ---------------- exports ---------------- */
  function download(name, blob) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }
  function csvCell(v) { v = String(v ?? ""); return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; }
  function exportCSV() {
    const gs = S.view === "rate" || S.view === "dashboard" ? [S.view === "rate" ? teamGrade() : S.f.grade] : visibleGrades();
    const list = S.view === "activity" ? null : filtered({ ignoreDivision: S.view === "rate" || S.view === "dashboard" });
    let rows;
    if (!list) rows = [["When", "Team", "Framework", "Code", "Grade", "From", "To", "Undone"], ...S.events.map((e) => [e.created_at, e.team, e.framework, e.code, e.grade, e.old_level == null ? "" : LEVEL[e.old_level], LEVEL[e.new_level], e.undone])];
    else rows = [["Subject", "Framework", "Code", "Strand", "Suggested grade(s)", "Standard", ...gs.map(gname)],
      ...list.map((e) => [S.f.subject, e.f, e.c, e.s, e.pl.join(" "), e.t, ...gs.map((g) => { const r = rating(e.f, e.c, g); return r ? LEVEL[r.level] : ""; })])];
    download(`awsaj-${S.view}-${S.f.subject.replace(/\s/g, "")}.csv`, new Blob(["﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\n")], { type: "text/csv" }));
  }
  function exportPNG() {
    const gs = visibleGrades(), list = filtered(), cw = 26, ch = 16, gap = 2, left = 150, top = 70, pad = 20;
    const W = left + gs.length * (cw + gap) + pad, Hh = top + list.length * (ch + gap) + 50;
    if (list.length > 1500) { toast("Too many rows for one image. Narrow the filters first."); return; }
    const c = document.createElement("canvas"), dpr = 2; c.width = W * dpr; c.height = Hh * dpr;
    const x = c.getContext("2d"); x.scale(dpr, dpr); x.fillStyle = "#fff"; x.fillRect(0, 0, W, Hh);
    x.fillStyle = COLORS.maroon; x.fillRect(0, 0, W, 5);
    x.fillStyle = COLORS.ink; x.font = "600 16px Georgia"; x.fillText(`Awsaj Academy · ${S.f.subject} coverage ${S.f.division === "all" ? "K-12" : S.f.division}`, pad, 30);
    x.font = "11px sans-serif"; x.fillStyle = "#4A5058"; x.fillText(new Date().toLocaleDateString(), pad, 48);
    gs.forEach((g, i) => x.fillText(gl(g), left + i * (cw + gap) + 6, top - 6));
    list.forEach((e, r) => {
      const y = top + r * (ch + gap);
      x.fillStyle = COLORS.ink; x.fillText(e.c.slice(0, 22), pad, y + 12);
      gs.forEach((g, i) => {
        const rt = rating(e.f, e.c, g), X = left + i * (cw + gap);
        x.fillStyle = rt ? COLORS[rt.level] : COLORS.none; x.strokeStyle = e.pl.includes(g) ? COLORS.maroon : COLORS.line; x.lineWidth = e.pl.includes(g) ? 2 : 1;
        x.beginPath(); x.roundRect(X, y, cw, ch, 3); x.fill(); x.stroke();
      });
    });
    const ly = Hh - 26; [["Not rated", COLORS.none], ["Not taught", COLORS[0]], ["Introduced", COLORS[1]], ["In depth", COLORS[2]]].forEach(([l, col], i) => {
      x.fillStyle = col; x.strokeStyle = COLORS.line; x.fillRect(pad + i * 110, ly, 14, 14); x.strokeRect(pad + i * 110, ly, 14, 14); x.fillStyle = COLORS.ink; x.fillText(l, pad + i * 110 + 20, ly + 11);
    });
    c.toBlob((b) => download(`awsaj-heatmap-${S.f.subject.replace(/\s/g, "")}.png`, b));
  }

  /* ---------------- events ---------------- */
  let adminAction = null;
  function askAdmin(fn) { adminAction = fn; $("#a-pass").value = ""; $("#admin").showModal(); $("#a-pass").focus(); }
  document.addEventListener("click", async (ev) => {
    const b = ev.target.closest("[data-act]"); if (!b) return;
    const act = b.dataset.act;
    if (act === "rate") { const e = findItem(b.dataset.k); const l = +b.dataset.l; const cur = rating(e.f, e.c, b.dataset.g); if (cur && cur.level === l) return; setRating(e, b.dataset.g, l); }
    else if (act === "open") openDetail(b.dataset.k);
    else if (act === "cycle") {
      const e = findItem(b.dataset.k), g = b.dataset.g, cur = rating(e.f, e.c, g);
      if (!canEdit(g)) { toast(S.team ? `Your team rates ${S.team.grades.map(gname).join(", ")}.` : "Choose your team first."); return; }
      await setRating(e, g, cur ? (cur.level + 1) % 3 : 1); openDetail(b.dataset.k);
    } else if (act === "comment") {
      const body = $("#c-body").value.trim(); if (!body) return;
      const e = findItem(b.dataset.k);
      try { await rpc("add_comment", { p_framework: e.f, p_code: e.c, p_grade: teamGrade(), p_team: S.team.name, p_author: $("#c-author").value.trim(), p_body: body });
        await loadComments(); openDetail(b.dataset.k); toast("Comment posted"); } catch (err) { toast("Could not post: " + err.message); }
    } else if (act === "undo") askAdmin(async (p) => { await rpc("admin_undo", { p_event_id: +b.dataset.id, p_passcode: p }); await Promise.all([loadRatings(true), loadEvents()]); rerender(); toast("Change undone"); });
    else if (act === "hide") askAdmin(async (p) => { await rpc("admin_hide_comment", { p_comment_id: +b.dataset.id, p_passcode: p }); await loadComments(); rerender(); toast("Comment hidden"); });
  });
  $("#a-go").addEventListener("click", async () => { try { await adminAction($("#a-pass").value); $("#admin").close(); } catch (err) { toast(err.message === "not allowed" ? "Wrong passcode" : err.message); } });
  $$("dialog [data-close], #d-close").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
  $("#detail").addEventListener("close", () => rerender());

  // tooltip for heatmap cells and bars
  const tip = $("#tip");
  document.addEventListener("mouseover", (ev) => {
    const c = ev.target.closest("[data-tip],[data-tip-text]"); if (!c) { tip.hidden = true; return; }
    if (c.dataset.tipText) tip.innerHTML = esc(c.dataset.tipText);
    else { const e = findItem(c.dataset.k), g = c.dataset.g, r = rating(e.f, e.c, g);
      tip.innerHTML = `<b>${esc(e.c)}</b> · ${esc(gname(g))}<br>${r ? LEVEL[r.level] + " · " + esc(r.team) : "Not rated"}${e.pl.includes(g) ? "<br>Suggested grade" : ""}<br><span style="opacity:.8">${esc(e.t.slice(0, 120))}…</span>`; }
    tip.hidden = false;
  });
  document.addEventListener("mousemove", (ev) => { if (!tip.hidden) { tip.style.left = Math.min(ev.clientX + 14, innerWidth - 360) + "px"; tip.style.top = ev.clientY + 14 + "px"; } });

  $$(".tabs [data-view]").forEach((b) => b.addEventListener("click", () => {
    S.view = b.dataset.view; $$(".tabs [data-view]").forEach((x) => x.setAttribute("aria-selected", x === b));
    $$(".view").forEach((v) => (v.hidden = v.id !== "view-" + S.view));
    store.set("va_view", S.view); refreshFilterOptions(); rerender();
    if (S.view === "activity") Promise.all([loadEvents(), loadComments()]).then(rerender);
  }));
  const bindF = (id, key) => $(id).addEventListener(id === "#f-search" ? "input" : "change", (ev) => { S.f[key] = ev.target.value; refreshFilterOptions(); rerender(); });
  bindF("#f-subject", "subject"); bindF("#f-framework", "framework"); bindF("#f-division", "division"); bindF("#f-grade", "grade"); bindF("#f-strand", "strand"); bindF("#f-search", "search");
  $("#team").addEventListener("change", (ev) => { setTeam(ev.target.value); store.set("va_team", ev.target.value); });
  $("#x-csv").addEventListener("click", exportCSV); $("#x-png").addEventListener("click", exportPNG); $("#x-pdf").addEventListener("click", () => window.print());

  function setTeam(name) {
    S.team = S.teams.find((t) => t.name === name) || null;
    if (S.team && S.team.name !== "Vertical Alignment Committee") {
      S.f.subject = S.team.subjects[0]; S.f.grade = S.team.grades[0]; S.f.division = "all"; S.f.strand = "";
      S.f.framework = S.f.subject === "Science" && !DIV.Elementary.includes(S.f.grade) ? "NGSS" : "";
    }
    refreshFilterOptions(); rerender();
  }

  /* ---------------- start ---------------- */
  async function start() {
    S.device = store.get("va_device") || Math.random().toString(36).slice(2, 12); store.set("va_device", S.device);
    S.meta = await (await fetch("data/meta.json")).json();
    S.teams = S.meta.teams;
    await Promise.all(S.meta.subjects.map(async (s) => (S.idx[s.slug] = await (await fetch(`data/index_${s.slug}.json`)).json())));
    const groups = { "Committee": [], "Elementary": [], "Middle school": [], "High school": [] };
    S.teams.forEach((t) => (t.name === "Vertical Alignment Committee" ? groups.Committee : DIV.Elementary.includes(t.grades[0]) ? groups.Elementary : DIV.Middle.includes(t.grades[0]) ? groups["Middle school"] : groups["High school"]).push(t));
    $("#team").innerHTML = `<option value="">Choose your team</option>` + Object.entries(groups).map(([g, ts]) => `<optgroup label="${g}">${ts.map((t) => `<option>${esc(t.name)}</option>`).join("")}</optgroup>`).join("");
    const saved = store.get("va_team"); if (saved && S.teams.some((t) => t.name === saved)) { $("#team").value = saved; setTeam(saved); }
    const v = store.get("va_view"); if (v && $(`.tabs [data-view="${v}"]`)) $(`.tabs [data-view="${v}"]`).click(); else { refreshFilterOptions(); rerender(); }
    try { await Promise.all([loadRatings(true), loadEvents(), loadComments()]); syncNote("Up to date"); rerender(); }
    catch (err) { syncNote("Offline: ratings could not load"); }
    let n = 0;
    setInterval(async () => {
      if (document.hidden) return;
      try { n++; const got = await loadRatings(n % 15 === 0); if (got) { rerender(); } syncNote("Up to date " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })); }
      catch (e) { syncNote("Reconnecting…"); }
    }, CFG.refreshSeconds * 1000);
  }
  start();
})();
