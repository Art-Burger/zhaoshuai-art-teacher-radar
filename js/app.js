const BUILD_DATE = "2026-09-09",
  TODAY = new Date().toISOString().slice(0, 10),
  $ = (s) => document.querySelector(s),
  fmt = (v) => v ?? "未注明";
const DEFAULTS = {
  cityPriority: { 哈尔滨: 6, 北京: 5, 沈阳: 4, 大连: 4, 长春: 4, 东北其他: 2 },
  minSalary: 0,
  acceptUnknownSalary: true,
  schoolTypes: {
    public: true,
    private: true,
    international: true,
    bilingual: true,
    artHigh: true,
    artExam: true,
    training: true,
    other: true,
  },
  stages: { 小学: true, 初中: true, 高中: true, 少儿美术: true },
  jobTypes: {
    k12: true,
    漫画: true,
    插画: true,
    数字绘画: true,
    素描: true,
    色彩: true,
    速写: true,
    艺考: true,
    国际: true,
  },
  acceptEnglish: false,
  acceptInternational: true,
  acceptIB: false,
  acceptALevel: false,
  acceptIGCSE: false,
  showOpenOnly: false,
  showVerify: true,
  showHistory: true,
  topPriority: "city",
  dealbreakers: "",
};
const PRESETS = {
  steady: {
    cityPriority: {
      哈尔滨: 6,
      北京: 4,
      沈阳: 3,
      大连: 3,
      长春: 3,
      东北其他: 1,
    },
    topPriority: "stability",
    schoolTypes: { ...DEFAULTS.schoolTypes, training: false },
  },
  salary: {
    cityPriority: {
      哈尔滨: 5,
      北京: 6,
      沈阳: 3,
      大连: 3,
      长春: 3,
      东北其他: 1,
    },
    topPriority: "salary",
    schoolTypes: {
      ...DEFAULTS.schoolTypes,
      international: true,
      bilingual: true,
    },
  },
  growth: {
    ...DEFAULTS,
    topPriority: "growth",
    schoolTypes: { ...DEFAULTS.schoolTypes, training: false },
  },
  creative: {
    ...DEFAULTS,
    topPriority: "platform",
    jobTypes: {
      ...DEFAULTS.jobTypes,
      漫画: true,
      插画: true,
      数字绘画: true,
      艺考: true,
    },
  },
};
let jobs = [],
  schools = [],
  coverage = [],
  radarCoverage = [],
  searchLogs = [],
  systemStatus = {},
  filtered = [],
  quickFilter = "",
  preferences = RadarStore.getPreferences(DEFAULTS);
const labels = {
  open: "🟢 当前可投",
  verify: "🟡 待核实",
  lead: "🔎 新发现招聘线索",
  expired: "⚫ 历史 / 已过期",
  dead: "⚫ 页面失效",
};
const days = (d) =>
  d ? Math.ceil((new Date(d + "T23:59:59") - new Date()) / 86400000) : 9999;
