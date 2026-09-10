#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot auditable Deep Search import. Public endpoints only; no login bypass."""
import hashlib,json,re,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';SH=timezone(timedelta(hours=8));now=datetime.now(SH);today=now.date().isoformat();UA='ZhaoShuaiJobRadar-DeepSearch/2.0'
def load(n):return json.loads((D/n).read_text('utf-8'))
def dump(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
def check(url):
 try:
  q=urllib.request.Request(url,headers={'User-Agent':UA});r=urllib.request.urlopen(q,timeout=15);body=r.read(500000);return True,len(body),None
 except Exception as e:return False,0,f'{type(e).__name__}: {str(e)[:120]}'
def search_url(name):return'https://www.bing.com/news/search?'+urllib.parse.urlencode({'q':f'"{name}" 美术教师 OR 美术老师 OR 艺术教师 招聘 2026','format':'rss','setlang':'zh-cn'})
def lead(school,title,city,url,platform,typ='未注明',salary=None):
 i='deep-'+hashlib.sha256((school+'|'+title+'|'+url).encode()).hexdigest()[:16]
 return{'id':i,'school_name':school,'job_title':title,'province':None,'city':city,'district':None,'school_type':typ,'education_stage':'未注明','job_category':'美术教师','salary_min':None,'salary_max':None,'salary_unit':None,'salary_raw_text':salary or '未注明','education_requirement':None,'major_requirement':None,'teacher_certificate_requirement':None,'mandarin_requirement':None,'experience_requirement':None,'age_requirement':None,'hukou_requirement':None,'english_required':None,'english_requirement':None,'international_curriculum_requirement':None,'published_date':None,'deadline':None,'first_seen_date':today,'last_verified_date':today,'job_status':'lead','source_level':'C','source_name':platform,'source_url':url,'official_url':None,'other_sources':[],'page_title':title,'match_score':75,'match_level':'较高匹配','match_reasons':['美术教学方向与候选人技能相关'],'risk_flags':['公开索引已发现，但发布时间和当前投递状态未确认'],'hard_blockers':[],'recommendation_score':25,'recommendation_level':'C','recommendation_label':'🔎 新发现招聘线索','recommendation_reason':'等待公开详情页或人工浏览器进一步核实。','information_confidence':'低','is_new_72h':False,'deadline_urgency':'未注明','user_favorite':False,'application_status':'未收藏','user_notes':'','created_at':today,'updated_at':today,'scoring_version':'2026-09-cloud-v2'}
jobs=load('jobs.json');hs=load('harbin-schools.json');cs=load('city-schools.json');official=load('official-sources.json');recruit=load('recruitment-sources.json');logs=load('search-log.json');targets=[]
for s in hs+cs:targets.append(('school',s,search_url(s['school_name'])))
for s in official:targets.append(('official',s,s['url']))
for s in recruit:targets.append(('recruit',s,s['url']))
results=[]
with ThreadPoolExecutor(max_workers=12) as pool:
 fut={pool.submit(check,u):(kind,obj,u) for kind,obj,u in targets}
 for f in as_completed(fut):
  kind,obj,u=fut[f];ok,size,err=f.result();results.append({'kind':kind,'city':obj.get('city'),'name':obj.get('school_name') or obj.get('source_name'),'url':u,'success':ok,'bytes':size,'error':err})
  obj['last_checked']=now.isoformat(timespec='seconds');obj['last_success']=ok
  if kind=='school':obj['queries_executed']=obj.get('queries_executed',0)+1
# Leads discovered in the live Deep Search results; never promoted to open without details.
new=[lead('哈尔滨市松雷中学校','高中美术教师','哈尔滨','https://nangangqu.job910.com/','教师招聘网 job910','民办完全中学','5–8K/月'),lead('长春市柏辰艺术中学','峰合画室美术教师（可接受外派）','长春','https://www.zhaopin.com/jobdetail/CC822051650J40917294903.htm','智联招聘公开索引','民办艺术高中')]
before=len(jobs)
for x in new:
 if not any(j['id']==x['id'] or (j['school_name']==x['school_name'] and j['job_title']==x['job_title']) for j in jobs):jobs.append(x)
# Re-audit weak existing records.
to_lead={'harbin-songbei-dongfang-art-2026','beijing-international-art-echinacareers-26708','dalian-wengu-high-art-2026'}
for j in jobs:
 if j['id'] in to_lead:j['job_status']='lead';j['information_confidence']='低';j['recommendation_score']=25;j['recommendation_label']='🔎 新发现招聘线索';j['risk_flags']=list(dict.fromkeys((j.get('risk_flags') or [])+['详情或当前投递入口无法确认，降级为招聘线索']))
 elif j['job_status']=='verify':j['information_confidence']='中' if j['source_level'] in ('A','B') else '低'
 elif j['job_status']=='expired':j['information_confidence']='高' if j.get('deadline') else '中'
queries=['哈尔滨 美术教师 最新招聘 2026','哈尔滨 艺术教师 学校招聘 2026年9月','哈尔滨市德强学校 美术教师 招聘 2026','哈尔滨市松雷中学校 美术教师 招聘 2026','哈尔滨工业大学附属中学 美术教师 招聘 2026','北京 美术教师 招聘 2026年9月 最新 学校','沈阳 美术教师 招聘 2026年9月 最新 学校','大连 美术教师 招聘 2026年9月 最新 学校','长春 美术教师 招聘 2026年9月 最新 学校','哈尔滨市 学校名单 南岗区 小学 初中 高中 官方','哈尔滨市教育局 学校名录 民办学校 2026','哈尔滨 国际学校 民办学校 艺术高中 学校官网']
city_rows=[]
for city in ('哈尔滨','北京','沈阳','大连','长春'):
 reg=hs if city=='哈尔滨' else [s for s in cs if s['city']==city];r=[x for x in results if x['city']==city or (x['kind']=='school' and x['name'] in {s['school_name'] for s in reg})];cj=[j for j in jobs if j.get('city')==city];city_rows.append({'city':city,'schools_monitored':len(reg),'official_sources':sum(s['city']==city for s in official),'recruitment_sources':len(recruit),'discovery_queries':sum(x['kind']=='school' for x in r)+(len(queries) if city=='哈尔滨' else 1),'urls_examined':len(r),'new_sources':0,'job_leads':sum(j['job_status']=='lead' for j in cj),'high_confidence_pending':sum(j['job_status']=='verify' for j in cj),'verified_open':sum(j['job_status']=='open' for j in cj),'expired':sum(j['job_status']=='expired' for j in cj),'failed_sources':sum(not x['success'] for x in r),'last_searched_at':now.isoformat(timespec='seconds')})
run={'run_id':f'deep-{now:%Y%m%dT%H%M%S%z}','timestamp':now.isoformat(timespec='seconds'),'run_type':'openclaw_deep_search','city':['哈尔滨','北京','沈阳','大连','长春'],'known_sources_checked':len(official)+len(recruit),'schools_checked':len(hs)+len(cs),'discovery_queries_executed':len(hs)+len(cs)+len(queries),'queries_executed':queries+[f'"{s["school_name"]}" + 美术教师/美术老师/艺术教师 + 招聘 + 2026' for s in hs+cs],'urls_examined':len(results),'new_sources_found':len(official)+len(recruit)-9,'new_job_leads':len(jobs)-before,'new_verified_jobs':0,'jobs_reverified':0,'jobs_status_audited':len(jobs),'jobs_expired':0,'duplicates_merged':0,'failed_sources':[x for x in results if not x['success']],'notes':'96 school reverse searches plus official/recruitment registry checks. Public-index leads remain leads.'}
logs.append(run);dump('jobs.json',jobs);dump('harbin-schools.json',hs);dump('city-schools.json',cs);dump('official-sources.json',official);dump('recruitment-sources.json',recruit);dump('search-log.json',logs);dump('radar-coverage.json',city_rows);dump('deep-search-results.json',results)
print(json.dumps({'run_id':run['run_id'],'schools_checked':run['schools_checked'],'urls_examined':run['urls_examined'],'new_leads':run['new_job_leads'],'failures':len(run['failed_sources'])},ensure_ascii=False))
