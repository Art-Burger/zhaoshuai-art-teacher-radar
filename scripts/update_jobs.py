#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search Engine V2: additive public-source monitoring plus rotating discovery."""
from __future__ import annotations
import hashlib,json,re,sys,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';SH=timezone(timedelta(hours=8));now=datetime.now(SH);today=now.date().isoformat();UA='ZhaoShuaiJobRadar/2.0 (+https://github.com/Art-Burger/zhaoshuai-art-teacher-radar)'
ART=('美术教师','美术老师','艺术教师','美术学科教师','美术专任教师','素描教师','色彩教师','速写教师','漫画教师','插画教师','动漫教师','数字绘画教师','艺考美术教师','少儿美术教师','art teacher','visual arts teacher','art & design teacher','digital art teacher')
def load(n):return json.loads((DATA/n).read_text('utf-8'))
def dump(n,x):p=(DATA/n).with_suffix('.json.tmp');p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8');json.loads(p.read_text('utf-8'));p.replace(DATA/n)
def fetch(url,timeout=18):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xml;q=0.9,*/*;q=0.8'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(2_000_000).decode(r.headers.get_content_charset() or 'utf-8','replace')
def clean(s):return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()
def sid(url,title):return'lead-'+hashlib.sha256((url+'|'+title).encode()).hexdigest()[:16]
def links(base,html):
 out=[]
 for href,raw in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',html,re.I|re.S):
  title=clean(raw); low=title.lower()
  if title and any(k in low for k in ART) and ('招聘' in title or 'teacher' in low):out.append((urllib.parse.urljoin(base,href),title))
 return out
def rss(query):
 url='https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':query,'format':'rss','setlang':'zh-cn'});root=ET.fromstring(fetch(url));return[(x.findtext('link'),x.findtext('title') or '') for x in root.findall('.//item')]
def city_of(s):return next((c for c in ('哈尔滨','北京','沈阳','大连','长春','大庆','齐齐哈尔','牡丹江','吉林市','鞍山','抚顺','营口') if c in s),'未注明')
def lead(url,title,source,level='C'):
 city=city_of(title);return{'id':sid(url,title),'school_name':source,'job_title':title[:100],'province':None,'city':city,'district':None,'school_type':'未注明','education_stage':'未注明','job_category':'美术教师','salary_min':None,'salary_max':None,'salary_unit':None,'salary_raw_text':'未注明','education_requirement':None,'major_requirement':None,'teacher_certificate_requirement':None,'mandarin_requirement':None,'experience_requirement':None,'age_requirement':None,'hukou_requirement':None,'english_required':None,'english_requirement':None,'international_curriculum_requirement':None,'published_date':None,'deadline':None,'first_seen_date':today,'last_verified_date':today,'job_status':'lead','source_level':level,'source_name':source,'source_url':url,'official_url':url if level=='A' else None,'other_sources':[],'page_title':title[:160],'match_score':55,'match_level':'中等匹配','match_reasons':['招聘线索与美术教学方向相关'],'risk_flags':['新发现招聘线索；正文、要求和当前投递状态待核实'],'hard_blockers':[],'recommendation_score':25,'recommendation_level':'C','recommendation_label':'🔎 新发现招聘线索','recommendation_reason':'先保留发现信号，核实前不进入可投推荐。','information_confidence':'低','is_new_72h':False,'deadline_urgency':'未注明','user_favorite':False,'application_status':'未收藏','user_notes':'','created_at':today,'updated_at':today,'scoring_version':'2026-09-cloud-v2'}
def score(j):
 raw=' '.join(str(j.get(k) or '') for k in ('job_title','job_category','major_requirement','teacher_certificate_requirement','experience_requirement','education_stage'))+' '+' '.join(j.get('match_reasons') or []);s=(15 if re.search(r'美术|绘画|艺术|art',raw,re.I) else 6)+(15 if re.search(r'教师资格',str(j.get('teacher_certificate_requirement') or '')) else 9)+(18 if re.search(r'小学|初中|K12|教学|教师',raw,re.I) else 10)+(15 if re.search(r'素描|色彩|速写|漫画|插画|数字|绘画',raw,re.I) else 8)+(8 if re.search(r'经验|教学',raw,re.I) else 5)+(10 if j.get('city')=='哈尔滨' else 9 if j.get('city')=='北京' else 8 if j.get('city') in ('沈阳','大连','长春') else 5)+(8 if j.get('salary_min') is not None else 4)+(5 if re.search(r'漫画|插画|Photoshop|Procreate|动漫|数字绘画|角色设计',raw,re.I) else 0);j['match_score']=min(100,s);j['match_level']='高匹配' if s>=80 else '较高匹配' if s>=70 else '中等匹配' if s>=55 else '低匹配';j['information_confidence']='高' if j.get('source_level')=='A' and j.get('deadline') else '中' if j.get('source_level') in ('A','B') and j.get('last_verified_date') else '低'
 if j.get('job_status')=='lead':rec=25
 elif j.get('hard_blockers') or j.get('job_status') in ('expired','dead'):rec=0
 else:rec=round(s*.65+{'A':10,'B':7,'C':3}.get(j.get('source_level'),2)+2-(10 if j.get('job_status')=='verify' else 0))
 j['recommendation_score']=max(0,min(100,rec));j['scoring_version']='2026-09-cloud-v2'
def queries_for(day,school_names):
 base=['哈尔滨 美术教师 最新招聘 2026','哈尔滨 艺术教师 学校招聘 2026年9月']
 rotation={0:['哈尔滨 小学美术教师 教育局 招聘','哈尔滨 初中美术教师 人社局'],1:['北京 Visual Arts Teacher 2026-2027','北京 民办学校 美术教师 秋季招聘'],2:['沈阳 美术教师 最新招聘','长春 艺考美术教师 最新招聘'],3:[f'{n} 美术教师 招聘 2026' for n in school_names[:4]],4:['大连 高中美术教师 最新招聘','东北 艺术高中 美术教师 招聘'],5:['漫画教师 插画教师 数字绘画教师 东北 招聘','艺考美术教师 哈尔滨 沈阳 长春 招聘'],6:['美术教师 2026年9月 教育局 人社局 东北','Art Teacher Beijing Harbin latest']};return base+rotation[day]
jobs=load('jobs.json');logs=load('search-log.json');official=load('official-sources.json');recruit=load('recruitment-sources.json');harbin=load('harbin-schools.json');others=load('city-schools.json');system_status=load('system-status.json');coverage_data=[];fail=[];urls=set();new_sources=0;new_leads=0;verified=0;expired=0;reverified=0;known_checked=0;schools_checked=0
try:
 cities=list(dict.fromkeys(['哈尔滨']+{0:['哈尔滨'],1:['北京'],2:['沈阳','长春'],3:['哈尔滨'],4:['大连'],5:['哈尔滨','沈阳','长春'],6:['哈尔滨','北京','沈阳','大连','长春']}[now.weekday()]))
 for src in official:
  if src['city'] not in cities:continue
  known_checked+=1;urls.add(src['url'])
  try:
   page=fetch(src['url']);found=links(src['url'],page);src.update(last_checked=now.isoformat(timespec='seconds'),last_success=True,jobs_discovered=len(found))
   for url,title in found:
    urls.add(url);item=lead(url,title,src['source_name'],'A')
    if not any(j['id']==item['id'] for j in jobs):jobs.append(item);new_leads+=1
  except Exception as e:src.update(last_checked=now.isoformat(timespec='seconds'),last_success=False);fail.append({'source_name':src['source_name'],'url':src['url'],'reason':f'{type(e).__name__}: {str(e)[:150]}'})
 school_pool=harbin if now.weekday() in (0,3,5,6) else [s for s in others if s['city'] in cities]
 qs=queries_for(now.weekday(),[s['school_name'] for s in school_pool]);schools_checked=min(4,len(school_pool))
 for q in qs:
  urls.add('https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':q,'format':'rss','setlang':'zh-cn'}))
  try:
   for url,title in rss(q):
    urls.add(url);item=lead(url,title,'公开搜索/RSS','C')
    if any(k in title.lower() for k in ART) and not any(j['id']==item['id'] for j in jobs):jobs.append(item);new_leads+=1
  except Exception as e:fail.append({'source_name':'公开搜索/RSS','url':None,'reason':f'{type(e).__name__}: {str(e)[:150]}'})
 for j in jobs:
  old=j.get('job_status');
  if j.get('deadline') and j['deadline']<today and old in ('open','verify'):j['job_status']='expired';expired+=1
  if old in ('open','verify') and j.get('source_level')=='A':
   try:fetch(j['source_url']);j['last_verified_date']=today;reverified+=1
   except Exception as e:fail.append({'source_name':j['source_name'],'url':j['source_url'],'reason':f'{type(e).__name__}: {str(e)[:150]}'})
  score(j)
 seen=set();unique=[];merged=0
 for j in jobs:
  k=(j.get('school_name'),j.get('job_title'),j.get('city'),j.get('education_stage'),j.get('published_date'))
  if k in seen and j['id'].startswith('lead-'):merged+=1;continue
  seen.add(k);unique.append(j)
 jobs=unique
 for city in ('哈尔滨','北京','沈阳','大连','长春'):
  registry=harbin if city=='哈尔滨' else [s for s in others if s['city']==city];city_jobs=[j for j in jobs if j.get('city')==city];coverage_data.append({'city':city,'schools_monitored':len(registry),'official_sources':sum(s['city']==city for s in official),'recruitment_sources':len(recruit),'queries_last_7d':sum(len(x.get('queries_executed',x.get('queries',[]))) for x in logs[-7:] if x.get('city') in (city,None))+(len(qs) if city in cities else 0),'last_searched_at':now.isoformat(timespec='seconds') if city in cities else next((x.get('last_searched_at') for x in reversed(coverage_data) if x.get('city')==city),None),'job_leads':sum(j.get('job_status')=='lead' for j in city_jobs),'high_confidence_pending':sum(j.get('job_status')=='verify' for j in city_jobs),'verified_open':sum(j.get('job_status')=='open' for j in city_jobs),'expired':sum(j.get('job_status')=='expired' for j in city_jobs)})
 run={'run_id':f'cloud-{now:%Y%m%dT%H%M%S%z}','timestamp':now.isoformat(timespec='seconds'),'run_type':'cloud_daily_radar','city':cities,'known_sources_checked':known_checked,'schools_checked':schools_checked,'discovery_queries_executed':len(qs),'queries_executed':qs,'urls_examined':len(urls),'new_sources_found':new_sources,'new_job_leads':new_leads,'new_verified_jobs':verified,'jobs_reverified':reverified,'jobs_expired':expired,'duplicates_merged':merged,'failed_sources':fail,'notes':'Additive-first V2 rotation; public leads remain leads until verified.'};logs.append(run)
 next_run=(now+timedelta(days=1)).replace(hour=9,minute=0,second=0,microsecond=0) if now.hour>=9 else now.replace(hour=9,minute=0,second=0,microsecond=0);system_status.update({'last_data_update':now.isoformat(timespec='seconds'),'last_automatic_update':now.isoformat(timespec='seconds'),'next_scheduled_update':next_run.isoformat(timespec='seconds'),'update_status':'partial' if fail else 'ok','status_label':'🟡 部分来源暂不可自动核实' if fail or any(x['automation_level']=='C' for x in recruit) else '🟢 数据已更新','last_error':'; '.join(x['reason'] for x in fail[:3]) or None})
 dump('jobs.json',jobs);dump('official-sources.json',official);dump('search-log.json',logs);dump('radar-coverage.json',coverage_data);dump('system-status.json',system_status)
 print(json.dumps({'run_id':run['run_id'],'jobs':len(jobs),'new_leads':new_leads,'urls_examined':len(urls),'failures':len(fail)},ensure_ascii=False))
except Exception as e:print(f'FATAL: {type(e).__name__}: {e}',file=sys.stderr);sys.exit(1)
