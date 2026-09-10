(function () {
  const clamp = (n) => Math.max(0, Math.min(100, Math.round(n)));
  const schoolKey = (t) => {
    t = t || "";
    if (/国际/.test(t)) return "international";
    if (/双语/.test(t)) return "bilingual";
    if (/艺术.*高|美术.*高/.test(t)) return "artHigh";
    if (/艺考/.test(t)) return "artExam";
    if (/培训|教育机构/.test(t)) return "training";
    if (/公办/.test(t)) return "public";
    if (/民办|私立/.test(t)) return "private";
    return "other";
  };
  const text = (j) =>
    [
      j.job_title,
      j.job_category,
      j.school_type,
      j.education_stage,
      ...(j.match_reasons || []),
      ...(j.risk_flags || []),
    ]
      .join(" ")
      .toLowerCase();
  window.RadarRecommendation = {
    score(j, p) {
      if (
        j.hard_blockers?.length ||
        j.job_status === "expired" ||
        j.job_status === "dead"
      )
        return 0;
      if (j.job_status === "lead") return 25;
      const t = text(j),
        rank = p.cityPriority[j.city] || p.cityPriority["东北其他"] || 1,
        sk = schoolKey(j.school_type);
      let s =
        j.match_score * 0.55 +
        rank * 3 +
        ((p.schoolTypes[sk] ?? true) ? 6 : -12);
      if (j.salary_min != null) s += j.salary_min >= p.minSalary ? 8 : -10;
      else s += p.acceptUnknownSalary ? 0 : -8;
      for (const [k, on] of Object.entries(p.jobTypes || {}))
        if (t.includes(k)) s += on ? 3 : -8;
      for (const [k, on] of Object.entries(p.stages || {}))
        if (t.includes(k) && !on) s -= 12;
      if (j.english_required && !p.acceptEnglish) s -= 18;
      if (/国际/.test(t) && !p.acceptInternational) s -= 15;
      if (/\bib\b/i.test(t) && !p.acceptIB) s -= 20;
      if (/a-level/i.test(t) && !p.acceptALevel) s -= 16;
      if (/igcse/i.test(t) && !p.acceptIGCSE) s -= 14;
      if (j.job_status === "verify") s -= 10;
      const weights = {
        salary: j.salary_min ? 8 : 0,
        stability: /公办|正式/.test(j.school_type + " " + j.job_title) ? 8 : 0,
        city: rank * 1.5,
        platform: /学校|高中|小学|初中/.test(j.school_type) ? 6 : 0,
        workload: 0,
        growth: /教师|学校/.test(j.job_title + " " + j.school_type) ? 7 : 0,
      };
      s += weights[p.topPriority] || 0;
      const blocked = (p.dealbreakers || "")
        .split(/[，,；;\n]/)
        .map((x) => x.trim().toLowerCase())
        .filter((x) => x.length > 1)
        .some((x) => t.includes(x));
      if (blocked) s -= 35;
      return clamp(s);
    },
    level(s) {
      return s >= 80
        ? ["S", "🔥 S 建议优先投"]
        : s >= 65
          ? ["A", "🟢 A 值得投"]
          : s >= 45
            ? ["B", "🟡 B 可以考虑"]
            : s > 0
              ? ["C", "⚪ C 低优先级"]
              : ["X", "🔴 X 存在硬伤"];
    },
  };
})();
