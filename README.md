# 🎨美术教师求职雷达

静态个人招聘情报网站：岗位搜索、真实性状态、匹配分析、学校 Watchlist 与浏览器本地投递进度。

## 网站入口

https://art-burger.github.io/zhaoshuai-art-teacher-radar/

## 数据与更新

- `data/jobs.json`：岗位、验证、匹配和推荐信息
- `data/schools.json`：目标学校与历史招聘规律
- `data/search-log.json`：搜索范围、统计和失败记录

首次建立与第一轮判断基准为 2026-09-09；后续更新使用实际运行日期。稳定 `job_id` 将岗位更新与 `localStorage` 中的收藏、投递状态和备注分离。每轮应重新验证、检查截止日期、合并重复、更新学校雷达并运行 `npm test`。

## 隐私与免责声明

公开仓库不保存电话、微信、生日、住址、身份证、私人照片或简历原文件。岗位摘要仅用于求职研判，完整要求、时效与资格以原招聘页面为准。个人状态仅保存在当前浏览器，不提供跨设备同步。

最后更新：2026-09-09

## 云端自动更新

`Daily Job Radar Update` 位于 `.github/workflows/daily-update.yml`，每天 `01:00 UTC`（北京时间 09:00）运行，也支持在 GitHub Actions 页面手动运行。任务由 GitHub 托管 runner 执行，不依赖个人电脑开机。它先备份数据，再运行保守型公开来源搜索、验证、去重、日期检查和测试；只有通过测试的数据才提交并部署到 Pages。

自动搜索只覆盖无需私人登录的公开 HTTP 来源。教育局、人社局和已登记学校官网为 A 类；公开搜索/RSS 和部分动态页为 B 类有限支持；BOSS、智联、猎聘、万行等登录、CAPTCHA 或强反爬来源为 C 类，仍需人工/OpenClaw 补充。具体状态见 `data/source-coverage.json` 和网站“数据来源与覆盖情况”。

## 个人偏好与状态

网站“我的求职偏好”提供城市优先级、薪资、学校性质、学段、岗位方向、国际课程接受度、展示选项、关注重点、不能接受条件及四套 Preset。Match Score 是客观履历匹配，不随偏好变化；Recommendation Score 在浏览器中根据偏好即时重算。

偏好、收藏、投递、面试和备注通过 `js/storage.js` 统一保存在浏览器 `localStorage`，旧版岗位状态会自动迁移。当前不支持跨设备同步；数据接口已与 UI 分离，未来可替换为 Supabase/Firebase 适配器。
