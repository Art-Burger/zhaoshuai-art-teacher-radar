import { chromium } from "playwright";
import assert from "node:assert/strict";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));
await page.goto("http://127.0.0.1:8765/");
await page.waitForSelector("#jobs .card");

const sections = await page.locator("main > section, main > details").evaluateAll((nodes) => nodes.map((n) => n.id || n.querySelector("h2")?.textContent));
assert.match(String(sections[0]), /现在最值得投/, "priority jobs are first");
assert.equal(await page.locator("#top .card").count(), 2, "only two qualified priority jobs");
assert.equal(await page.locator("#maintenance").evaluate((x) => x.open), false, "maintenance details default collapsed");
assert.doesNotMatch(await page.locator("#dates").textContent(), /T\d\d:/, "update summary is human-readable");

await page.click('[data-city="哈尔滨"]');
assert.equal(await page.inputValue("#city"), "哈尔滨", "city radar changes city filter");
assert.equal(await page.locator("#jobs .card").count(), 8, "city radar filters job cards");

await page.click("#recent-filter");
assert.match(await page.locator("#quick-note").textContent(), /最近72小时/, "recent shortcut applies filter");
await page.click("#reset");

const targetCard = page.locator("#jobs .card").filter({ hasText: "北京市育英学校" }).first();
const before = await targetCard.locator(".badge").first().textContent();
await page.selectOption('[data-city-rank="北京"]', "1");
const after = await targetCard.locator(".badge").first().textContent();
assert.notEqual(before, after, "preference immediately changes recommendation");

const firstCard = page.locator("#jobs .card").first();
await firstCard.locator("[data-fav]").click();
assert.match(await page.locator("#jobs .card").first().locator("[data-fav]").textContent(), /已收藏/, "favorite updates immediately");
await page.locator("#jobs .card").first().locator(".status-menu summary").click();
await page.locator("#jobs .card").first().locator('[data-app-state][data-value="已投递"]').click();
assert.match(await page.locator("#jobs .card").first().locator(".status-menu summary").textContent(), /已投递/, "application state updates immediately");

await page.reload();
await page.waitForSelector("#jobs .card");
assert.equal(await page.inputValue('[data-city-rank="北京"]'), "1", "preference survives reload");
assert.match(await page.locator("#jobs .card").first().locator("[data-fav]").textContent(), /已收藏/, "favorite survives reload");
assert.match(await page.locator("#jobs .card").first().locator(".status-menu summary").textContent(), /已投递/, "application state survives reload");

await page.locator("#maintenance > summary").click();
assert.equal(await page.locator("#radar-coverage .stat").count(), 5, "coverage renders after expansion");
assert.ok(await page.locator("#search-log .log-item").count() > 0, "search log renders");
assert.equal(await page.locator("body").evaluate((el) => el.scrollWidth <= window.innerWidth), true, "mobile layout does not overflow");
assert.equal(errors.length, 0, errors.join("\n"));

await browser.close();
console.log("OK: homepage order, city/quick filters, card actions, persistence, maintenance fold and mobile layout passed.");
