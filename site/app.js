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
  // Awsaj brand: ratings use three of the four symbol ribbons (orange is kept for highlights so it never sits next to lime).
  const COLORS = { none: "#FFFFFF", 0: "#D00070", placed: "#024638", 1: "#0092BC", 2: "#78BE21", maroon: "#024638", accent: "#ED8B00", line: "#D9E1E2", ink: "#1E2324" };

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
    team: null, view: "rate", explore: false, flow: { subject: null, skipped: new Set(), back: null, history: [] }, lastSync: null, device: null, pending: null,
    f: { subject: "Math", framework: "", division: "all", grade: "", strand: "", search: "" },
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
  // The grade the Strand menu follows: the team's own grade on Rate, otherwise the Grade filter. "" = none chosen.
  const strandGrade = () => (S.view === "rate" ? teamGrade() : S.f.grade);
  // Standards a grade works with: those suggested for it, plus band standards it may claim (same set as the Rate page).
  const forGrade = (e, g) => e.pl.includes(g) || (e.sg && e.div.includes(divOf(g)));
  const pickGrade = (el, what) => { el.innerHTML = `<div class="panel empty">Choose a grade with the Grade filter above to see ${what}.</div>`; };

  const hb = (k) => `<button type="button" class="help" data-help="${k}" aria-label="What is this?">?</button>`;
  // action: optional [label, fn] shown as a button in the toast (used for Undo), which then stays up longer.
  function toast(msg, action) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    if (action) {
      const b = document.createElement("button"); b.type = "button"; b.textContent = action[0];
      b.addEventListener("click", () => { t.hidden = true; action[1](); }); t.append(" ", b);
    }
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), action ? 10000 : 2600);
  }
  function syncNote(msg) { $("#sync").textContent = msg; }

  async function setRating(e, g, level) {
    if (!S.team) { toast("Choose your team first (top right)."); $("#team").focus(); return; }
    if (!canEdit(g)) { toast(`Your team rates ${S.team.grades.map(gname).join(", ")}.`); return; }
    const k = rkey(e.f, e.c, g), before = S.ratings.get(k);
    const leftBefore = toRateLeft(g), strandBefore = strandLeft(e, g);
    S.ratings.set(k, { framework: e.f, code: e.c, grade: g, level, team: S.team.name, updated_at: new Date().toISOString() });
    S.flash = k; rerender(); S.flash = null;
    const leftAfter = toRateLeft(g), undo = ["Undo", () => undoRating(e, g, before)];
    const finished = Object.keys(leftAfter).find((sb) => leftBefore[sb] > 0 && leftAfter[sb] === 0);
    const party = finished ? `Every ${finished} standard for ${gname(g)} is rated!` : strandBefore > 0 && strandLeft(e, g) === 0 ? `${e.s}: every standard rated` : "";
    try {
      await rpc("set_rating", { p_framework: e.f, p_code: e.c, p_grade: g, p_level: level, p_team: S.team.name, p_device: S.device });
      syncNote("Saved " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      if (party) celebrate(party, undo); else toast(`${e.c}, ${gname(g)}: ${LEVEL[level]}`, undo);
    } catch (err) {
      if (before) S.ratings.set(k, before); else S.ratings.delete(k);
      rerender(); toast("Could not save: " + err.message);
    }
  }

  // Take back this device's latest rating (no passcode; the database allows it for 15 minutes).
  async function undoRating(e, g, before) {
    const k = rkey(e.f, e.c, g), now = S.ratings.get(k);
    if (before) S.ratings.set(k, before); else S.ratings.delete(k);
    rerender();
    try {
      await rpc("undo_my_rating", { p_framework: e.f, p_code: e.c, p_grade: g, p_device: S.device });
      toast("Undone"); if (S.view === "activity") { await loadEvents(); rerender(); }
    } catch (err) {
      if (now) S.ratings.set(k, now); rerender(); toast("Could not undo: " + err.message);
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
    const gs = visibleGrades();
    if (!gs.includes(S.f.grade)) S.f.grade = "";
    fillSelect($("#f-grade"), [["", "Choose a grade"], ...gs.map((g) => [g, gname(g)])], S.f.grade);
    const sg = strandGrade(), strandSel = $("#f-strand");
    const strands = sg ? [...new Set(items().filter((e) => (!S.f.framework || e.f === S.f.framework) && forGrade(e, sg)).map((e) => e.s).filter(Boolean))].sort() : [];
    if (S.f.strand && !strands.includes(S.f.strand)) S.f.strand = "";
    fillSelect(strandSel, sg ? [["", "All strands"], ...strands.map((s) => [s, s])] : [["", ""]], S.f.strand);
    strandSel.disabled = !sg;
    strandSel.title = sg ? "" : "Choose a grade first";
    $("#f-division").value = S.f.division;
    $("#filters").dataset.view = S.view;
    $("#filters").dataset.committee = S.team && S.team.name === "Vertical Alignment Committee" ? "1" : "0";
  }

  /* ---------------- views ---------------- */
  // Teachers get one guided flow (view "flow"); the committee, or a teacher who chooses "Explore", gets the full tabs.
  const isCommittee = () => S.team && S.team.name === "Vertical Alignment Committee";
  const mode = () => (!S.team ? "welcome" : isCommittee() || S.explore ? "full" : "teacher");
  function showView(v) {
    S.view = v;
    $$(".tabs [data-view]").forEach((x) => x.setAttribute("aria-selected", x.dataset.view === v));
    $$(".view").forEach((x) => (x.hidden = x.id !== "view-" + v));
    document.body.dataset.mode = mode(); document.body.dataset.view = v;
    renderWho();
  }
  function renderWho() {
    const m = mode();
    $("#whoami").innerHTML = m === "welcome" ? "" : `<span class="who-team">${esc(S.team.name)}</span>
      ${m === "teacher" ? `<button type="button" class="ghost sm" data-act="explore">Explore the K-12 map</button>` : !isCommittee() ? `<button type="button" class="sm" data-act="back-to-flow">Back to rating</button>` : ""}
      <button type="button" class="linkish" data-act="switch-team">Change team</button>`;
  }
  function rerender() {
    const v = S.view;
    if (v === "flow") renderFlow(); else if (v === "rate") renderRate(); else if (v === "heatmap") renderHeatmap(); else if (v === "gaps") renderGaps();
    else if (v === "dashboard") renderDashboard(); else if (v === "ladder") renderLadder(); else if (v === "plans") renderPlans(); else renderActivity();
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
    const k = rkey(e.f, e.c, g);
    return `<div class="std ${r ? "rated l" + r.level : ""} ${S.flash === k ? "flash" : ""}"><div><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}">${esc(e.c)}</button></div>
      <div><div class="txt">${esc(e.t)}${e.t.length >= 220 ? "…" : ""}</div><div class="tags">${tags.join("")}</div></div>
      <div>${segFor(e, g)}</div>${r ? `<div class="who">${esc(r.team)} · ${new Date(r.updated_at).toLocaleDateString()}</div>` : ""}</div>`;
  }
  function groupByStrand(list, g, noteFn) {
    let html = "", last = null;
    for (const e of list) {
      if (e.s !== last) {
        const inS = list.filter((x) => x.s === e.s), c = countLevels(inS, g), done = inS.length - c[3];
        html += `<div class="strand ${c[3] ? "" : "done"}"><span>${esc(e.s || "Standards")}</span>${miniBar(c, `${done} of ${inS.length} rated`)}<span class="strand-n">${c[3] ? `${done}/${inS.length}` : "✓ all rated"}</span></div>`;
        last = e.s;
      }
      html += stdRow(e, g, noteFn && noteFn(e));
    }
    return html;
  }
  // c = [not taught, introduced, in depth, not rated] for a list of standards in grade g
  function countLevels(list, g) { const c = [0, 0, 0, 0]; for (const e of list) { const r = rating(e.f, e.c, g); c[r ? r.level : 3]++; } return c; }
  // Thin stacked bar: in depth, introduced, not taught, then unrated track. 2px gaps between fills.
  function miniBar(c, label) {
    const n = c[0] + c[1] + c[2] + c[3] || 1;
    return `<span class="mini" role="img" aria-label="${esc(label || "")}">${[2, 1, 0].map((i) => (c[i] ? `<i style="flex:${c[i] / n};background:${COLORS[i]}"></i>` : "")).join("")}${c[3] ? `<i class="rest" style="flex:${c[3] / n}"></i>` : ""}</span>`;
  }
  // Ring chart of a grade's progress with % rated in the middle.
  function donut(c, size = 84) {
    const n = c[0] + c[1] + c[2] + c[3] || 1, r = 15.9, C = 2 * Math.PI * r, gap = c[3] === n ? 0 : 0.6;
    let off = 0, arcs = "";
    for (const i of [2, 1, 0]) {
      if (!c[i]) continue;
      const len = (c[i] / n) * C;
      arcs += `<circle r="${r}" cx="20" cy="20" fill="none" stroke="${COLORS[i]}" stroke-width="4.2" stroke-dasharray="${Math.max(len - gap, 0.1)} ${C}" stroke-dashoffset="${-off}" class="arc"><title>${LEVEL[i]}: ${c[i]}</title></circle>`;
      off += len;
    }
    const pct = Math.round(((n - c[3]) / n) * 100);
    return `<svg class="donut" width="${size}" height="${size}" viewBox="0 0 40 40" role="img" aria-label="${pct}% rated">
      <circle r="${r}" cx="20" cy="20" fill="none" stroke="var(--chip)" stroke-width="4.2"></circle><g transform="rotate(-90 20 20)">${arcs}</g>
      <text x="20" y="21.5" text-anchor="middle" class="donut-n">${pct}%</text><text x="20" y="27.5" text-anchor="middle" class="donut-l">rated</text></svg>`;
  }
  function celebrate(msg, action) {
    toast(msg, action);
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const box = document.createElement("div"); box.className = "confetti"; box.setAttribute("aria-hidden", "true");
    const cols = [COLORS[2], COLORS[1], COLORS[0], COLORS.accent, COLORS.maroon];
    for (let i = 0; i < 70; i++) {
      const b = document.createElement("i");
      b.style.cssText = `left:${Math.random() * 100}vw;background:${cols[i % cols.length]};animation-delay:${Math.random() * 0.4}s;animation-duration:${1.4 + Math.random()}s;transform:rotate(${Math.random() * 360}deg)`;
      box.append(b);
    }
    document.body.append(box); setTimeout(() => box.remove(), 3000);
  }
  function progressBar(list, g) {
    const c = [0, 0, 0, 0];
    for (const e of list) { const r = rating(e.f, e.c, g); c[r ? r.level : 3]++; }
    const n = list.length || 1;
    const seg = (i, col) => (c[i] ? `<i style="width:${(c[i] / n) * 100}%;background:${col}"></i>` : "");
    return `<div class="progress"><div class="bar">${seg(2, COLORS[2])}${seg(1, COLORS[1])}${seg(0, COLORS[0])}</div>
      <span>${list.length - c[3]} of ${list.length} rated · ${c[2]} in depth</span></div>`;
  }

  // The default framework for a subject and grade, also the one each "still to rate" count uses so a standard
  // listed in two frameworks is not counted twice. Social Studies is Wisconsin (with EEs) in every grade;
  // Science is AERO in K-5 (the school's current framework) and NGSS in 6-12.
  function countFramework(subject, g) {
    if (subject === "Science") return DIV.Elementary.includes(g) ? "AERO-SCI" : "NGSS";
    if (subject === "Social Studies") return "WI-SS";
    return null;
  }
  const defaultFramework = (subject, g) => (subject === "Science" && (!g || DIV.Elementary.includes(g)) ? "" : countFramework(subject, g) || "");
  // Unrated grade-level standards per subject (counted framework only), and unrated standards left in e's strand.
  function toRateLeft(g) {
    const out = {};
    for (const s of S.meta.subjects) { const fw = countFramework(s.name, g); out[s.name] = S.idx[s.slug].filter((e) => e.pl.includes(g) && (!fw || e.f === fw) && !rating(e.f, e.c, g)).length; }
    return out;
  }
  const strandLeft = (e, g) => items().filter((x) => x.s === e.s && x.f === e.f && x.pl.includes(g) && !rating(x.f, x.c, g)).length;
  // Grade-level standards (suggested for grade g) that no one has marked yet, per subject. The goal is 0 everywhere.
  function toRateStrip(g) {
    const subs = S.team.name === "Vertical Alignment Committee" ? S.meta.subjects.map((s) => s.name) : S.team.subjects;
    const chips = subs.map((name) => {
      const sl = S.meta.subjects.find((s) => s.name === name).slug;
      const fw = countFramework(name, g);
      const list = S.idx[sl].filter((e) => e.pl.includes(g) && (!fw || e.f === fw));
      const left = list.filter((e) => !rating(e.f, e.c, g)).length;
      return `<button type="button" class="torate ${left ? "" : "done"} ${name === S.f.subject ? "on" : ""}" data-act="subject" data-s="${esc(name)}" data-fw="${esc(fw || "")}"
        title="${left} of ${list.length} ${esc(name)} standards for ${esc(gname(g))} not rated yet${fw ? " (" + esc(FW_NAME[fw]) + ")" : ""}"><b>${left}</b> ${esc(name)}${left ? "" : " ✓"}</button>`;
    }).join("");
    return `<div class="torate-row"><span class="muted">Still to rate in ${esc(gname(g))}:</span> ${chips} ${hb("torate")}</div>`;
  }

  /* ---------------- teacher flow: one standard at a time ---------------- */
  // The grade-level list a teacher works through for one subject, in document order (strand by strand).
  function flowList(subject, g) {
    const sl = S.meta.subjects.find((s) => s.name === subject).slug, fw = countFramework(subject, g);
    return S.idx[sl].filter((e) => e.pl.includes(g) && (!fw || e.f === fw));
  }
  // Index rows trim long standards; the card shows the full text from the detail file once it has loaded.
  function fullText(e) {
    const sub = S.meta.subjects.find((s) => S.idx[s.slug].includes(e)), det = sub && S.detail[sub.slug];
    if (!det) { if (sub) loadDetail(sub.slug).then(() => S.view === "flow" && rerender()).catch(() => {}); return e.t + (e.t.length >= 220 ? "…" : ""); }
    return (det[`${e.f}|${e.c}|${e.pl[0]}`] || {}).text || e.t;
  }
  function flowCurrent(list, g) {
    const F = S.flow;
    if (F.back) { const b = list.find((e) => rkey(e.f, e.c, g) === F.back); if (b) return b; F.back = null; }
    const open = list.filter((e) => !rating(e.f, e.c, g));
    return open.find((e) => !F.skipped.has(rkey(e.f, e.c, g))) || open[0] || null;
  }
  function welcome(el) {
    const groups = { "Elementary": [], "Middle school": [], "High school": [] };
    S.teams.forEach((t) => { if (t.name !== "Vertical Alignment Committee") (DIV.Elementary.includes(t.grades[0]) ? groups.Elementary : DIV.Middle.includes(t.grades[0]) ? groups["Middle school"] : groups["High school"]).push(t); });
    el.innerHTML = `<div class="flow-wrap"><div class="hero"><h2>Which team are you?</h2>
      <p class="lede">You will see your grade's standards one at a time. For each one, say how it is really taught this year. It saves as you go, and this device remembers your team.</p></div>
      ${Object.entries(groups).map(([g, ts]) => `<h3 class="pick-h">${g}</h3><div class="pick">${ts.map((t) => `<button type="button" class="pick-b" data-act="team" data-t="${esc(t.name)}">${esc(t.name)}</button>`).join("")}</div>`).join("")}
      <p class="muted committee-link"><button type="button" class="linkish" data-act="team" data-t="Vertical Alignment Committee">I am on the Vertical Alignment Committee</button></p></div>`;
  }
  function renderFlow() {
    const el = $("#view-flow");
    if (!S.team) return welcome(el);
    const g = teamGrade(), F = S.flow;
    if (!F.subject || !S.team.subjects.includes(F.subject)) F.subject = S.team.subjects.find((s) => flowList(s, g).some((e) => !rating(e.f, e.c, g))) || S.team.subjects[0];
    const list = flowList(F.subject, g), done = list.filter((e) => rating(e.f, e.c, g)).length, left = list.length - done;
    const pills = S.team.subjects.length > 1 ? `<div class="subj-pills" role="tablist" aria-label="Subjects">${S.team.subjects.map((s) => {
      const l = flowList(s, g), n = l.filter((e) => !rating(e.f, e.c, g)).length;
      return `<button type="button" role="tab" aria-selected="${s === F.subject}" class="subj ${n ? "" : "done"}" data-act="flow-subject" data-s="${esc(s)}">${esc(s)} <span>${n ? n + " left" : "✓"}</span></button>`;
    }).join("")}</div>` : "";
    const pct = list.length ? (done / list.length) * 100 : 100;
    const head = `<div class="flow-head">${pills}
      <div class="flow-progress"><div class="fp-bar"><i style="width:${pct}%"></i></div>
      <span><b>${done}</b> of ${list.length} rated · <b>${left}</b> left ${hb("flow")}</span></div></div>`;
    const e = flowCurrent(list, g);
    let body;
    if (!e) {
      const next = S.team.subjects.find((s) => flowList(s, g).some((x) => !rating(x.f, x.c, g)));
      body = `<div class="card done-card"><div class="big-tick">✓</div><h2>${esc(F.subject)} is done</h2>
        <p class="lede">All ${list.length} ${esc(F.subject)} standards for ${esc(gname(g))} are rated. Thank you.</p>
        <div class="done-actions">${next ? `<button type="button" data-act="flow-subject" data-s="${esc(next)}">Next: ${esc(next)} →</button>` : `<p><b>Every subject is done.</b> The committee can now see your grade on the map.</p>`}
        <button type="button" class="ghost" data-act="review">Review my answers</button></div></div>`;
    } else {
      const k = rkey(e.f, e.c, g), r = rating(e.f, e.c, g), pos = list.indexOf(e) + 1;
      const ee = e.ee ? e.ee.split(";")[0].trim() : "";
      const fresh = S.flow.lastKey !== k; S.flow.lastKey = k;
      body = `<article class="card std-card ${fresh ? "enter" : ""}" data-k="${esc(k)}">
        <div class="card-top"><span class="eyebrow">${esc(e.s || F.subject)}</span><span class="muted">${pos} of ${list.length}</span></div>
        <h2 class="card-code"><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}" title="Open the full standard">${esc(e.c)}</button></h2>
        <p class="card-text">${esc(fullText(e))}</p>
        <p class="card-meta">${ee ? `Essential Element ${esc(ee)} · ` : ""}<button type="button" class="linkish" data-act="open" data-k="${esc(e.f + "|" + e.c)}">Full standard and "I can" levels</button>${e.sg ? ` · <span class="tag sg">Suggested placement</span>` : ""}</p>
        <p class="card-q">How is this taught in ${esc(gname(g))} this year?</p>
        <div class="choices">${[0, 1, 2].map((l) => `<button type="button" class="choice c${l} ${r && r.level === l ? "on" : ""}" data-act="flow-rate" data-k="${esc(e.f + "|" + e.c)}" data-l="${l}">
          <kbd>${l + 1}</kbd><b>${["Not taught", "Introduced", "Taught in depth"][l]}</b><small>${["We do not teach this", "Touched on, not a main focus", "Taught, practised and assessed"][l]}</small></button>`).join("")}</div>
        <div class="card-foot">
          <button type="button" class="linkish" data-act="flow-back" ${F.history.length ? "" : "disabled"}>← Previous</button>
          <span class="muted keys">Keys: 1, 2, 3 to answer · S to skip ${hb("flow_keys")}</span>
          <button type="button" class="linkish" data-act="flow-skip">Skip for now →</button></div>
      </article>`;
    }
    el.innerHTML = `<div class="flow-wrap">${head}${body}
      <p class="flow-more"><button type="button" class="linkish" data-act="review">See the whole list</button> ${hb("review")}</p></div>`;
  }
  async function flowRate(k, level) {
    const g = teamGrade(), e = findItem(k); if (!e) return;
    const rk = rkey(e.f, e.c, g), cur = rating(e.f, e.c, g);
    S.flow.skipped.delete(rk);
    if (S.flow.back === rk) S.flow.back = null;
    if (!S.flow.history.includes(rk)) S.flow.history.push(rk);
    const card = $(".std-card"); if (card) card.classList.add("leaving");
    if (cur && cur.level === level) { rerender(); return; }
    await setRating(e, g, level);
  }

  function renderRate() {
    const el = $("#view-rate");
    if (!S.team) {
      el.innerHTML = `<div class="panel"><h2>Welcome ${hb("team")}</h2><p class="lede">Choose your team at the top right. You will see the standards for your grade, and you can mark each one as
        <b>Not taught</b>, <b>Introduced / exposed</b> or <b>Taught in depth</b>. Every change is saved straight away and recorded with your team name.</p></div>`;
      return;
    }
    const g = teamGrade();
    if (!g) return pickGrade(el, "its standards");
    const all = filtered({ ignoreDivision: true });
    const placed = all.filter((e) => e.pl.includes(g));
    const band = all.filter((e) => !e.pl.includes(g) && e.sg && e.div.includes(divOf(g)));
    const committee = S.team.name === "Vertical Alignment Committee";
    el.innerHTML = (mode() === "teacher" ? `<div class="flow-wrap wide"><p><button type="button" class="ghost" data-act="back-to-flow">← Back to one at a time</button></p></div>` : "") + `<div class="panel">
      <div class="rate-head"><div><h2>${esc(S.f.subject)} · ${esc(gname(g))} ${hb("rate")}</h2>
      <p class="lede">For each standard, choose how it is taught in ${esc(gname(g))} this year. Use what is really taught, even if the plans do not show it yet.</p></div>
      <div class="ring-box">${(() => { const lst = placed.concat(band.filter((e) => rating(e.f, e.c, g))), c = countLevels(lst, g); return donut(c) +
        `<div class="ring-key"><b>${lst.length - c[3]} of ${lst.length}</b> rated<br><span><i class="lv lv-2"></i>${c[2]} in depth</span><span><i class="lv lv-1"></i>${c[1]} introduced</span><span><i class="lv lv-0"></i>${c[0]} not taught</span></div>`; })()}${hb("progress")}</div></div>
      ${toRateStrip(g)}
      ${committee ? `<p class="muted">Committee view: pick a grade with the Grade filter above.</p>` : ""}
      <div class="group-title"><h3>Standards suggested for ${esc(gname(g))} (${placed.length}) ${hb("rate_placed")}</h3></div>
      ${placed.length ? groupByStrand(placed, g, (e) => (e.sg ? "Suggested placement" : "")) : `<div class="empty">No standards match these filters.</div>`}
      ${band.length ? `<div class="group-title"><h3>Other ${esc(divOf(g).toLowerCase())} school standards (${band.length}) ${hb("rate_band")}</h3>
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
          return `<td data-gi="${g}"><button class="${cls}" data-act="open" data-k="${esc(e.f + "|" + e.c)}" data-g="${g}" data-tip="1"
            aria-label="${esc(e.c)}, ${esc(gname(g))}: ${r ? LEVEL[r.level] : "not rated"}${placed ? ", suggested grade" : ""}"></button></td>`;
        }).join("") + `</tr>`;
    }
    const rated = list.filter((e) => levelsAcross(e).length).length;
    el.innerHTML = `<div class="panel"><h2>${esc(S.f.subject)} coverage, ${S.f.division === "all" ? "K-12" : esc(S.f.division) + " school"} ${hb("heatmap")}</h2>
      <p class="lede">${list.length} standards. ${rated} have at least one rating. Each row is a standard and each column a grade. A dark green outline marks the grade the standard is suggested for; a dot marks a grade that reports teaching it somewhere else.</p></div>
      <div class="hm-wrap" id="hm"><table class="hm" data-sel="${esc(S.f.grade)}"><thead><tr><th class="rowh">Standard <span class="muted" style="font-weight:400">${hb("hm_cols")}</span></th>${gs.map((g) => {
        const mine = list.filter((e) => e.pl.includes(g)), c = countLevels(mine, g), pct = mine.length ? Math.round(((mine.length - c[3]) / mine.length) * 100) : 0;
        return `<th data-gi="${g}" class="${S.f.grade === g ? "sel" : ""}"><button type="button" class="colh" data-act="grade" data-g="${g}" data-tip-text="${esc(gname(g))}: ${mine.length - c[3]} of ${mine.length} suggested standards rated (${c[2]} in depth, ${c[1]} introduced, ${c[0]} not taught). Click to choose this grade.">${gl(g)}<small>${mine.length ? pct + "%" : ""}</small>${mine.length ? miniBar(c) : ""}</button></th>`;
      }).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`;
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
    el.innerHTML = `<div class="panel"><h2>Gaps and repetition: ${esc(S.f.subject)}${S.f.division === "all" ? "" : ", " + esc(S.f.division) + " school"} ${hb("gaps")}</h2>
      <div class="summary"><p>${hb("summary")} ${n} standards in view. ${n - a.unrated.length} (${pct(n - a.unrated.length)}%) have been rated by at least one grade.</p>
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
    if (!g) return pickGrade(el, "its dashboard");
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
      return `<button type="button" class="sb-name" data-act="strand" data-s="${esc(x.s)}" title="Rate this strand">${esc(x.s)}</button><div class="sb" role="img" aria-label="${esc(x.s)}: ${x.c[2]} in depth, ${x.c[1]} introduced, ${x.c[0]} not taught, ${x.c[3]} not rated">
        ${[[2, COLORS[2]], [1, COLORS[1]], [0, COLORS[0]], [3, "#F2F4F6"]].map(([i, col]) => (x.c[i] ? `<i style="width:${w(i)}%;background:${col}" data-tip-text="${esc(x.s)}: ${x.c[i]} ${i === 3 ? "not rated" : LEVEL[i].toLowerCase()}"></i>` : "")).join("")}</div>
        <div class="num">${x.c[2]}/${x.arr.length}</div>`;
    }).join("");
    const strong = ratedStrands[0], weak = ratedStrands[ratedStrands.length - 1];
    el.innerHTML = `<div class="panel"><h2>${esc(gname(g))} · ${esc(S.f.subject)} ${hb("dashboard")}</h2>
      <div class="tiles">
        <div class="tile"><div class="n">${list.length}</div><div class="l">standards suggested for this grade ${hb("t_total")}</div></div>
        <div class="tile ring-tile">${donut(tot, 64)}<div class="l">rated so far ${hb("t_rated")}</div></div>
        <div class="tile t2"><div class="n">${tot[2]}</div><div class="l">taught in depth ${hb("t_depth")}</div></div>
        <div class="tile t1"><div class="n">${tot[1]}</div><div class="l">introduced or exposed ${hb("t_intro")}</div></div>
        <div class="tile t0"><div class="n">${tot[0]}</div><div class="l">not taught ${hb("t_not")}</div></div>
        <div class="tile"><div class="n">${extra.length}</div><div class="l">taught here but suggested for another grade ${hb("t_extra")}</div></div>
      </div>
      <div class="summary">${hb("summary")}${list.length - tot[3] === 0 ? `<p>No ratings yet for ${esc(gname(g))}. Once the team rates its standards, this summary fills in.</p>` :
        `<p>${esc(gname(g))} has rated ${list.length - tot[3]} of ${list.length} ${esc(S.f.subject)} standards. ${tot[2]} are taught in depth and ${tot[1]} are introduced; ${tot[0]} are not taught this year.</p>
        ${strong && weak && strong !== weak ? `<p>Strongest coverage: <b>${esc(strong.s)}</b>. Most room to grow: <b>${esc(weak.s)}</b>.</p>` : ""}
        ${extra.length ? `<p>The team also teaches ${extra.length} standard${extra.length > 1 ? "s" : ""} suggested for other grades (see Gaps &amp; repetition).</p>` : ""}`}</div>
      <h3>Coverage by strand ${hb("strandbars")}</h3><div class="strand-bars" id="dash-bars">${bars || "<div class='muted'>No standards.</div>"}</div></div>`;
  }

  function renderLadder() {
    const el = $("#view-ladder"), gs = visibleGrades();
    const g0 = S.f.grade;
    if (!g0) return pickGrade(el, "a progression");
    const inG = filtered().filter((e) => forGrade(e, g0));
    const strand = S.f.strand || (inG[0] && inG[0].s);
    if (!strand) { el.innerHTML = `<div class="panel empty">No standards match these filters.</div>`; return; }
    const list = filtered().filter((e) => e.s === strand);
    const rungs = gs.map((g) => {
      const here = list.filter((e) => e.pl.includes(g));
      const moved = list.filter((e) => !e.pl.includes(g) && (rating(e.f, e.c, g)?.level || 0) > 0);
      const chip = (e, m) => { const r = rating(e.f, e.c, g); return `<button class="chip ${r ? "l" + r.level : ""}" data-act="open" data-k="${esc(e.f + "|" + e.c)}" style="${m ? "border-style:dashed" : ""}">${esc(e.c)}<small>${esc(e.t.slice(0, 60))}${e.t.length > 60 ? "…" : ""}</small></button>`; };
      const c = countLevels(here, g);
      return `<div class="rung div-${divOf(g)} ${g === g0 ? "sel" : ""}"><h4>${esc(gname(g))} <span class="muted">(${here.length})</span></h4>${here.length ? miniBar(c, `${here.length - c[3]} of ${here.length} rated`) : ""}${here.map((e) => chip(e)).join("")}${moved.length ? `<div class="muted" style="font-size:11px;margin:6px 0 4px">Also taught here</div>${moved.map((e) => chip(e, true)).join("")}` : ""}</div>`;
    }).join("");
    el.innerHTML = `<div class="panel"><h2>Progression: ${esc(strand || "")} ${hb("ladder")}</h2>
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
    el.innerHTML = `<div class="panel"><h2>Recent changes ${hb("activity")}</h2><p class="lede">Every rating change, newest first. Undo needs the committee passcode.</p>
      <table class="log"><thead><tr><th>When</th><th>Team</th><th>Standard</th><th>Grade</th><th>Change</th><th></th></tr></thead><tbody>${rows || "<tr><td colspan='6' class='muted'>No changes yet.</td></tr>"}</tbody></table></div>
      <div class="panel"><h2>Recent comments</h2><table class="log"><thead><tr><th>When</th><th>Team</th><th>Standard</th><th colspan="2">Comment</th><th></th></tr></thead><tbody>${crow || "<tr><td colspan='6' class='muted'>No comments yet.</td></tr>"}</tbody></table></div>`;
  }

  /* ---------------- Part 2: plans vs ratings ---------------- */
  // data/evidence.json is written by scripts/part2/match_plans.py (not run yet). Until it exists the page shows
  // its layout with empty states, so the committee can see what Part 2 will report.
  const ev = (f, c, g) => S.evidence && S.evidence.items[`${f}|${c}|${g}`];
  function evidenceFor(e) {
    if (!S.evidence) return `<p class="muted">Part 2 has not run yet. When it does, this shows which 2025-26 and 2026-27 plans include this standard, in which weeks, and whether the code was cited or inferred.</p>`;
    const rows = GRADES.map((g) => ({ g, x: ev(e.f, e.c, g) })).filter((r) => r.x);
    if (!rows.length) return `<p class="muted">Not found in any plan read so far.</p>`;
    return `<ul class="comments">${rows.map(({ g, x }) => `<li><b>${esc(gname(g))}</b>: ${x.weeks} week${x.weeks === 1 ? "" : "s"} (${LEVEL[x.level].toLowerCase()}, ${x.match})
      <div class="meta">${x.refs.map(([si, wk]) => { const s = S.evidence.sources[si]; return `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> ${esc(s.year)}: ${esc(wk.join(", "))}`; }).join("<br>")}</div></li>`).join("")}</ul>`;
  }
  function renderPlans() {
    const el = $("#view-plans"), g = S.f.grade, ready = !!S.evidence;
    if (!g) return pickGrade(el, "its plans");
    const list = filtered({ ignoreDivision: true });
    const pill = (l, lab) => `<span class="pill"><i class="lv ${l == null ? "lv-none" : "lv-" + l}"></i>${lab}</span>`;
    let svsRows = "", off = [];
    if (ready) {
      for (const e of list) {
        const r = rating(e.f, e.c, g), x = ev(e.f, e.c, g);
        if (!r && !x) continue;
        const said = r ? r.level : null, shown = x ? x.level : 0;
        if (said === shown) continue;
        const note = said == null ? "Plans show it; the team has not rated it yet." : said > 0 && !x ? "Not yet recorded in plans." :
          said === 0 && x ? "Plans include it, but the team marked it not taught. Worth a quick check." :
          said > shown ? "Taught more than the plans show." : "Plans show more time than the rating suggests.";
        svsRows += `<tr><td><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}">${esc(e.c)}</button></td>
          <td>${said == null ? pill(null, "Not rated") : pill(said, LEVEL_SHORT[said])}</td><td>${x ? pill(x.level, LEVEL_SHORT[x.level] + " · " + x.weeks + " wk") : pill(null, "Not in plans")}</td><td>${note}</td></tr>`;
      }
      off = Object.entries(S.evidence.items).filter(([k]) => k.endsWith("|" + g)).map(([k, x]) => { const [f, c] = k.split("|"); return { e: findItem(f + "|" + c), x }; })
        .filter((o) => o.e && !o.e.pl.includes(g) && o.e.f && (!S.f.framework || o.e.f === S.f.framework) && list.includes(o.e));
    }
    const empty = (cols, msg) => `<tr class="placeholder"><td colspan="${cols}">${msg}</td></tr>`;
    el.innerHTML = `<div class="panel"><h2>Plans vs ratings: ${esc(gname(g))} · ${esc(S.f.subject)} ${hb("plans")}</h2>
      <p class="lede">What the curriculum plans show, side by side with what teams said in Part 1.</p>
      ${ready ? `<p class="muted">Plans last read ${esc(S.evidence.built)} · ${S.evidence.sources.length} plan files.</p>` :
      `<div class="notice"><b>Part 2 has not run yet.</b> This page shows what it will report. When the plans are read, every section below fills in, and each standard's popup shows the plans and weeks where it appears.</div>`}
      <h3>How Part 2 works</h3>
      <ol class="steps">
        <li><b>Read the plans ${hb("p_sources")}</b>2026-27 unit and weekly plans for every grade, with 2025-26 filling weeks not planned yet.</li>
        <li><b>Find the standards ${hb("p_match")}</b>Codes named in a plan are <i>cited</i>; content without a code is matched by AI and labelled <i>inferred</i>.</li>
        <li><b>Count the weeks ${hb("p_rule")}</b>1-2 weeks = Introduced; 3 or more = Taught in depth.</li>
        <li><b>Compare with Part 1 ${hb("p_svs")}</b>Where plans and ratings differ, the page says so gently, because plans do not always record everything taught.</li>
      </ol></div>
    <div class="panel"><h2>Says vs shows ${hb("p_svs")}</h2><p class="lede">Standards where the team's rating and the plans differ for ${esc(gname(g))}.</p>
      <table class="svs"><thead><tr><th>Standard</th><th>Team says (Part 1)</th><th>Plans show (Part 2)</th><th>Note</th></tr></thead>
      <tbody>${ready ? svsRows || empty(4, "No differences in this view.") : empty(4, "Fills in when Part 2 runs.")}</tbody></table></div>
    <div class="panel"><h2>Below and above grade in the plans ${hb("p_offgrade")}</h2><p class="lede">Standards from other grades that appear in ${esc(gname(g))}'s plans.</p>
      <table class="svs"><thead><tr><th>Standard</th><th>Suggested grade</th><th>Weeks in ${esc(gname(g))} plans</th><th>Below or above</th></tr></thead>
      <tbody>${ready ? off.map(({ e, x }) => `<tr><td><button class="code" data-act="open" data-k="${esc(e.f + "|" + e.c)}">${esc(e.c)}</button></td><td>${e.pl.map(gl).join(", ")}</td><td>${x.weeks} (${x.match})</td>
        <td>${GRADES.indexOf(e.pl[0]) < GRADES.indexOf(g) ? "Below grade (review or remediation)" : "Above grade (extension)"}</td></tr>`).join("") || empty(4, "None found.") : empty(4, "Fills in when Part 2 runs.")}</tbody></table></div>
    <div class="panel"><h2>Plan sources ${hb("p_sources")}</h2>
      <table class="svs"><thead><tr><th>Plan</th><th>Year</th><th>Grade</th><th>Type</th><th>Notes</th></tr></thead>
      <tbody>${ready ? S.evidence.sources.filter((s) => s.grade === g).map((s) => `<tr><td><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></td><td>${esc(s.year)}</td><td>${esc(gname(s.grade))}</td><td>${esc(s.kind)}</td><td>${s.carried_forward ? "Copied forward from last year" : ""}</td></tr>`).join("") || empty(5, "No plans read for this grade yet.") :
        empty(5, "Elementary weekly and unit plans, Middle and High school unit and lesson plans (2026-27, with 2025-26 for weeks not yet planned).")}</tbody></table></div>`;
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
      <div class="box"><h3>How each grade teaches it ${hb("d_strip")}</h3><div class="strip">${strip}</div>
        <p class="muted" style="margin:8px 0 0">${S.team ? "Click your grade's square to change its rating." : "Choose your team to rate."}</p></div>
      ${d.descriptor_flag ? `<div class="flagbox">${hb("d_flag")} <b>Committee review:</b> ${esc(d.descriptor_flag)}. A suggested version is shown beside the school descriptor.</div>` : ""}
      <div class="grid2" style="margin-top:14px">
        <div class="box"><h3>"I can" levels ${hb("d_levels")} ${d.descriptor_source === "draft" ? '<span class="tag flag">draft</span>' : '<span class="tag">school</span>'}</h3>${lvl(desc)}</div>
        <div class="box"><h3>Essential Element ${esc(e.ee || "")} ${hb("d_ee")}</h3><p>${esc(d.ee_text || "No Essential Element for this standard.")}</p>
          ${desc.ee_at_target && !String(desc.ee_at_target).startsWith("Not applicable") ? `<dl class="levels"><dt>EE at target</dt><dd>${esc(desc.ee_at_target)}</dd></dl>` : ""}</div>
      </div>
      ${d.descriptors_suggested ? `<div class="box" style="margin-top:14px"><h3>Suggested "I can" levels <span class="tag flag">draft</span></h3>${lvl(d.descriptors_suggested)}</div>` : ""}
      <div class="grid2 related" style="margin-top:14px">
        <div class="box"><h3>Same strand, grade before ${hb("d_related")}</h3><ul class="gap-list" style="columns:1">${relList(GRADES[pg - 1])}</ul></div>
        <div class="box"><h3>Same strand, grade after</h3><ul class="gap-list" style="columns:1">${relList(GRADES[pg + 1])}</ul></div>
      </div>
      ${(d.crosswalk || []).length ? `<p class="muted" style="margin-top:12px">Related codes in other frameworks: ${d.crosswalk.map(esc).join(", ")}</p>` : ""}
      <div class="grid2" style="margin-top:14px">
        <div class="box"><h3>Comments ${hb("d_comments")}</h3><ul class="comments">${comments.map((c) => `<li>${esc(c.body)}<div class="meta">${esc(c.team)}${c.author ? " · " + esc(c.author) : ""} · ${new Date(c.created_at).toLocaleDateString()}</div></li>`).join("") || "<li class='muted'>No comments yet.</li>"}</ul>
          <label class="muted" for="c-body" style="display:block;margin-top:8px">Add a comment${S.team ? "" : " (choose your team first)"}</label>
          <textarea id="c-body" maxlength="2000" ${S.team ? "" : "disabled"}></textarea>
          <input id="c-author" placeholder="Your name (optional)" style="margin-top:6px;width:100%" ${S.team ? "" : "disabled"}>
          <div class="row-end"><button data-act="comment" data-k="${esc(k)}" ${S.team ? "" : "disabled"}>Post comment</button></div></div>
        <div class="box"><h3>History ${hb("d_history")}</h3><ul class="comments">${hist.map((ev) => `<li>${gl(ev.grade)}: ${ev.old_level == null ? "Not rated" : LEVEL_SHORT[ev.old_level]} → ${LEVEL_SHORT[ev.new_level]}<div class="meta">${esc(ev.team)} · ${new Date(ev.created_at).toLocaleString()}${ev.undone ? " · undone" : ""}</div></li>`).join("") || "<li class='muted'>No changes yet.</li>"}</ul>
          <h3 style="margin-top:12px">Curriculum evidence ${hb("d_evidence")}</h3>${evidenceFor(e)}</div>
      </div>
      <p class="muted" style="margin-top:12px;font-size:12px">Source: ${esc(d.source || "")}</p>`;
    $("#detail").dataset.k = k;
    if (!$("#detail").open) $("#detail").showModal();
  }

  /* ---------------- exports ---------------- */
  function download(name, blob) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }
  function csvCell(v) { v = String(v ?? ""); return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; }
  function exportCSV() {
    if ((S.view === "rate" && !teamGrade()) || (S.view === "dashboard" && !S.f.grade)) { toast("Choose a grade first."); return; }
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
        x.fillStyle = rt ? COLORS[rt.level] : COLORS.none; x.strokeStyle = e.pl.includes(g) ? COLORS.placed : COLORS.line; x.lineWidth = e.pl.includes(g) ? 2 : 1;
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
    else if (act === "team") { setTeam(b.dataset.t); store.set("va_team", b.dataset.t); $("#team").value = b.dataset.t; }
    else if (act === "switch-team") { S.explore = false; setTeam(""); store.set("va_team", ""); $("#team").value = ""; }
    else if (act === "explore") { S.explore = true; showView("heatmap"); refreshFilterOptions(); rerender(); }
    else if (act === "back-to-flow") { S.explore = false; showView("flow"); rerender(); }
    else if (act === "review") { S.f.subject = S.flow.subject || S.f.subject; S.f.framework = defaultFramework(S.f.subject, teamGrade()); S.f.strand = ""; showView("rate"); refreshFilterOptions(); rerender(); }
    else if (act === "flow-subject") { S.flow.subject = b.dataset.s; S.flow.back = null; S.flow.skipped.clear(); showView("flow"); rerender(); }
    else if (act === "flow-rate") flowRate(b.dataset.k, +b.dataset.l);
    else if (act === "flow-skip") flowSkip();
    else if (act === "flow-back") flowBack();
    else if (act === "grade") { S.f.grade = b.dataset.g; refreshFilterOptions(); rerender(); }
    else if (act === "strand") { S.f.strand = b.dataset.s; $(`.tabs [data-view="rate"]`).click(); }
    else if (act === "subject") { S.f.subject = b.dataset.s; S.f.framework = b.dataset.fw || ""; S.f.strand = ""; refreshFilterOptions(); rerender(); }
    else if (act === "cycle") {
      const e = findItem(b.dataset.k), g = b.dataset.g, cur = rating(e.f, e.c, g);
      if (!canEdit(g)) { toast(S.team ? `Your team rates ${S.team.grades.map(gname).join(", ")}.` : "Choose your team first."); return; }
      await setRating(e, g, cur ? (cur.level + 1) % 3 : 1); openDetail(b.dataset.k);
    } else if (act === "comment") {
      const body = $("#c-body").value.trim(); if (!body) return;
      if (!teamGrade()) { toast("Choose a grade first."); return; }
      const e = findItem(b.dataset.k);
      try { await rpc("add_comment", { p_framework: e.f, p_code: e.c, p_grade: teamGrade(), p_team: S.team.name, p_author: $("#c-author").value.trim(), p_body: body });
        await loadComments(); openDetail(b.dataset.k); toast("Comment posted"); } catch (err) { toast("Could not post: " + err.message); }
    } else if (act === "undo") askAdmin(async (p) => { await rpc("admin_undo", { p_event_id: +b.dataset.id, p_passcode: p }); await Promise.all([loadRatings(true), loadEvents()]); rerender(); toast("Change undone"); });
    else if (act === "hide") askAdmin(async (p) => { await rpc("admin_hide_comment", { p_comment_id: +b.dataset.id, p_passcode: p }); await loadComments(); rerender(); toast("Comment hidden"); });
  });
  $("#a-go").addEventListener("click", async () => { try { await adminAction($("#a-pass").value); $("#admin").close(); } catch (err) { toast(err.message === "not allowed" ? "Wrong passcode" : err.message); } });
  $$("dialog [data-close], #d-close").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
  $("#detail").addEventListener("close", () => rerender());

  // "?" explanations
  const pop = $("#pop");
  let popFor = null;
  function closePop() { pop.hidden = true; if (popFor) popFor.setAttribute("aria-expanded", "false"); popFor = null; }
  document.addEventListener("click", (ev) => {
    const h = ev.target.closest(".help");
    if (h) {
      ev.preventDefault(); ev.stopPropagation();
      if (popFor === h) { closePop(); return; }
      closePop();
      const [t, b] = (window.VA_HELP || {})[h.dataset.help] || ["Help", "No explanation yet."];
      $("#pop-t").textContent = t; $("#pop-b").innerHTML = /<(ul|p)/.test(b) ? b : `<p>${b}</p>`;
      const host = h.closest("dialog"); (host || document.body).appendChild(pop);
      pop.hidden = false; popFor = h; h.setAttribute("aria-expanded", "true");
      const r = h.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
      pop.style.left = Math.max(8, Math.min(r.left - 12, innerWidth - pw - 8)) + "px";
      pop.style.top = (r.bottom + ph + 8 < innerHeight ? r.bottom + 6 : Math.max(8, r.top - ph - 6)) + "px";
      return;
    }
    if (!ev.target.closest("#pop")) closePop();
  }, true);
  $("#pop-x").addEventListener("click", closePop);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !pop.hidden) { closePop(); } });

  // heatmap crosshair: light up the row and grade column under the pointer
  let hmCol = null;
  document.addEventListener("mouseover", (ev) => {
    const td = ev.target.closest("table.hm td[data-gi], table.hm th[data-gi]");
    const col = td ? td.dataset.gi : null;
    if (col === hmCol) return;
    $$("table.hm .xcol").forEach((x) => x.classList.remove("xcol"));
    hmCol = col; if (col) $$(`table.hm [data-gi="${col}"]`).forEach((x) => x.classList.add("xcol"));
  });
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
    showView(b.dataset.view);
    store.set("va_view", S.view); refreshFilterOptions(); rerender();
    if (S.view === "activity") Promise.all([loadEvents(), loadComments()]).then(rerender);
  }));
  const bindF = (id, key) => $(id).addEventListener(id === "#f-search" ? "input" : "change", (ev) => {
    S.f[key] = ev.target.value;
    if (key === "subject") S.f.framework = defaultFramework(S.f.subject, teamGrade());
    refreshFilterOptions(); rerender();
  });
  bindF("#f-subject", "subject"); bindF("#f-framework", "framework"); bindF("#f-division", "division"); bindF("#f-grade", "grade"); bindF("#f-strand", "strand"); bindF("#f-search", "search");
  $("#team").addEventListener("change", (ev) => { setTeam(ev.target.value); store.set("va_team", ev.target.value); });
  $("#x-csv").addEventListener("click", exportCSV); $("#x-png").addEventListener("click", exportPNG); $("#x-pdf").addEventListener("click", () => window.print());

  function setTeam(name) {
    S.team = S.teams.find((t) => t.name === name) || null;
    S.flow = { subject: null, skipped: new Set(), back: null, history: [] };
    $("#toast").hidden = true;
    if (S.team && !isCommittee()) {
      S.f.subject = S.team.subjects[0]; S.f.grade = S.team.grades[0]; S.f.division = "all"; S.f.strand = "";
      S.f.framework = defaultFramework(S.f.subject, S.f.grade);
    }
    showView(!S.team || !isCommittee() ? "flow" : S.view === "flow" ? "rate" : S.view);
    refreshFilterOptions(); rerender();
  }
  function flowSkip() {
    const g = teamGrade(), list = flowList(S.flow.subject, g), e = flowCurrent(list, g); if (!e) return;
    const k = rkey(e.f, e.c, g);
    if (S.flow.back === k) S.flow.back = null; else S.flow.skipped.add(k);
    const open = list.filter((x) => !rating(x.f, x.c, g));
    if (open.length && open.every((x) => S.flow.skipped.has(rkey(x.f, x.c, g)))) { S.flow.skipped.clear(); toast("Back to the ones you skipped."); }
    rerender();
  }
  function flowBack() {
    const h = S.flow.history; if (!h.length) return;
    const cur = S.flow.back, i = cur ? h.indexOf(cur) - 1 : h.length - 1;
    if (i < 0) return; S.flow.back = h[i]; rerender();
  }
  document.addEventListener("keydown", (ev) => {
    if (S.view !== "flow" || mode() !== "teacher" || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.target.closest("input, textarea, select, dialog") || $("#detail").open) return;
    const card = $(".std-card"); if (!card) return;
    const k = card.dataset.k.split("|").slice(0, 2).join("|");
    if (["1", "2", "3"].includes(ev.key)) { ev.preventDefault(); flowRate(k, +ev.key - 1); }
    else if (ev.key === "s" || ev.key === "S") { ev.preventDefault(); flowSkip(); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); flowBack(); }
  });

  /* ---------------- start ---------------- */
  async function start() {
    S.device = store.get("va_device") || Math.random().toString(36).slice(2, 12); store.set("va_device", S.device);
    S.meta = await (await fetch("data/meta.json")).json();
    S.teams = S.meta.teams;
    await Promise.all(S.meta.subjects.map(async (s) => (S.idx[s.slug] = await (await fetch(`data/index_${s.slug}.json`)).json())));
    try { const r = await fetch("data/evidence.json"); S.evidence = r.ok ? await r.json() : null; } catch (e) { S.evidence = null; }
    const groups = { "Committee": [], "Elementary": [], "Middle school": [], "High school": [] };
    S.teams.forEach((t) => (t.name === "Vertical Alignment Committee" ? groups.Committee : DIV.Elementary.includes(t.grades[0]) ? groups.Elementary : DIV.Middle.includes(t.grades[0]) ? groups["Middle school"] : groups["High school"]).push(t));
    $("#team").innerHTML = `<option value="">Choose your team</option>` + Object.entries(groups).map(([g, ts]) => `<optgroup label="${g}">${ts.map((t) => `<option>${esc(t.name)}</option>`).join("")}</optgroup>`).join("");
    const saved = store.get("va_team"); if (saved && S.teams.some((t) => t.name === saved)) { $("#team").value = saved; setTeam(saved); }
    const v = store.get("va_view");
    if (mode() === "full" && v && v !== "flow" && $(`.tabs [data-view="${v}"]`)) $(`.tabs [data-view="${v}"]`).click();
    else { showView(mode() === "full" ? "rate" : "flow"); refreshFilterOptions(); rerender(); }
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
