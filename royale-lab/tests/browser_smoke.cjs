/* Optional browser QA: Node + playwright-core + installed Chrome. Not needed to run the app. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright-core");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1});
  const failures=[];
  page.on("pageerror",error=>failures.push(error.message));
  const screenshotDir=path.resolve(__dirname,"../screenshots");fs.mkdirSync(screenshotDir,{recursive:true});
  const base=process.env.DASHBOARD_URL || "http://127.0.0.1:8501";
  const response=await page.goto(base,{waitUntil:"networkidle"});assert.equal(response.status(),200);
  await page.waitForSelector("#app:not([hidden])");
  await page.waitForFunction(()=>document.querySelector("#brief-forecast")?._fullLayout);
  assert.equal(await page.locator("#view-briefing .kpi").count(),8);
  await page.screenshot({path:path.join(screenshotDir,"executive-desktop.png")});
  await page.click('[data-page="forecast"]');
  await page.waitForFunction(()=>document.querySelector("#forecast-main")?._fullLayout);
  await page.click('[data-forecast-mode="holdout"]');
  assert.match(await page.locator("#forecast-chart-heading").innerText(),/unseen/);
  assert.equal(await page.locator("#view-forecast .metrics-table tbody tr").count(),3);
  assert.ok(await page.locator("#demand-bridge").count()===1);
  await page.screenshot({path:path.join(screenshotDir,"forecast-desktop.png")});
  await page.click('[data-page="machines"]');
  await page.selectOption("#bank-filter","B-01");
  assert.ok(await page.locator("#view-machines tbody tr").count()>0);
  await page.locator("#view-machines tbody tr").first().click();
  await page.fill("#start-date","2025-06-01");await page.locator("#start-date").dispatchEvent("change");
  await page.selectOption("#zone-filter","High-Limit Room");
  assert.match(await page.locator("#view-machines").innerText(),/No machine observations/);
  await page.click("#reset-filters");
  await page.click('[data-page="guests"]');
  assert.equal(await page.locator("#view-guests .kpi").count(),4);
  await page.selectOption("#guest-start","2025-06");
  await page.selectOption("#guest-tier","Base");
  assert.equal(await page.locator("#view-guests tbody tr").count(),1);
  await page.click('[data-page="budget"]');
  assert.match(await page.locator('#view-budget').innerText(),/one extra technician/);
  await page.locator('#comparison-recovery').evaluate(el=>{el.value=100;el.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.match(await page.locator('#comparison-tech-net').innerText(),/-|−/);
  assert.match(await page.locator("#plan-validation").innerText(),/checks pass/);
  await page.click("#add-plan");
  await page.locator("#uplift").evaluate(el=>{el.value=5;el.dispatchEvent(new Event("input",{bubbles:true}));});
  assert.equal(await page.locator("#uplift-value").innerText(),"5%");
  await page.click("#add-plan");
  assert.match(await page.locator("#plan-validation").innerText(),/duplicate/);
  assert.equal(await page.locator("#uplift-value").innerText(),"5%","Scenario assumptions survive action edits");
  await page.locator('[data-remove-plan="2"]').click();
  assert.match(await page.locator("#plan-validation").innerText(),/checks pass/);
  await page.locator('[data-plan-row="0"] [data-plan-field="quantity"]').fill("2");
  await page.locator('[data-plan-row="0"] [data-plan-field="quantity"]').dispatchEvent("change");
  assert.equal(await page.locator('[data-plan-row="0"] .budget-cost').innerText(),"$2,400");
  await page.locator('[data-plan-row="0"] [data-plan-field="quantity"]').fill("1");
  await page.locator('[data-plan-row="0"] [data-plan-field="quantity"]').dispatchEvent("change");
  await page.click('[data-page="evidence"]');
  for(const filename of ["property_day.csv","machine_day.csv","forecast_july.csv","TABLEAU_GUIDE.md","AI_DISCLOSURE.md"]){
    const asset=await page.request.get(base+"/downloads/"+filename);assert.equal(asset.status(),200,filename);
  }
  await page.locator('#view-evidence [data-evidence="F-01"]').first().click();
  await page.waitForFunction(()=>!document.querySelector("#gemini-status").textContent.includes("Checking"));
  assert.equal(await page.locator("#gemini-explain").isDisabled(),true);
  await page.locator(".close-dialog").click();
  const status=await (await page.request.get(base+"/api/status")).json();assert.equal(status.enabled,false);assert.equal(status.attempts,0);
  await page.setViewportSize({width:390,height:844});
  for(const view of ["briefing","forecast","machines","guests","budget","evidence"]){
    await page.locator(`[data-page="${view}"]`).click();
    await page.waitForTimeout(150);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2),"Mobile overflow in "+view);
  }
  await page.locator('[data-page="briefing"]').click();
  await page.screenshot({path:path.join(screenshotDir,"executive-mobile.png"),fullPage:true});
  await browser.close();
  assert.deepEqual(failures,[],"Browser runtime errors");
  console.log(JSON.stringify({status:"passed",pages:6,desktop:true,mobile:true,downloads:true,gemini:"disabled; zero calls",screenshots:screenshotDir},null,2));
})().catch(error=>{console.error(error);process.exit(1);});
