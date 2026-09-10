#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloud Daily Radar V3.

Public, additive-first discovery with auditable counters. Ordinary web results are
the primary discovery channel; news RSS is supplementary. No login, cookies,
CAPTCHA bypass, or private search API is used.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SH = timezone(timedelta(hours=8))
NOW = datetime.now(SH)
TODAY = NOW.date().isoformat()
STAMP = NOW.isoformat(timespec="seconds")
UA = "Mozilla/5.0 (compatible; ZhaoShuaiJobRadar/3.0; +https://github.com/Art-Burger/zhaoshuai-art-teacher-radar)"
ART = ("美术", "艺术教师", "艺术老师", "art teacher", "visual art", "art & design", "绘画教师", "素描教师", "色彩教师", "速写教师", "漫画教师", "插画教师", "数字绘画教师", "艺考美术")
RECRUIT = ("招聘", "教师招聘", "公开招聘", "聘用", "岗位", "人才招聘", "加入我们", "teacher", "career", "vacancy")
DETAIL_HINTS = ("教师招聘", "公开招聘", "招聘教师", "招聘公告", "招聘岗位", "岗位表", "职位表", "附件", "拟聘", "人才招聘")
MAX_BODY = 5_000_000


def load(name):
    return json.loads((DATA / name).read_text("utf-8"))


def dump(name, obj):
    tmp = (DATA / name).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", "utf-8")
    json.loads(tmp.read_text("utf-8"))
    tmp.replace(DATA / name)


def request(url, timeout=20, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.7"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(MAX_BODY)
        content_type = response.headers.get_content_type()
        if binary:
            return raw, content_type, response.geturl()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "replace"), content_type, response.geturl()


def textify(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.I | re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def anchors(base, html):
    found = []
    for href, raw in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, re.I | re.S):
        title = textify(raw)
        url = urllib.parse.urljoin(base, unescape(href))
        if title and url.startswith(("http://", "https://")):
            found.append((url, title))
    return found


def unique(items):
    out, seen = [], set()
    for url, title in items:
        key = url.split("#", 1)[0]
        if key not in seen:
            seen.add(key)
            out.append((key, title))
    return out


def bing_web(query):
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "setlang": "zh-cn", "count": 20})
    html, _, _ = request(url)
    rows = re.findall(r'<li class="b_algo".*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S)
    return url, unique([(unescape(u), textify(t)) for u, t in rows])


def duckduckgo_web(query):
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    html, _, _ = request(url)
    rows = []
    for attrs, title in re.findall(r'<a([^>]*)>(.*?)</a>', html, re.I | re.S):
        if "result__a" not in attrs:
            continue
        match = re.search(r'href=["\']([^"\']+)', attrs, re.I)
        if match:
            rows.append((match.group(1), title))
    out = []
    for href, title in rows:
        href = unescape(href)
        parsed = urllib.parse.urlparse(href)
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [href])[0]
        out.append((target, textify(title)))
    return url, unique(out)


def bing_news(query):
    url = "https://www.bing.com/news/search?" + urllib.parse.urlencode({"q": query, "format": "rss", "setlang": "zh-cn"})
    xml, _, _ = request(url)
    root = ET.fromstring(xml)
    return url, unique([(x.findtext("link") or "", x.findtext("title") or "") for x in root.findall(".//item") if x.findtext("link")])


def relevant(title, snippet=""):
    value = (title + " " + snippet).lower()
    return any(k in value for k in ART) and any(k in value for k in RECRUIT)


def suspicious_announcement(title):
    return any(x in title.lower() for x in DETAIL_HINTS)


def extract_attachment(raw, content_type, url):
    """Best-effort text extraction for public PDF/XLS/XLSX attachments."""
    suffix = urllib.parse.urlparse(url).path.lower()
    try:
        if content_type == "application/pdf" or suffix.endswith(".pdf"):
            from pypdf import PdfReader
            return " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
        if suffix.endswith(".xlsx") or "spreadsheetml" in content_type:
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            return " ".join(str(v) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for v in row if v is not None)
        if suffix.endswith(".xls") or content_type == "application/vnd.ms-excel":
            import xlrd
            wb = xlrd.open_workbook(file_contents=raw)
            return " ".join(str(wb.sheet_by_index(i).cell_value(r, c)) for i in range(wb.nsheets) for r in range(wb.sheet_by_index(i).nrows) for c in range(wb.sheet_by_index(i).ncols))
    except Exception:
        return ""
    return ""