function normalizedPrefs(raw) {
  return {
    ...DEFAULTS,
    ...raw,
    cityPriority: { ...DEFAULTS.cityPriority, ...raw.cityPriority },
    schoolTypes: { ...DEFAULTS.schoolTypes, ...raw.schoolTypes },
    stages: { ...DEFAULTS.stages, ...raw.stages },
    jobTypes: { ...DEFAULTS.jobTypes, ...raw.jobTypes },
  };
}
function scored(j) {
  const score = RadarRecommendation.score(j, preferences),
    [level, label] = RadarRecommendation.level(score);
  return {
    ...j,
    preference_score: score,
    display_level: level,
    display_label: label,
  };
}
function state(id) {
  return RadarStore.getJobState(id);
}
function save(id, patch) {
  RadarStore.saveJobState(id, patch);
}
function card(raw, compact = false) {
  const j = scored(raw),
    s = state(j.id),
    hard = j.hard_blockers?.length;
  const appStatus = ["准备投递", "已投递", "已联系", "面试", "等待结果", "Offer", "拒绝", "主动放弃"].includes(s.application_status) ? s.application_status : "准备投递";
  return `<article class="card"><div class="badges"><span class="badge ${j.display_level.toLowerCase()}">${j.display_label} · ${j.preference_score}</span><span class="badge">履历匹配 ${j.match_score}%</span><span class="badge">信息可信度：${j.information_confidence || "低"}</span><span class="badge">${labels[j.job_status]}</span><span class="badge">${j.source_badge || { A: "🛡️ 官方", B: "✓ 招聘平台", C: "⚠️ 第三方线索" }[j.source_level]}</span></div><h3>${j.school_name}</h3><b>${j.job_title}</b><div class="meta">📍 ${j.city} · ${fmt(j.district)}　🏫 ${j.school_type}　🎓 ${j.education_stage}</div><div>💰 ${fmt(j.salary_raw_text)}　📅 ${fmt(j.published_date)}　⏳ ${fmt(j.deadline)}</div><div class="why">${j.recommendation_reason}</div>${hard ? `<div class="risk">🔴 硬性资格风险：${j.hard_blockers.join("；")}</div>` : ""}${j.risk_flags?.length ? `<div class="muted">⚠️ ${j.risk_flags.join("；")}</div>` : ""}${compact ? "" : `<div>${j.match_reasons.map((x) => "✓ " + x).join("　")}</div><div class="job-controls"><button data-fav="${j.id}">${s.favorite ? "❤️ 已收藏" : "♡ 收藏"}</button><details class="status-menu"><summary>📝 ${appStatus}</summary><div>${["准备投递", "已投递", "已联系", "面试", "等待结果", "Offer", "拒绝", "主动放弃"].map((x) => `<button data-app-state="${j.id}" data-value="${x}">${x}</button>`).join("")}</div></details></div><input type="date" data-date="${j.id}" value="${s.activity_date || ""}" aria-label="投递或联系日期"><textarea data-notes="${j.id}" placeholder="本地备注">${s.user_notes || ""}</textarea>`}<div class="actions"><a class="primary" target="_blank" rel="noopener" href="${j.source_url}">查看原招聘</a>${j.official_url ? `<a target="_blank" rel="noopener" href="${j.official_url}">查看官方公告</a>` : ""}${compact ? `<button data-fav="${j.id}">${s.favorite ? "❤️ 已收藏" : "♡ 收藏"}</button>` : ""}</div></article>`;
}
function bindCards() {
  document.querySelectorAll("[data-fav]").forEach(
    (b) =>
      (b.onclick = () => {
        save(b.dataset.fav, { favorite: !state(b.dataset.fav).favorite });
        render();
      }),
  );
  document.querySelectorAll("[data-app-state]").forEach((b) => (b.onclick = () => {
    save(b.dataset.appState, { application_status: b.dataset.value });
    render();
  }));
  document
    .querySelectorAll("[data-date]")
    .forEach(
      (e) =>
        (e.onchange = () => save(e.dataset.date, { activity_date: e.value })),
    );
  document
    .querySelectorAll("[data-notes]")
    .forEach(
      (e) =>
        (e.onchange = () => save(e.dataset.notes, { user_notes: e.value })),
    );
}
function allowedByDisplay(j) {
  if (preferences.showOpenOnly && j.job_status !== "open") return false;
  if (!preferences.showVerify && j.job_status === "verify") return false;
  if (!preferences.showHistory && ["expired", "dead"].includes(j.job_status))
    return false;
  return true;
}
function render() {
  const f = {
    city: $("#city").value,
    stage: $("#stage").value,
    type: $("#type").value,
    status: $("#status").value,
    source: $("#source").value,
  };
  filtered = jobs
    .filter(allowedByDisplay)
    .filter((j) =>
      Object.entries(f).every(
        ([k, v]) =>
          !v ||
          j[
            k === "type"
              ? "school_type"
              : k === "source"
                ? "source_level"
                : k === "stage"
                  ? "education_stage"
                  : k
          ] === v,
      ),
    )
    .filter(
      (j) =>
        !$("#blocker").value ||
        ($("#blocker").value === "yes") === !!j.hard_blockers.length,
    );
  if (quickFilter === "recent") filtered = filtered.filter((j) => days(j.first_seen_date) >= -2 && days(j.first_seen_date) <= 1);
  if (quickFilter === "urgent") filtered = filtered.filter((j) => j.job_status === "open" && days(j.deadline) >= 0 && days(j.deadline) <= 7);
  const key = $("#sort").value;
  filtered.sort((a, b) =>
    key === "recommendation_score"
      ? scored(b).preference_score - scored(a).preference_score
      : key === "deadline"
        ? (a.deadline || "9999").localeCompare(b.deadline || "9999")
        : key.includes("date")
          ? (b[key] || "").localeCompare(a[key] || "")
          : (b[key] || 0) - (a[key] || 0),
  );
  $("#result-count").textContent = `${filtered.length} 个岗位`;
  $("#jobs").innerHTML =
    filtered.map((j) => card(j)).join("") ||
    '<p class="empty">当前筛选或偏好下没有岗位。</p>';
  renderHighlights();
  bindCards();
}
function renderHighlights() {
  const open = jobs.filter((j) => j.job_status === "open"),
    top = open
      .filter((j) => !j.hard_blockers.length)
      .sort((a, b) => scored(b).preference_score - scored(a).preference_score)
    .filter((j) => (j.information_confidence || "低") !== "低")
    .slice(0, 5);
  $("#top").innerHTML =
    top.map((j) => card(j)).join("") ||
    '<p class="empty">目前没有达到“当前可投”证据门槛的优先岗位。</p>';
}

