#!/usr/bin/env python3
"""Conservative cloud updater: public HTTP sources only, never deletes old data."""
from __future__ import annotations
import hashlib, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; SH=timezone(timedelta(hours=8)); now=datetime.now(SH); today=now.date().isoformat()
UA='ZhaoShuaiJobRadar/1.0 (+https://github.com/Art-Burger/zhaoshuai-art-teacher-radar)'
KEYWORDS=('美术教师','美术老师','艺术教师','视觉艺术教师','art teacher','visual arts teacher','visual art teacher','digital art teacher','fine arts teacher')
CITIES=('哈尔滨','北京','沈阳','大连','长春','大庆','齐齐哈尔','牡丹江','吉林','鞍山','抚顺','营口')

def load(name): return json.loads((DATA/name).read_text('utf-8'))
def dump(name,data):
    tmp=(DATA/name).with_suffix('.json.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8'); json.loads(tmp.read_text('utf-8')); tmp.replace(DATA/name)
def fetch(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    with urllib.request.urlopen(req,timeout=timeout) as res: return res.read(2_000_000).decode(res.headers.get_content_charset() or 'utf-8','replace')
def textify(s): return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def city_for(s): return next((c for c in CITIES if c in s),None)
def stable_id(url,title): return 'cloud-'+hashlib.sha256((url+'|'+title).encode()).hexdigest()[:16]
def recalculate_scores(j):
    """Recompute objective résumé match and a preference-neutral delivery baseline."""
    raw=' '.join(str(j.get(k) or '') for k in ('job_title','job_category','major_requirement','teacher_certificate_requirement','experience_requirement','education_stage'))+' '+' '.join(j.get('match_reasons') or [])
    score=0
    score+=15 if re.search(r'美术|绘画|艺术|art',raw,re.I) else 6
    cert=j.get('teacher_certificate_requirement'); score+=15 if cert and re.search(r'教师资格',str(cert)) else 9
    score+=18 if re.search(r'小学|初中|K12|教学|教师',raw,re.I) else 10
    score+=15 if re.search(r'素描|色彩|速写|漫画|插画|数字|绘画',raw,re.I) else 8
    score+=8 if re.search(r'经验|教学',raw,re.I) else 5
    score+=10 if j.get('city')=='哈尔滨' else 9 if j.get('city')=='北京' else 8 if j.get('city') in ('沈阳','大连','长春') else 5
    score+=8 if j.get('salary_min') is not None else 4
    score+=5 if re.search(r'漫画|插画|Photoshop|Procreate|动漫|数字绘画|角色设计',raw,re.I) else 0
    j['match_score']=min(100,score); j['match_level']='高匹配' if score>=80 else '较高匹配' if score>=70 else '中等匹配' if score>=55 else '低匹配'
    if j.get('hard_blockers') or j.get('job_status') in ('expired','dead'): rec=0
    else:
        trust={'A':10,'B':7,'C':3}.get(j.get('source_level'),2); freshness=8 if j.get('published_date') and j['published_date']>=today else 2; rec=round(score*.65+trust+freshness-(10 if j.get('job_status')=='verify' else 0))
    j['recommendation_score']=max(0,min(100,rec)); level='S' if rec>=80 else 'A' if rec>=65 else 'B' if rec>=45 else 'C' if rec>0 else 'X'; labels={'S':'🔥 S 建议优先投','A':'🟢 A 值得投','B':'🟡 B 可以考虑','C':'⚪ C 低优先级','X':'🔴 X 存在硬伤'}; j['recommendation_level']=level; j['recommendation_label']=labels[level]; j['scoring_version']='2026-09-cloud-v1'
def candidate(url,title,source_name,level='C'):
    city=city_for(title) or '未注明'; sid=stable_id(url,title)
    return {'id':sid,'school_name':source_name,'job_title':title[:100],'province':None,'city':city,'district':None,'school_type':'未注明','education_stage':'未注明','job_category':'美术教师','salary_min':None,'salary_max':None,'salary_unit':None,'salary_raw_text':'未注明','education_requirement':None,'major_requirement':None,'teacher_certificate_requirement':None,'mandarin_requirement':None,'experience_requirement':None,'age_requirement':None,'hukou_requirement':None,'english_required':None,'english_requirement':None,'international_curriculum_requirement':None,'published_date':None,'deadline':None,'first_seen_date':today,'last_verified_date':today,'job_status':'verify','source_level':level,'source_name':source_name,'source_url':url,'official_url':url if level=='A' else None,'other_sources':[],'page_title':title[:160],'match_score':55,'match_level':'待详细分析','match_reasons':['岗位方向与美术教学相关'], 'risk_flags':['自动发现线索；招聘要求与时效待深度核实'],'hard_blockers':[],'recommendation_score':35,'recommendation_level':'C','recommendation_label':'⚪ C 低优先级','recommendation_reason':'云端新发现，待核实后再决定是否投递。','is_new_72h':False,'deadline_urgency':'未注明','user_favorite':False,'application_status':'未收藏','user_notes':'','created_at':today,'updated_at':today}

def official_links(base,html):
    out=[]
    for href,raw in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',html,re.I|re.S):
        title=textify(raw); low=title.lower()
        if any(k in low for k in KEYWORDS) and ('招聘' in title or 'teacher' in low): out.append((urllib.parse.urljoin(base,href),title))
    return out
def rss_links():
    q=' OR '.join(f'"{x}"' for x in ('美术教师 招聘 2026','Art Teacher Beijing 2026','美术教师 哈尔滨 2026','美术教师 沈阳 大连 长春 2026'))
    url='https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':q,'format':'rss','setlang':'zh-cn'})
    root=ET.fromstring(fetch(url)); return [(i.findtext('link'),i.findtext('title') or '') for i in root.findall('.//item')]