def inspect_detail(url, counters, failures, source_name):
    try:
        raw, ctype, final_url = request(url, binary=True)
        counters["job_pages_opened"] += 1
        if ctype in ("application/pdf", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") or final_url.lower().endswith((".pdf", ".xls", ".xlsx")):
            return extract_attachment(raw, ctype, final_url), [], final_url
        html = raw.decode("utf-8", "replace")
        body = textify(html)
        attachments = []
        for attachment_url, title in anchors(final_url, html):
            if attachment_url.lower().split("?", 1)[0].endswith((".pdf", ".xls", ".xlsx")) or "附件" in title or "岗位表" in title:
                attachments.append((attachment_url, title))
        for attachment_url, _ in unique(attachments)[:6]:
            try:
                blob, kind, attachment_final = request(attachment_url, binary=True)
                counters["job_pages_opened"] += 1
                body += " " + extract_attachment(blob, kind, attachment_final)
            except Exception as exc:
                failures.append({"source_name": source_name, "url": attachment_url, "stage": "attachment", "reason": f"{type(exc).__name__}: {str(exc)[:150]}"})
        return body, attachments, final_url
    except Exception as exc:
        failures.append({"source_name": source_name, "url": url, "stage": "detail", "reason": f"{type(exc).__name__}: {str(exc)[:150]}"})
        return "", [], url


def stable_id(url, title):
    return "lead-" + hashlib.sha256((url + "|" + title).encode()).hexdigest()[:16]


def make_lead(url, title, source, level="C", school=None):
    city = next((c for c in ("哈尔滨", "北京", "沈阳", "大连", "长春") if c in (title + " " + (school or ""))), "哈尔滨" if school else "未注明")
    return {"id": stable_id(url, title), "school_name": school or source, "job_title": title[:100], "province": None, "city": city, "district": None, "school_type": "未注明", "education_stage": "未注明", "job_category": "美术教师", "salary_min": None, "salary_max": None, "salary_unit": None, "salary_raw_text": "未注明", "education_requirement": None, "major_requirement": None, "teacher_certificate_requirement": None, "mandarin_requirement": None, "experience_requirement": None, "age_requirement": None, "hukou_requirement": None, "english_required": None, "english_requirement": None, "international_curriculum_requirement": None, "published_date": None, "deadline": None, "first_seen_date": TODAY, "last_verified_date": TODAY, "job_status": "lead", "source_level": level, "source_name": source, "source_url": url, "official_url": url if level == "A" else None, "other_sources": [], "page_title": title[:160], "match_score": 55, "match_level": "中等匹配", "match_reasons": ["公开页面发现美术教学招聘信号"], "risk_flags": ["正文要求和当前投递状态待核实"], "hard_blockers": [], "recommendation_score": 25, "recommendation_level": "C", "recommendation_label": "🔎 新发现招聘线索", "recommendation_reason": "核实前不进入可投推荐。", "information_confidence": "低", "is_new_72h": False, "deadline_urgency": "未注明", "user_favorite": False, "application_status": "未收藏", "user_notes": "", "created_at": TODAY, "updated_at": TODAY, "scoring_version": "2026-09-cloud-v3"}


def add_lead(jobs, candidate, counters, created_urls):
    duplicate = any(j.get("id") == candidate["id"] or (j.get("school_name") == candidate["school_name"] and j.get("job_title") == candidate["job_title"] and j.get("city") == candidate["city"]) for j in jobs)
    if not duplicate:
        jobs.append(candidate)
        counters["job_leads_created"] += 1
        created_urls.append(candidate["source_url"])


def run_search(query, engine, counters, failures, channel):
    counters["queries_actually_sent"] += 1
    try:
        search_url, results = engine(query)
        counters["result_pages_received"] += 1
        counters["result_urls_examined"] += len(results)
        return results, True
    except Exception as exc:
        failures.append({"source_name": channel, "url": None, "stage": "search", "query": query, "reason": f"{type(exc).__name__}: {str(exc)[:150]}"})
        return [], False


def recruitment_strategy(source):
    name = source.get("source_name", "")
    if name == "Bing News RSS":
        return "news_rss_supplement"
    if name in ("Nord Anglia Careers", "eChinaCareers"):
        return "public_careers_index_and_site_query"
    if name in ("高校人才网", "教师招聘网 job910", "粉笔资讯", "全国事业单位招聘网", "高校就业信息网集合"):
        return "public_index_fetch_and_site_query"
    return "public_search_index_only_manual_detail"


def select_schools(schools, count=20):
    def key(s):
        checked = s.get("last_actually_checked") or "0000"
        priority = 0 if s.get("monitoring_priority") == "S" else 1
        return checked, priority, s.get("id", "")
    return sorted(schools, key=key)[:count]


def main():
    jobs = load("jobs.json")
    logs = load("search-log.json")
    official = load("official-sources.json")
    recruitment = load("recruitment-sources.json")
    schools = load("harbin-schools.json")
    system_status = load("system-status.json")
    failures, created_urls = [], []
    c = {k: 0 for k in ("schools_actually_checked", "sources_actually_fetched", "queries_actually_sent", "result_pages_received", "result_urls_examined", "job_pages_opened", "job_leads_created", "jobs_verified_open")}

    # 1) Known official recruitment columns: fetch index, open likely announcements,
    # inspect body and public PDF/Excel attachments for art roles.
    for src in [x for x in official if x.get("city") == "哈尔滨" and x.get("automation_level") in ("A", "B")]:
        src["last_checked"] = STAMP
        try:
            html, _, final_url = request(src["url"])
            c["sources_actually_fetched"] += 1
            src["last_success"] = True
            discovered = 0
            candidates = [(u, t) for u, t in unique(anchors(final_url, html)) if suspicious_announcement(t)][:25]
            for url, title in candidates:
                if not suspicious_announcement(title):
                    continue
                body, _, detail_url = inspect_detail(url, c, failures, src["source_name"])
                if any(k in body.lower() for k in ART):
                    display = title if any(k in title.lower() for k in ART) else f"{title}（正文/岗位表含美术岗位）"
                    add_lead(jobs, make_lead(detail_url, display, src["source_name"], "A"), c, created_urls)
                    discovered += 1
            src["jobs_discovered"] = discovered
        except Exception as exc:
            src["last_success"] = False
            failures.append({"source_name": src["source_name"], "url": src["url"], "stage": "source", "reason": f"{type(exc).__name__}: {str(exc)[:150]}"})

    # 2) True least-recently-checked school queue. A successful ordinary web result
    # page counts as a check; merely existing in the registry does not.
    selected = select_schools(schools, 20)
    for index, school in enumerate(selected):
        query = f'"{school["school_name"]}" (美术教师 OR 美术老师 OR 艺术教师) 招聘 2026'
        results, received = run_search(query, bing_web if index % 2 == 0 else duckduckgo_web, c, failures, "学校反向网页搜索")
        if received:
            school["last_checked"] = STAMP
            school["last_actually_checked"] = STAMP
            school["last_success"] = True
            school["queries_executed"] = school.get("queries_executed", 0) + 1
            c["schools_actually_checked"] += 1
        relevant_rows = [(u, t) for u, t in results if relevant(t)]
        school["jobs_discovered"] = len(relevant_rows)
        for url, title in relevant_rows[:5]:
            body, _, final_url = inspect_detail(url, c, failures, school["school_name"])
            if any(k in (title + " " + body).lower() for k in ART):
                add_lead(jobs, make_lead(final_url, title, "学校反向网页搜索", "C", school["school_name"]), c, created_urls)

    # 3) General web discovery: ten distinct queries, split across two ordinary
    # web result engines. News RSS is an extra channel, never the primary one.
    general_queries = [
        "哈尔滨 美术教师 招聘 2026 最新", "哈尔滨 小学美术教师 招聘 2026",
        "哈尔滨 初中美术教师 招聘 2026", "哈尔滨 高中美术教师 招聘 2026",
        "哈尔滨 艺术教师 学校招聘 2026年9月", "哈尔滨 美术学科教师 教育局 招聘",
        "哈尔滨 美术教师 人社局 事业单位 招聘", "哈尔滨 民办学校 美术老师 招聘",
        "哈尔滨 国际学校 Visual Arts Teacher", "哈尔滨 艺考美术教师 素描教师 招聘",
    ]
    for index, query in enumerate(general_queries):
        rows, _ = run_search(query, bing_web if index % 2 == 0 else duckduckgo_web, c, failures, "通用网页搜索")
        for url, title in rows:
            if relevant(title):
                body, _, final_url = inspect_detail(url, c, failures, "通用网页搜索")
                if any(k in (title + " " + body).lower() for k in ART):
                    add_lead(jobs, make_lead(final_url, title, "通用网页搜索", "C"), c, created_urls)
    for query in general_queries[:2]:
        rows, _ = run_search(query, bing_news, c, failures, "新闻/RSS补充")
        for url, title in rows:
            if relevant(title):
                add_lead(jobs, make_lead(url, title, "新闻/RSS补充", "C"), c, created_urls)

    # 4) Recruitment source adapters. A/B sources are directly fetched and also
    # queried via their public domain index. C sources are not called "fetched";
    # only their public search-engine index is used and the limitation is logged.
    for src in recruitment:
        host = urllib.parse.urlparse(src["url"]).netloc.removeprefix("www.")
        src["last_checked"] = STAMP
        src["adapter"] = recruitment_strategy(src)
        if src.get("automation_level") in ("A", "B"):
            try:
                request(src["url"])
                c["sources_actually_fetched"] += 1
                src["last_success"] = True
            except Exception as exc:
                src["last_success"] = False
                failures.append({"source_name": src["source_name"], "url": src["url"], "stage": "source", "reason": f"{type(exc).__name__}: {str(exc)[:150]}"})
        else:
            src["last_success"] = False
            src["source_unavailable_for_cloud_automation"] = True
        query = f"site:{host} 哈尔滨 美术教师 招聘"
        rows, _ = run_search(query, bing_web, c, failures, f'{src["source_name"]}公开索引')
        found = 0
        for url, title in rows:
            if relevant(title):
                found += 1
                add_lead(jobs, make_lead(url, title, f'{src["source_name"]}公开索引', "C"), c, created_urls)
        src["jobs_discovered"] = found

    # Conservative status and dedupe maintenance.
    expired = 0
    for job in jobs:
        if job.get("deadline") and job["deadline"] < TODAY and job.get("job_status") in ("open", "verify"):
            job["job_status"] = "expired"
            expired += 1
    seen, deduped, merged = set(), [], 0
    for job in jobs:
        key = (job.get("school_name"), job.get("job_title"), job.get("city"), job.get("education_stage"), job.get("published_date"))
        if key in seen and str(job.get("id", "")).startswith("lead-"):
            merged += 1
            continue
        seen.add(key)
        deduped.append(job)
    jobs = deduped

    seven_days_ago = NOW - timedelta(days=7)
    checked_7d = 0
    for school in schools:
        try:
            if school.get("last_actually_checked") and datetime.fromisoformat(school["last_actually_checked"]) >= seven_days_ago:
                checked_7d += 1
        except ValueError:
            pass
    run = {
        "run_id": f"cloud-v3-{NOW:%Y%m%dT%H%M%S%z}", "timestamp": STAMP, "run_type": "cloud_daily_radar_v3", "city": ["哈尔滨"],
        "registered_schools": len(schools), "schools_actually_checked": c["schools_actually_checked"], "schools_checked_last_7_days": checked_7d,
        "registered_sources": sum(x.get("city") == "哈尔滨" for x in official) + len(recruitment), "sources_actually_fetched": c["sources_actually_fetched"],
        "queries_actually_sent": c["queries_actually_sent"], "result_pages_received": c["result_pages_received"],
        "result_urls_examined": c["result_urls_examined"], "job_pages_opened": c["job_pages_opened"],
        "job_leads_created": c["job_leads_created"], "new_job_lead_urls": created_urls, "jobs_verified_open": c["jobs_verified_open"],
        "jobs_expired": expired, "duplicates_merged": merged, "failed_sources": failures,
        "channels": {"ordinary_web_search": "primary", "news_rss": "supplement", "school_reverse_search": True, "official_body_and_attachments": True, "recruitment_public_index": True},
        "notes": "Counters represent completed requests only; registry size is never counted as fetched coverage."
    }
    logs.append(run)
    coverage = load("radar-coverage.json")
    for row in coverage:
        if row.get("city") == "哈尔滨":
            row.update({"registered_schools": len(schools), "schools_actually_checked_today": c["schools_actually_checked"], "schools_checked_last_7_days": checked_7d, "registered_sources": sum(x.get("city") == "哈尔滨" for x in official) + len(recruitment), "sources_actually_fetched_today": c["sources_actually_fetched"], "queries_actually_sent_today": c["queries_actually_sent"], "result_pages_received_today": c["result_pages_received"], "result_urls_examined_today": c["result_urls_examined"], "job_pages_opened_today": c["job_pages_opened"], "last_searched_at": STAMP})
    next_run = (NOW + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0) if NOW.hour >= 9 else NOW.replace(hour=9, minute=0, second=0, microsecond=0)
    system_status.update({"last_data_update": STAMP, "last_automatic_update": STAMP, "next_scheduled_update": next_run.isoformat(timespec="seconds"), "update_status": "partial" if failures else "ok", "status_label": "🟡 部分来源暂不可自动核实" if failures else "🟢 数据已更新", "last_error": "; ".join(x["reason"] for x in failures[:3]) or None})
    dump("jobs.json", jobs)
    dump("harbin-schools.json", schools)
    dump("official-sources.json", official)
    dump("recruitment-sources.json", recruitment)
    dump("search-log.json", logs)
    dump("radar-coverage.json", coverage)
    dump("system-status.json", system_status)
    print(json.dumps(run, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