function zhTime(value) {
  if (!value) return "尚未更新";
  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
}
function checkbox(path, key, label) {
  const checked = preferences[path][key] ? "checked" : "";
  return `<label><input type="checkbox" data-pref-map="${path}" value="${key}" ${checked}> ${label}</label>`;
}
function renderPreferences() {
  const cityRows = Object.entries(preferences.cityPriority)
    .map(
      ([c, v]) =>
        `<label class="city-rank"><span>${c}</span><select data-city-rank="${c}">${[1, 2, 3, 4, 5, 6].map((n) => `<option value="${n}" ${v === n ? "selected" : ""}>${n}</option>`).join("")}</select></label>`,
    )
    .join("");
  $("#preference-form").innerHTML =
    `<div class="pref-group"><b>城市优先级（6 最高）</b>${cityRows}</div><div class="pref-group"><b>薪资</b><label>最低月薪<input id="pref-min-salary" type="number" min="0" step="500" value="${preferences.minSalary}"></label><label><input id="pref-unknown-salary" type="checkbox" ${preferences.acceptUnknownSalary ? "checked" : ""}> 接受薪资未注明</label><b>学校类型</b>${Object.entries(
      {
        public: "公办",
        private: "民办/私立",
        international: "国际学校",
        bilingual: "双语学校",
        artHigh: "艺术高中",
        artExam: "艺考机构",
        training: "培训机构",
      },
    )
      .map(([k, v]) => checkbox("schoolTypes", k, v))
      .join(
        "",
      )}</div><div class="pref-group"><b>学段</b>${["小学", "初中", "高中", "少儿美术"].map((k) => checkbox("stages", k, k)).join("")}<b>岗位方向</b>${Object.keys(
      preferences.jobTypes,
    )
      .map((k) => checkbox("jobTypes", k, k))
      .join(
        "",
      )}</div><div class="pref-group"><b>国际方向</b><label><input id="pref-english" type="checkbox" ${preferences.acceptEnglish ? "checked" : ""}> 接受全英文授课</label><label><input id="pref-international" type="checkbox" ${preferences.acceptInternational ? "checked" : ""}> 接受国际学校</label><label><input id="pref-ib" type="checkbox" ${preferences.acceptIB ? "checked" : ""}> 接受需要 IB</label><label><input id="pref-alevel" type="checkbox" ${preferences.acceptALevel ? "checked" : ""}> 接受 A-Level</label><label><input id="pref-igcse" type="checkbox" ${preferences.acceptIGCSE ? "checked" : ""}> 接受 IGCSE</label><b>展示</b><label><input id="pref-open" type="checkbox" ${preferences.showOpenOnly ? "checked" : ""}> 只看当前可投</label><label><input id="pref-verify" type="checkbox" ${preferences.showVerify ? "checked" : ""}> 显示待核实</label><label><input id="pref-history" type="checkbox" ${preferences.showHistory ? "checked" : ""}> 显示历史岗位</label></div><div class="pref-group"><b>最看重</b><select id="pref-top">${Object.entries(
      {
        salary: "薪资",
        stability: "稳定性",
        city: "城市",
        platform: "学校平台",
        workload: "工作强度",
        growth: "职业发展",
      },
    )
      .map(
        ([k, v]) =>
          `<option value="${k}" ${preferences.topPriority === k ? "selected" : ""}>${v}</option>`,
      )
      .join(
        "",
      )}</select><label>绝对不能接受的条件<textarea id="pref-dealbreakers">${preferences.dealbreakers || ""}</textarea></label></div>`;
}
function collectPreferences() {
  const p = structuredClone(preferences);
  document
    .querySelectorAll("[data-city-rank]")
    .forEach((e) => (p.cityPriority[e.dataset.cityRank] = +e.value));
  document
    .querySelectorAll("[data-pref-map]")
    .forEach((e) => (p[e.dataset.prefMap][e.value] = e.checked));
  Object.assign(p, {
    minSalary: +$("#pref-min-salary").value,
    acceptUnknownSalary: $("#pref-unknown-salary").checked,
    acceptEnglish: $("#pref-english").checked,
    acceptInternational: $("#pref-international").checked,
    acceptIB: $("#pref-ib").checked,
    acceptALevel: $("#pref-alevel").checked,
    acceptIGCSE: $("#pref-igcse").checked,
    showOpenOnly: $("#pref-open").checked,
    showVerify: $("#pref-verify").checked,
    showHistory: $("#pref-history").checked,
    topPriority: $("#pref-top").value,
    dealbreakers: $("#pref-dealbreakers").value,
  });
  return p;
}
function bindPreferences() {
  $("#save-preferences").onclick = () => {
    preferences = normalizedPrefs(collectPreferences());
    RadarStore.savePreferences(preferences);
    render();
    $("#save-preferences").textContent = "已保存 ✓";
    setTimeout(() => ($("#save-preferences").textContent = "保存偏好"), 1200);
  };
  document.querySelectorAll("[data-preset]").forEach(
    (b) =>
      (b.onclick = () => {
        preferences = normalizedPrefs(PRESETS[b.dataset.preset]);
        RadarStore.savePreferences(preferences);
        renderPreferences();
        bindPreferences();
        render();
      }),
  );
}
function fill(id, key) {
  [...new Set(jobs.map((j) => j[key]).filter(Boolean))].forEach((v) =>
    $(id).insertAdjacentHTML("beforeend", `<option>${v}</option>`),
  );
}
async function init() {
  [jobs, schools, coverage, systemStatus, radarCoverage, searchLogs] = await Promise.all(
    [
      "jobs.json",
      "schools.json",
      "source-coverage.json",
      "system-status.json",
      "radar-coverage.json",
      "search-log.json",
    ].map((f) =>
      fetch("data/" + f + "?v=" + Date.now()).then((r) => {
        if (!r.ok) throw Error(f + " " + r.status);
        return r.json();
      }),
    ),
  );
  preferences = normalizedPrefs(preferences);
  const open = jobs.filter((j) => j.job_status === "open"),
    verify = jobs.filter((j) => j.job_status === "verify"),
    leads = jobs.filter((j) => j.job_status === "lead"),
    published = jobs.filter((j) => j.is_new_72h),
    seen = jobs.filter(
      (j) => days(j.first_seen_date) >= -2 && days(j.first_seen_date) <= 1,
    ),
    urgent = open.filter((j) => days(j.deadline) <= 7 && days(j.deadline) >= 0);
  $("#dates").textContent = `🟢 今天 ${zhTime(systemStatus.last_automatic_update)} 已更新 · ${open.length} 当前可投 · ${verify.length} 待核实 · ${leads.length} 招聘线索`;
  $("#radar-coverage").innerHTML = radarCoverage.map((r) => `<div class="stat"><strong>${r.city}</strong><span>学校 ${r.schools_monitored} · 官方源 ${r.official_sources}<br>Discovery Query ${r.discovery_queries || r.queries_last_7d || 0} · URL ${r.urls_examined || 0}<br>线索 ${r.job_leads} · 待核实 ${r.high_confidence_pending} · 可投 ${r.verified_open}<br>失败 ${r.failed_sources || 0} · ${fmt(r.last_searched_at)}</span></div>`).join("");
  const groups = ["哈尔滨", "北京", "沈阳", "大连", "长春", "东北其他"];
  $("#cities").innerHTML = groups
    .map(
      (c) =>
        `<button data-city="${c}">${c} ${jobs.filter((j) => j.city === c && j.job_status === "open").length}/${jobs.filter((j) => j.city === c && j.job_status === "verify").length}</button>`,
    )
    .join("");
  fill("#city", "city");
  fill("#stage", "education_stage");
  fill("#type", "school_type");
  fill("#status", "job_status");
  fill("#source", "source_level");
  document
    .querySelectorAll(".filters select")
    .forEach((x) => (x.onchange = render));
  $("#reset").onclick = () => {
    quickFilter = "";
    $("#quick-note").textContent = "";
    document.querySelectorAll("[data-city]").forEach((b) => b.classList.remove("active"));
    document
      .querySelectorAll(".filters select")
      .forEach((x) => (x.selectedIndex = 0));
    render();
  };
  document.querySelectorAll("[data-city]").forEach(
    (b) =>
      (b.onclick = () => {
        quickFilter = "";
        document.querySelectorAll("[data-city]").forEach((x) => x.classList.toggle("active", x === b));
        $("#city").value = b.dataset.city === "东北其他" ? "" : b.dataset.city;
        render();
        $("#all-jobs").scrollIntoView({ behavior: "smooth" });
      }),
  );
  const applyQuickFilter = (mode, note) => {
    document.querySelectorAll(".filters select").forEach((x) => (x.selectedIndex = 0));
    document.querySelectorAll("[data-city]").forEach((b) => b.classList.remove("active"));
    quickFilter = mode;
    $("#quick-note").textContent = note;
    render();
    $("#all-jobs").scrollIntoView({ behavior: "smooth" });
  };
  $("#recent-filter").onclick = () => applyQuickFilter("recent", "已筛选：最近72小时发现");
  $("#urgent-filter").onclick = () => applyQuickFilter("urgent", "已筛选：7天内截止且当前可投");
  $("#coverage-list").innerHTML = coverage
    .map(
      (s) =>
        `<div class="coverage-item"><div><b>${s.name}</b><div class="muted">${s.status_note}</div></div><span class="coverage-class ${s.automation_class}">${s.automation_class} 类</span><span>最近：${fmt(s.last_searched_at)}<br>${s.last_success === true ? "成功" : s.last_success === false ? "失败" : "未自动运行"}</span><span>${s.manual_required ? "需要人工补充" : "云端自动"}</span></div>`,
    )
    .join("");
  $("#schools").innerHTML = schools
    .map(
      (s) =>
        `<div class="school"><b>${s.school_name}</b><span>${s.city} · ${s.school_type}</span><span>近一年 ${s.recruitment_count_12m} 次</span><span>${s.currently_hiring ? "当前招聘" : "暂无当前招聘"}</span></div>`,
    )
    .join("");
  $("#search-log").innerHTML = searchLogs.slice(-5).reverse().map((x) => `<div class="log-item"><b>${x.run_type || "搜索运行"}</b><span>${zhTime(x.timestamp)} · 学校 ${x.schools_actually_checked ?? x.schools_checked ?? 0} · Source ${x.sources_actually_fetched ?? x.known_sources_checked ?? 0} · Query ${x.queries_actually_sent ?? x.discovery_queries_executed ?? 0} · URL ${x.result_urls_examined ?? x.urls_examined ?? 0} · 失败 ${(x.failed_sources || []).length}</span></div>`).join("");
  renderPreferences();
  bindPreferences();
  render();
}
document.addEventListener("change", (event) => {
  if (event.target.closest("#preference-form")) {
    preferences = normalizedPrefs(collectPreferences());
    RadarStore.savePreferences(preferences);
    render();
  }
});
init().catch((e) =>
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<p class="risk">数据加载失败：${e.message}</p>`,
  ),
);
