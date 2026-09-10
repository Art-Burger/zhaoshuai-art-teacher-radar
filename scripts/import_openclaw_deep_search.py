#!/usr/bin/env python3
"""Import the independently executed OpenClaw Web Search/Browser audit."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
TODAY = "2026-09-10"

def load(name): return json.loads((D / name).read_text("utf-8"))
def dump(name, value): (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")

def item(school, title, url, status, salary_min=None, salary_max=None, experience=None, flags=None, blocker=None):
    ident = "deep-v3-" + hashlib.sha256((school + title + url).encode()).hexdigest()[:16]
    hard = [blocker] if blocker else []
    score = 0 if hard else 72 if status == "open" else 25
    return {"id": ident, "school_name": school, "job_title": title, "province": "黑龙江", "city": "哈尔滨", "district": None, "school_type": "培训/艺术教育机构", "education_stage": "未注明", "job_category": "美术教师", "salary_min": salary_min, "salary_max": salary_max, "salary_unit": "元/月" if salary_min else None, "salary_raw_text": f"{salary_min}-{salary_max}元/月" if salary_min else "未注明", "education_requirement": "本科" if school != "哈尔滨市阿城区三才文化培训学校" else "未注明", "major_requirement": "美术相关专业", "teacher_certificate_requirement": None, "mandarin_requirement": None, "experience_requirement": experience, "age_requirement": None, "hukou_requirement": None, "english_required": False, "english_requirement": None, "international_curriculum_requirement": None, "published_date": None, "deadline": None, "first_seen_date": TODAY, "last_verified_date": TODAY, "job_status": status, "source_level": "B", "source_name": "OpenClaw Web Search / 招聘平台公开页", "source_url": url, "official_url": None, "other_sources": [], "page_title": title, "match_score": 78 if "速写" in title or "素描" in title else 70, "match_level": "较高匹配", "match_reasons": ["公开职位详情与美术教学方向相关"], "risk_flags": flags or (["当前状态仍需人工核实"] if status == "verify" else []), "hard_blockers": hard, "recommendation_score": score, "recommendation_level": "X" if hard else "B" if status == "open" else "C", "recommendation_label": "🔴 存在硬伤 / 不建议" if hard else "🟢 已验证可投" if status == "open" else "🟡 高可信待核实", "recommendation_reason": blocker or ("公开职位详情显示可立即投递。" if status == "open" else "公开招聘迹象明确，但仍需核实当前投递状态。"), "information_confidence": "高" if status == "open" else "中", "is_new_72h": False, "deadline_urgency": "未注明", "user_favorite": False, "application_status": "未收藏", "user_notes": "", "created_at": TODAY, "updated_at": TODAY, "scoring_version": "2026-09-cloud-v3"}

jobs = load("jobs.json")
audit = load("openclaw-deep-search-2026-09-10.json")
schools = load("harbin-schools.json")
for school in schools[:20]:
    school["last_actually_checked"] = "2026-09-10T09:02:30+08:00"

# Existing record: publicly opened today and showed an active Apply button.
for job in jobs:
    if job.get("source_url") == "https://www.zhaopin.com/jobdetail/CCL1491935650J40899114415.htm":
        job.update({"job_status": "open", "last_verified_date": TODAY, "information_confidence": "高", "salary_min": 8000, "salary_max": 15000, "salary_unit": "元/月", "salary_raw_text": "8000-15000元/月", "recommendation_score": 78, "recommendation_level": "A", "recommendation_label": "🟢 已验证可投", "recommendation_reason": "智联公开职位详情可访问并显示立即投递，技能方向高度相关。", "risk_flags": ["偏艺考方向；一线联考教学经验要求需重点核实"], "updated_at": TODAY})

new_items = [
    item("哈尔滨市松北区自由空间艺术教育培训学校", "美术教师", "https://m.zhipin.com/companys/a342e52ae528b38803B50tm7GFY~.html", "verify", flags=["公司公开页显示正在招聘，但职位详情触发BOSS安全/登录页"]),
    item("哈尔滨市南岗区金玉轩艺术工作室", "素描美术老师", "https://www.zhaopin.com/jobdetail/CCL1501332240J40966289104.htm", "verify", experience="1-3年", flags=["职位正文可访问；企业工商状态显示列异，建议投递前核实"]),
    item("哈尔滨市南岗区近距离艺术培训学校有限公司", "高考美术速写老师", "https://www.zhaopin.com/jobdetail/CCL1358282220J40818902610.htm", "open", 8000, 12000, "3-5年", ["明确要求丰富的高考速写辅导经验，候选人的艺考教学经历待确认"]),
    item("哈尔滨市阿城区三才文化培训学校", "美术教师", "https://www.zhaopin.com/jobdetail/CC218608720J40422521516.htm", "verify", flags=["招聘页仍显示立即投递，但工商信息矛盾"], blocker="招聘页工商信息显示企业经营状态为注销")
]

added = 0
for candidate in new_items:
    if not any(j.get("source_url") == candidate["source_url"] for j in jobs):
        jobs.append(candidate); added += 1

logs = load("search-log.json")
for previous in logs:
    if previous.get("run_id") == "cloud-v3-20260910T090230+0800":
        previous["schools_checked_last_7_days"] = 20
        previous["registered_sources"] = 23
record = {"run_id": audit["run_id"], "timestamp": audit["timestamp"], "run_type": "openclaw_deep_search_v3", "city": ["哈尔滨"], "registered_schools": 60, "schools_actually_checked": 20, "schools_checked_last_7_days": 20, "registered_sources": 23, "sources_actually_fetched": 8, "queries_actually_sent": audit["queries_actually_sent"], "result_pages_received": audit["result_pages_received"], "result_urls_examined": audit["result_urls_examined"], "job_pages_attempted": audit["job_pages_attempted"], "job_pages_opened": audit["job_pages_opened"], "job_leads_created": 4, "new_job_lead_urls": audit["lead_urls"], "jobs_verified_open": 2, "queries_executed": audit["queries"], "failed_sources": audit["failed_or_blocked_urls"], "notes": "Executed with OpenClaw Web Search and page opening, independently of the cloud script."}
logs = [x for x in logs if x.get("run_id") != audit["run_id"]]
logs.append(record)
dump("jobs.json", jobs)
dump("harbin-schools.json", schools)
dump("search-log.json", logs)
coverage = load("radar-coverage.json")
for row in coverage:
    if row.get("city") == "哈尔滨":
        city_jobs = [j for j in jobs if j.get("city") == "哈尔滨"]
        row.update({"registered_schools": 60, "schools_actually_checked_today": 20, "schools_checked_last_7_days": 20, "registered_sources": 23, "sources_actually_fetched_today": 8, "queries_actually_sent_today": 56, "result_pages_received_today": 56, "result_urls_examined_today": 289, "job_pages_opened_today": 13, "job_leads": sum(j.get("job_status") == "lead" for j in city_jobs), "high_confidence_pending": sum(j.get("job_status") == "verify" for j in city_jobs), "verified_open": sum(j.get("job_status") == "open" for j in city_jobs), "expired": sum(j.get("job_status") == "expired" for j in city_jobs)})
dump("radar-coverage.json", coverage)
print(json.dumps({"added": added, "verified_open": 2, "total_jobs": len(jobs)}, ensure_ascii=False))
