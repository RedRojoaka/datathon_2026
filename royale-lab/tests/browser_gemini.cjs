/* UI behavior uses simulated responses intercepted in the browser: zero provider calls. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||"playwright-core");
const assert=require("node:assert/strict");
const fs=require("node:fs/promises");
const os=require("node:os");
const path=require("node:path");

(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",headless:true});
  try{
    const base=process.env.DASHBOARD_URL||"http://127.0.0.1:8501";
    const page=await browser.newPage({viewport:{width:1400,height:1000}});
    const errors=[],requests=[];
    page.on("pageerror",error=>errors.push(error.message));
    page.on("request",request=>requests.push(request.url()));
    await page.goto(base+"/ai.html",{waitUntil:"networkidle"});
    await page.waitForSelector('.topic-button');
    assert.equal(await page.locator('.topic-button').count(),4);
    assert.equal(await page.locator('#ai-generate').isDisabled(),true);
    assert.equal(await page.locator('#ai-download').isDisabled(),true);
    assert.equal(await page.locator('#ai-setup').getAttribute('open'),"");
    await page.screenshot({path:path.resolve(__dirname,'../screenshots/gemini-disabled-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    await page.screenshot({path:path.resolve(__dirname,'../screenshots/gemini-disabled-mobile.png'),fullPage:true});
    assert.ok(!requests.some(url=>url.endsWith('/data.json')||url.includes('plotly')),'The lightweight page must not load chart datasets');

    const topics=(await (await page.request.get(base+'/ai_topics.json')).json()).topics;
    const fixture={topics,insights:[],local_server:true,status:{enabled:true,model:'SIMULATED TEST RESPONSE',attempts:0,reserved_usd:0,max_attempts:500,max_total_reserve_usd:1.85,max_request_usd:.0037}};
    let posts=0,generations=0;
    await page.route('**/api/briefing',route=>route.fulfill({json:fixture}));
    await page.route('**/api/status',route=>route.fulfill({json:fixture.status}));
    await page.route('**/api/explain',async route=>{
      posts++;
      const id=route.request().postDataJSON().evidence_id,topic=topics.find(t=>t.id===id);
      if(topic.key==='guests'){
        fixture.status.attempts++;fixture.status.reserved_usd+=.0037;
        return route.fulfill({status:502,json:{error:'Simulated provider failure; no automatic retry.'}});
      }
      let row=fixture.insights.find(r=>r.topic===topic.key);
      if(!row){generations++;fixture.status.attempts++;fixture.status.reserved_usd+=.0037;row={topic:topic.key,title:topic.title,explanation:'SIMULATED TEST ONLY. Evidence F-01. Alternative: demand changes. Limitation: synthetic data.',evidence_ids:topic.sources.join(', '),scope:topic.scope,model:'SIMULATED TEST RESPONSE',generated_at_utc:'2026-11-07T00:00:00Z',context_digest:topic.context_digest,source:'Simulated browser test; not a real model response'};fixture.insights.push(row);}
      return route.fulfill({json:{text:row.explanation,cached:generations<posts,evidence_id:id}});
    });
    await page.goto(base+'/ai.html',{waitUntil:'networkidle'});
    assert.equal(posts,0,'Opening the page must not generate');
    await page.click('#ai-generate');
    await page.waitForFunction(()=>document.querySelector('#ai-answer').textContent.startsWith('SIMULATED TEST ONLY'));
    assert.equal(posts,1);assert.equal(generations,1);
    assert.match(await page.locator('#ai-reserved').innerText(),/0\.0037/);
    assert.equal(await page.locator('#ai-download').isEnabled(),true);
    const downloadEvent=page.waitForEvent('download');await page.click('#ai-download');
    const download=await downloadEvent;
    const csv=await fs.readFile(await download.path(),'utf8');
    assert.ok(csv.includes('evidence_ids')&&csv.includes('F-01')&&csv.includes('SIMULATED TEST ONLY'));
    assert.ok(!csv.includes('GEMINI_API_KEY'));
    await page.click('#ai-generate');
    await page.waitForFunction(()=>!document.querySelector('#ai-generate').disabled);
    assert.equal(generations,1,'Cached reuse must not generate again');
    await page.click('[data-topic="guests"]');await page.click('#ai-generate');
    await page.waitForSelector('#ai-error:not([hidden])');
    assert.match(await page.locator('#ai-error').innerText(),/no automatic retry/);
    assert.equal(posts,3);
    assert.equal(fixture.insights.length,1,'A failed request must not create a briefing');
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({status:'passed',topics:4,desktop:true,mobile:true,real_api_calls:0,checks:['disabled mode','no automatic generation','lightweight loading','simulated generation','cached reuse','CSV export','error handling']},null,2));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