jobs=load('jobs.json'); schools=load('schools.json'); logs=load('search-log.json'); coverage=load('source-coverage.json'); status=load('system-status.json'); by_id={j['id']:j for j in jobs}; failures=[]; found=0; added=0
try:
    for src in coverage:
        src['last_searched_at']=now.isoformat(timespec='seconds')
        if not src['cloud_supported']:
            src['last_success']=None; continue
        try:
            if src['id']=='public-search': links=rss_links(); level='C'
            else: page=fetch(src['url']); links=official_links(src['url'],page); level='A'
            src['last_success']=True; src['last_error']=None; found+=len(links)
            for url,title in links:
                if not url or not title: continue
                item=candidate(url,title,src['name'],level); jid=item['id']
                if jid not in by_id: jobs.append(item); by_id[jid]=item; added+=1
        except Exception as exc:
            src['last_success']=False; src['last_error']=f'{type(exc).__name__}: {str(exc)[:180]}'; failures.append({'site':src['name'],'url':src['url'],'failed_at':now.isoformat(timespec='seconds'),'reason':src['last_error'],'retry':True})
    for j in jobs:
        if j.get('deadline') and j['deadline']<today and j.get('job_status')=='open': j['job_status']='expired'; j['updated_at']=today
        if j.get('job_status') in ('open','verify') and j.get('source_level')=='A':
            try: fetch(j['source_url']); j['last_verified_date']=today
            except Exception as exc: failures.append({'site':j['source_name'],'url':j['source_url'],'failed_at':now.isoformat(timespec='seconds'),'reason':f'{type(exc).__name__}: {str(exc)[:180]}','retry':True})
        recalculate_scores(j)
    # Stable-key dedupe. Existing records win; no automatic destructive merge.
    seen=set(); unique=[]
    for j in jobs:
        key=(j.get('school_name'),j.get('job_title'),j.get('city'),j.get('education_stage'),j.get('published_date'))
        if key in seen and j['id'].startswith('cloud-'): continue
        seen.add(key); unique.append(j)
    jobs=unique
    totals={'sources_checked':sum(1 for s in coverage if s['cloud_supported']),'pages_found':found,'candidate_jobs':found,'open':sum(j['job_status']=='open' for j in jobs),'verify':sum(j['job_status']=='verify' for j in jobs),'expired':sum(j['job_status']=='expired' for j in jobs),'duplicates_merged':len(by_id)-len(jobs),'failures':len(failures),'new_jobs':added}
    logs.append({'date':today,'run_type':'github_actions_cloud_update','run_at':now.isoformat(timespec='seconds'),'queries':['公开教育局/人社局/学校招聘索引','Bing News RSS：美术教师与 Art Teacher 城市组合'],'totals':totals,'failures':failures,'source_unavailable_for_cloud_automation':[s['name'] for s in coverage if not s['cloud_supported']]})
    next_run=datetime.combine(now.date()+(timedelta(days=1) if now.hour>=9 else timedelta()),datetime.min.time(),SH).replace(hour=9)
    status.update({'last_data_update':now.isoformat(timespec='seconds'),'last_automatic_update':now.isoformat(timespec='seconds'),'next_scheduled_update':next_run.isoformat(timespec='seconds'),'update_status':'partial' if any(not s['cloud_supported'] for s in coverage) or failures else 'ok','status_label':'🟡 部分来源暂不可自动核实' if any(not s['cloud_supported'] for s in coverage) or failures else '🟢 数据已更新','last_error':'; '.join(f['reason'] for f in failures[:3]) or None})
    dump('jobs.json',jobs); dump('schools.json',schools); dump('search-log.json',logs); dump('source-coverage.json',coverage); dump('system-status.json',status)
    print(json.dumps({'date':today,'added':added,'total':len(jobs),'failures':len(failures)},ensure_ascii=False))
except Exception as exc:
    print(f'FATAL: {type(exc).__name__}: {exc}',file=sys.stderr); sys.exit(1)
