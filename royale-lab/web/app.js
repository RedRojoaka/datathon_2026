"use strict";
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g, x => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
const money = value => Number.isFinite(Number(value))?Number(value).toLocaleString("en-US", {style:"currency",currency:"USD",maximumFractionDigits:0}):"—";
const compact = value => {
  const v=Number(value), a=Math.abs(v), sign=v<0?"−":"";
  if(!Number.isFinite(v))return "—";
  return sign+"$"+(a>=1e6?(a/1e6).toFixed(2)+"M":a>=1e3?(a/1e3).toFixed(1)+"K":a.toFixed(0));
};
const num = (v,d=0) => Number(v).toLocaleString("en-US",{maximumFractionDigits:d});
const pct = (v,d=1) => Number.isFinite(v)?(v*100).toFixed(d)+"%":"—";
const ratio = (a,b) => b?a/b:NaN;
const date = v => String(v).slice(0,10);
const sum = (rows,key) => rows.reduce((total,r)=>total+(Number(r[key])||0),0);
const days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const palette = ["#3e8074","#b9924a","#607e9a","#a47368","#859752","#897c9d","#405c4d"];
let DATA, DAILY, GUESTS, activePage="briefing", guestCache=null, activeEvidence="F-01", plan=[];
const scenario = {uplift:0,recovery:0,realization:50,extraComp:0};
const comparisonAssumptions = {recovery:0,lift:0};
const selected = {machine:"",guestStart:"2025-01",guestEnd:"2025-06",guestTier:"",guestRegion:"",guestAge:"",forecastMode:"future"};
const titles = {
  briefing:["THE NEXT 30 DAYS","Plan for demand.<br><em>Keep the decision grounded.</em>","A July planning view backed by six months of wagering, availability and player outcomes."],
  forecast:["DEMAND & BUSINESS FORECASTING","Know the baseline.<br><em>Then price the opportunity.</em>","A fixed-origin demand forecast, an honest holdout test, and explicit financial assumptions."],
  machines:["LUCK, LOCATION, OR A LEAK?","Look beyond<br><em>the bottom ten.</em>","Separate payout variation, available exposure and wagering demand before replacing a machine."],
  guests:["TRACKED PLAYER OUTCOMES","Show what players wagered.<br><em>And what they kept.</em>","Tracked play only: player results, concentration and loyalty costs, without double counting."],
  budget:["JULY 1–30 · $100,000 OPERATIONS BUDGET","Make every dollar<br><em>earn its place.</em>","Price up to three action types. Test break-even assumptions before committing the budget."],
  evidence:["REPRODUCIBLE BY DESIGN","Every claim<br><em>has a paper trail.</em>","Methods, accounting checks, alternative explanations, Tableau exports and submission materials."]
};

function unpack(table) {
  const names=table.columns, dictionaries=table.dictionaries;
  return table.rows.map(row=>Object.fromEntries(names.map((key,i)=>[key,dictionaries[key]?dictionaries[key][row[i]]:row[i]])));
}
function metric(label,value,note,highlight=false) {
  return `<article class="kpi ${highlight?"highlight":""}"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-note">${note}</div></article>`;
}
function chartCard(id,title,subtitle,tag="",large=false) {
  return `<article class="card"><div class="card-head"><div><h2>${title}</h2><p class="card-subtitle">${subtitle}</p></div>${tag?`<span class="pill">${tag}</span>`:""}</div><div id="${id}" class="chart ${large?"large":""}" role="img" aria-label="${esc(title)}"></div></article>`;
}
function plot(id,traces,layout={}) {
  const node=document.getElementById(id); if(!node)return;
  const base={paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:{family:"Arial, sans-serif",size:10,color:"#68766e"},
    margin:{l:58,r:16,t:22,b:45},colorway:palette,hovermode:"closest",
    xaxis:{gridcolor:"#ebeee2",zeroline:false,linecolor:"#dde2d5",automargin:true},
    yaxis:{gridcolor:"#ebeee2",zeroline:false,automargin:true},
    legend:{orientation:"h",x:0,y:1.14,font:{size:9}},...layout};
  if(layout.xaxis)base.xaxis={gridcolor:"#ebeee2",zeroline:false,automargin:true,...layout.xaxis};
  if(layout.yaxis)base.yaxis={gridcolor:"#ebeee2",zeroline:false,automargin:true,...layout.yaxis};
  Plotly.react(node,traces,base,{responsive:true,displaylogo:false,modeBarButtonsToRemove:["lasso2d","select2d","autoScale2d"],toImageButtonOptions:{format:"png",scale:2}});
}
function bandTraces(rows,xKey,lowKey,highKey,name="Nominal 90% daily demand band") {
  return [{x:rows.map(r=>date(r[xKey])),y:rows.map(r=>r[lowKey]),mode:"lines",line:{width:0},showlegend:false,hoverinfo:"skip"},
          {x:rows.map(r=>date(r[xKey])),y:rows.map(r=>r[highKey]),mode:"lines",line:{width:0},fill:"tonexty",fillcolor:"rgba(62,128,116,.13)",name,hoverinfo:"skip"}];
}
function grouped(rows,key) {
  const groups=new Map();for(const row of rows){const name=row[key]??"Unknown";if(!groups.has(name))groups.set(name,[]);groups.get(name).push(row);}return groups;
}
function floorRows() {
  const start=$("#start-date").value,end=$("#end-date").value,zone=$("#zone-filter").value,bank=$("#bank-filter").value,maker=$("#maker-filter").value;
  return DAILY.filter(r=>r.gaming_date>=start&&r.gaming_date<=end&&(!zone||r.zone_name===zone)&&(!bank||r.bank_id===bank)&&(!maker||r.manufacturer===maker));
}
function floorAggregates(rows) {
  const cols=["coin_in_usd","payout_usd","house_win_usd","theo_usd","available_hours","scheduled_hours","occupied_hours","downtime_hours","faults_opened","payout_variance_usd2","contribution_after_supplied_costs_usd","expected_contribution_usd","opportunity_coin_in_usd","opportunity_theo_usd"];
  return [...grouped(rows,"machine_id")].map(([machine_id,group])=>{
    const r={...group[group.length-1],machine_id,active_days:new Set(group.map(g=>g.gaming_date)).size};
    for(const c of cols)r[c]=sum(group,c);
    r.availability=ratio(r.available_hours,r.scheduled_hours);
    r.theo_rate=ratio(r.theo_usd,r.available_hours);
    r.win_rate=ratio(r.house_win_usd,r.available_hours);
    r.coin_rate=ratio(r.coin_in_usd,r.available_hours);
    r.luck_residual_usd=r.house_win_usd-r.theo_usd;
    r.luck_z=ratio(r.luck_residual_usd,Math.sqrt(r.payout_variance_usd2));return r;
  });
}
function setPage(page) {
  if(!titles[page])page="briefing";activePage=page;
  document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id==="view-"+page));
  document.querySelectorAll(".nav-item").forEach(v=>v.classList.toggle("active",v.dataset.page===page));
  $("#breadcrumb").textContent=$(`[data-page="${page}"]`).textContent.trim().replace(/^\d+\s*/,"");
  $("#page-kicker").textContent=titles[page][0];$("#page-title").innerHTML=titles[page][1];$("#page-description").textContent=titles[page][2];
  $("#floor-filters").hidden=!["briefing","machines"].includes(page);
  history.replaceState(null,"","#"+page);render();$("#live-status").textContent=$("#breadcrumb").textContent+" loaded";
}
function render() {
  if(!DATA)return;
  const start=$("#start-date").value,end=$("#end-date").value;
  $("#filter-note").textContent=start>end?"Choose a start date before the end date.":"Floor filters affect historical floor views. Forecasts remain property-wide.";
  ({briefing:renderBriefing,forecast:renderForecast,machines:renderMachines,guests:renderGuests,budget:renderBudget,evidence:renderEvidence}[activePage])();
}

function forecastPlot(id,fullHistory=false) {
  const actual=fullHistory?DATA.property:DATA.property.filter(r=>date(r.gaming_date)>="2025-05-01");
  plot(id,[...bandTraces(DATA.future,"gaming_date","lower_90_usd","upper_90_usd"),
    {x:actual.map(r=>date(r.gaming_date)),y:actual.map(r=>r.coin_in_usd),name:"Observed wagers",mode:"lines",line:{color:"#7d8c80",width:1.6}},
    {x:DATA.future.map(r=>date(r.gaming_date)),y:DATA.future.map(r=>r.forecast_coin_in_usd),name:"July baseline forecast",mode:"lines",line:{color:"#3e8074",width:2.5}}],
    {yaxis:{tickprefix:"$",tickformat:".2s",title:{text:"Daily wagers",font:{size:10}}},xaxis:{type:"date"},hovermode:"x unified",
     shapes:[{type:"line",x0:"2025-07-01",x1:"2025-07-01",y0:0,y1:1,yref:"paper",line:{color:"#b9924a",width:1,dash:"dot"}}]});
}
function renderBriefing() {
  const f=DATA.forecast,future=DATA.future,sel=f.metrics.find(m=>m.selected),base=f.metrics.find(m=>m.model==="mean");
  const reduction=1-sel.test_mae_usd/base.test_mae_usd;
  const rows=floorRows();
  const monthLatest=DATA.monthly.at(-1),prev=DATA.monthly.at(-2);
  const dailyChange=monthLatest.daily_coin_in_usd/prev.daily_coin_in_usd-1;
  const forecastsByDay=[...grouped(future.map(r=>({...r,weekday:days[(new Date(date(r.gaming_date)+"T12:00:00Z").getUTCDay()+6)%7]})),"weekday")].map(([name,rs])=>({name,value:sum(rs,"forecast_coin_in_usd")/rs.length})).sort((a,b)=>b.value-a.value);
  $("#view-briefing").innerHTML=`
    <div class="kpi-grid">${metric("July baseline wagers",compact(sum(future,"forecast_coin_in_usd")),"July 1–30 · property-wide",true)}${metric("Expected contribution",compact(sum(future,"expected_contribution_usd")),"After supplied costs · June mix assumed")}${metric("Holdout forecast error",compact(sel.test_mae_usd),`${pct(Math.abs(reduction))} ${reduction>=0?"lower":"higher"} MAE than constant mean`)}${metric("Budget available","$100,000","Fictional operating budget · ≤3 action types")}</div>
    <div class="grid-two">${chartCard("brief-forecast","Demand is the planning baseline","Observed May–June and the next 30 days","PROPERTY-WIDE")}
    <article class="card"><div class="eyebrow">EXECUTIVE READOUT</div><h2 style="font-family:Georgia,serif;font-size:23px;margin-top:12px">Three things to take<br>into the next shift.</h2><ol class="decision-list">
      <li><span class="number">1</span><div><strong>Plan coverage around ${esc(forecastsByDay[0].name)} and ${esc(forecastsByDay[1].name)}.</strong><p>These are the forecast's strongest weekdays. Forecast demand supports scheduling; it does not prove more staffing creates more wagers.</p><button class="text-link" data-go="forecast">Open forecast & validation ↗</button></div></li>
      <li><span class="number">2</span><div><strong>June daily wagers ${dailyChange<0?"fell":"rose"} ${pct(Math.abs(dailyChange))} from May.</strong><p>Compare per day rather than monthly totals. Timing, exposure and events remain competing explanations.</p><button class="text-link" data-evidence="F-01">Trace the evidence ↗</button></div></li>
      <li><span class="number">3</span><div><strong>Price a promotion before promising its return.</strong><p>A promotion costs $15,000 and has a 14-day lead. Use the budget lab to calculate the additional wagering needed to break even.</p><button class="text-link" data-go="budget">Explore the budget ↗</button></div></li></ol></article></div>
    <p class="note" style="margin-top:-9px;margin-bottom:22px">${esc(f.interval_note)}</p>
    <div class="scope-note">Historical floor snapshot below: <strong>${esc($("#start-date").value)} → ${esc($("#end-date").value)}</strong>. ${num(new Set(rows.map(r=>r.machine_id)).size)} machines in the selected scope. Future forecast above remains property-wide.</div>
    <div class="kpi-grid">${metric("Historical wagers",compact(sum(rows,"coin_in_usd")),"All play · replayed winnings count as wagers")}${metric("Actual / expected house win",compact(sum(rows,"house_win_usd")),`${compact(sum(rows,"theo_usd"))} expected at configured RTP`)}${metric("Availability",pct(ratio(sum(rows,"available_hours"),sum(rows,"scheduled_hours"))),`${num(sum(rows,"downtime_hours"))} unavailable machine-hours`)}${metric("Machine contribution",compact(sum(rows,"contribution_after_supplied_costs_usd")),"Machine costs only · excludes property F&B / labor")}</div>
    <div class="grid-equal">${chartCard("brief-monthly","What the floor retained","Property totals · supplied costs only","GLOBAL HISTORY")}${chartCard("brief-zone","Where demand meets availability","Selected scope · theoretical win per available hour","EXPOSURE-ADJUSTED")}</div>
    <div class="callout section-space"><strong>Working recommendation: forecast first, then test the intervention.</strong><p>Use baseline demand to time existing coverage. Validate any additional staffing or promotional spending with a control group and contribution measurement. Payout luck is not a demand forecast.</p><button class="text-link" data-evidence="F-02">Why this is an estimate ↗</button></div>`;
  forecastPlot("brief-forecast");
  const m=DATA.monthly;
  plot("brief-monthly",[{x:m.map(r=>r.month),y:m.map(r=>r.house_win_usd),type:"bar",name:"House win",marker:{color:"#d2d9c7"}},
    {x:m.map(r=>r.month),y:m.map(r=>r.contribution_after_supplied_costs_usd),type:"bar",name:"Property contribution",marker:{color:"#3e8074"}}],{barmode:"group",yaxis:{tickprefix:"$",tickformat:".2s"}});
  const zones=[...grouped(rows,"zone_name")].map(([name,rs])=>({name,rate:ratio(sum(rs,"theo_usd"),sum(rs,"available_hours"))})).sort((a,b)=>a.rate-b.rate);
  plot("brief-zone",[{x:zones.map(r=>r.rate),y:zones.map(r=>r.name),type:"bar",orientation:"h",marker:{color:zones.map((_,i)=>i===zones.length-1?"#b9924a":"#3e8074")},hovertemplate:"%{y}<br>Expected win / available hour: $%{x:.2f}<extra></extra>"}],{margin:{l:118,r:15,t:10,b:35},xaxis:{tickprefix:"$"}});
}

function renderForecast() {
  const f=DATA.forecast,chosen=f.metrics.find(m=>m.selected),baseline=f.metrics.find(m=>m.model==="mean"),future=DATA.future;
  $("#view-forecast").innerHTML=`<div class="scope-note"><strong>Property-wide model.</strong> Training: Jan–Apr. Model selection: March and April rolling-origin folds. Final untouched test: May–June. Operational refit: Jan–June → July 1–30. Floor filters do not change this model.</div>
    <div class="kpi-grid">${metric("Selected model",esc(f.selected_label),"Selected before the May–June holdout",true)}${metric("May–June MAE",compact(chosen.test_mae_usd),`Constant-mean baseline: ${compact(baseline.test_mae_usd)}`)}${metric("Daily band coverage",pct(f.test_coverage_90),"Observed holdout coverage · nominal 90% band")}${metric("July expected house win",compact(sum(future,"expected_theo_usd")),`${pct(f.assumed_theo_hold,2)} June expected hold assumed`)}</div>
    <article class="card"><div class="card-head"><div><h2 id="forecast-chart-heading">${selected.forecastMode==="future"?"July operating outlook":"Did the model predict unseen demand?"}</h2><p class="card-subtitle">${selected.forecastMode==="future"?"Observed history and a refit forecast; future actuals are unavailable.":"All May–June predictions were made using only data through April 30."}</p></div><div class="tabs"><button data-forecast-mode="future" class="${selected.forecastMode==="future"?"active":""}">July outlook</button><button data-forecast-mode="holdout" class="${selected.forecastMode==="holdout"?"active":""}">Holdout test</button></div></div><div id="forecast-main" class="chart large" role="img" aria-label="Demand forecast and prediction bands"></div><p class="note">${esc(f.interval_note)}</p></article>
    <div class="grid-equal">${chartCard("forecast-weekday","Which days need the most coverage?","Average July forecast by weekday · demand, not required headcount")}
    <article class="card"><div class="card-head"><div><h2>Wagers → expected retained contribution</h2><p class="card-subtitle">July 1–30, same game mix and daily costs as June</p></div><span class="pill gold">ASSUMPTIONS</span></div>
    <div class="stat-row"><span>Forecast wagers</span><strong>${money(sum(future,"forecast_coin_in_usd"))}</strong></div><div class="stat-row"><span>Expected house win (${pct(f.assumed_theo_hold,2)})</span><strong>${money(sum(future,"expected_theo_usd"))}</strong></div><div class="stat-row"><span>Assumed food & beverage margin</span><strong>+ ${money(sum(future,"assumed_fnb_margin_usd"))}</strong></div><div class="stat-row"><span>Assumed machine + technician costs</span><strong>− ${money(sum(future,"assumed_supplied_costs_usd"))}</strong></div><div class="stat-row"><span>Expected contribution after supplied costs</span><strong>${money(sum(future,"expected_contribution_usd"))}</strong></div><p class="note">Comps are already inside food & beverage cost of goods. Actual payouts will vary. Rent, taxes, depreciation and other missing costs are excluded; this is not a full profit forecast.</p><button class="text-link" data-evidence="F-02">Inspect assumptions & limitations ↗</button></article></div>
    <article class="card"><div class="card-head"><div><h2>Model comparison</h2><p class="card-subtitle">Lower MAE is better. Model selection uses the pre-May column, not the final test column.</p></div><a class="button subtle" href="downloads/forecast_metrics.csv" download>Download validation</a></div><div class="table-wrap"><table class="metrics-table"><thead><tr><th>Model</th><th class="num">Pre-May CV MAE</th><th class="num">May–June MAE</th><th class="num">May–June RMSE</th><th class="num">Bias (prediction − actual)</th></tr></thead><tbody>${f.metrics.map(m=>`<tr class="${m.selected?"selected":""}"><td>${esc(m.label)} ${m.selected?'<span class="pill">SELECTED</span>':""}</td><td class="num">${money(m.cv_mae_usd)}</td><td class="num">${money(m.test_mae_usd)}</td><td class="num">${money(m.test_rmse_usd)}</td><td class="num">${money(m.test_bias_usd)}</td></tr>`).join("")}</tbody></table></div><p class="note">MAE = average absolute dollar error. RMSE penalizes large misses. Positive bias means overprediction. ${esc(f.limitations)}</p></article>
    <div class="callout"><strong>How this informs a decision</strong><p>Schedule existing coverage around forecast peaks. A promotion must generate incremental contribution beyond demand that would have happened anyway. The model does not estimate promotion lift or prove a staffing effect.</p><button class="text-link" data-go="budget">Calculate promotion and staffing break-even ↗</button></div>`;
  const bridge=DATA.demand_bridge;
  $("#view-forecast").insertAdjacentHTML("beforeend",`<div class="grid-equal">${chartCard("demand-bridge","What changed from May to June?",`${money(bridge.start_daily_coin_in_usd)} → ${money(bridge.end_daily_coin_in_usd)} in wagers per day`,"ACCOUNTING BRIDGE")}
    <article class="card"><h2>Separate the mechanism from the cause</h2><div class="stat-row"><span>Available machine-hours per day</span><strong>${money(bridge.exposure_effect_usd)} / day</strong></div><div class="stat-row"><span>Occupied share of available hours</span><strong>${money(bridge.occupancy_effect_usd)} / day</strong></div><div class="stat-row"><span>Wagering per occupied hour</span><strong>${money(bridge.intensity_effect_usd)} / day</strong></div><p class="note">The three components reconcile exactly to the daily wagering change. Their allocation depends on the stated sequence. They do not identify why utilization or wagering intensity changed.</p><p class="note"><strong>Competing explanations:</strong> weekday mix, events, guest/game mix and changing demand. ${DATA.closures.length?`A walkway closure is documented from ${esc(DATA.closures[0].closed_from_utc)} through ${esc(DATA.closures[0].closed_to_utc)}; that earlier event alone does not establish the cause of May–June changes.`:""}</p><button class="text-link" data-evidence="F-03">Trace the decomposition ↗</button></article></div>
    <article class="card"><h2>Event context, without claiming event lift</h2><p class="card-subtitle">Supplied event calendar. These events are not regressors in the selected weekday model.</p><div class="table-wrap"><table><thead><tr><th>Event</th><th>Start</th><th>End</th><th>Scope</th><th>Announced</th></tr></thead><tbody>${DATA.events.map(e=>`<tr><td>${esc(e.name)}</td><td>${esc(e.start_date)}</td><td>${esc(e.end_date)}</td><td>${esc(e.local_scope)}</td><td>${esc(e.announced_date)}</td></tr>`).join("")}</tbody></table></div><p class="note">Coinciding events and demand changes are associations. Without a credible counterfactual, an event's incremental wagering or contribution is unknown.</p></article>`);
  plot("demand-bridge",[{type:"waterfall",measure:["relative","relative","relative","total"],x:["Exposure","Occupancy","Wager intensity","Daily change"],y:[bridge.exposure_effect_usd,bridge.occupancy_effect_usd,bridge.intensity_effect_usd,0],connector:{line:{color:"#c7cebd"}},increasing:{marker:{color:"#3e8074"}},decreasing:{marker:{color:"#b9924a"}},totals:{marker:{color:"#153c35"}},hovertemplate:"%{x}: $%{y:,.0f}/day<extra></extra>"}],{showlegend:false,yaxis:{tickprefix:"$",tickformat:".2s"}});
  if(selected.forecastMode==="future")forecastPlot("forecast-main",true);
  else{
    const test=DATA.holdout.filter(r=>r.model===f.selected_model),mean=DATA.holdout.filter(r=>r.model==="mean");
    plot("forecast-main",[...bandTraces(test,"gaming_date","lower_90_usd","upper_90_usd"),
      {x:test.map(r=>date(r.gaming_date)),y:test.map(r=>r.actual_usd),name:"Unseen actual wagers",mode:"lines",line:{color:"#7d8c80",width:1.7}},
      {x:test.map(r=>date(r.gaming_date)),y:test.map(r=>r.forecast_usd),name:f.selected_label,mode:"lines",line:{color:"#3e8074",width:2}},
      {x:mean.map(r=>date(r.gaming_date)),y:mean.map(r=>r.forecast_usd),name:"Constant mean baseline",mode:"lines",line:{color:"#b9924a",width:1.5,dash:"dot"}}],{hovermode:"x unified",xaxis:{type:"date"},yaxis:{tickprefix:"$",tickformat:".2s"}});
  }
  const byDay=days.map((name,i)=>{const rs=future.filter(r=>(new Date(date(r.gaming_date)+"T12:00:00Z").getUTCDay()+6)%7===i);return {name,value:sum(rs,"forecast_coin_in_usd")/rs.length};});
  plot("forecast-weekday",[{x:days,y:byDay.map(r=>r.value),type:"bar",marker:{color:byDay.map(r=>r.value>=Math.max(...byDay.map(x=>x.value))*.95?"#b9924a":"#3e8074")},hovertemplate:"%{x}<br>Average forecast wagers: $%{y:,.0f}<extra></extra>"}],{yaxis:{tickprefix:"$",tickformat:".2s"}});
}

function renderMachines() {
  const rows=floorRows(),machines=floorAggregates(rows),ordered=[...machines].sort((a,b)=>a.house_win_usd-b.house_win_usd);
  if(!rows.length){$("#view-machines").innerHTML='<div class="card empty">No machine observations match these filters.</div>';return;}
  if(!machines.some(r=>r.machine_id===selected.machine))selected.machine=ordered[0].machine_id;
  const chosen=machines.find(r=>r.machine_id===selected.machine),series=rows.filter(r=>r.machine_id===selected.machine).sort((a,b)=>a.gaming_date.localeCompare(b.gaming_date));
  $("#view-machines").innerHTML=`<div class="kpi-grid">${metric("Machines in scope",num(machines.length),`${num(rows.length)} active machine-days`,true)}${metric("Expected win / available hour",money(ratio(sum(rows,"theo_usd"),sum(rows,"available_hours"))),"Ratio of sums · exposure-adjusted")}${metric("Unavailability",num(sum(rows,"downtime_hours"))+" h",`${pct(1-ratio(sum(rows,"available_hours"),sum(rows,"scheduled_hours")))} of scheduled exposure`)}${metric("Gross downtime opportunity",compact(sum(rows,"opportunity_theo_usd")),"Expected-win scenario · not observed lost revenue")}</div>
    <div class="grid-equal">${chartCard("machine-scatter","Weak demand or unlucky payouts?","Each point is one machine. Click to inspect its history.","SELECTED SCOPE")}${chartCard("machine-downtime","Where availability was lost","Unscheduled + scheduled downtime by zone")}</div>
    <div class="callout warn"><strong>Do not equate a low total with a bad machine.</strong><p>The scatter adjusts for available hours and distinguishes actual from theoretical house win. Location, game mix and time on the floor still matter. Downtime opportunity assumes demand would be recovered without shifting from another machine.</p></div>
    <article class="card"><div class="card-head"><div><h2>The manager's low-earner list, with context</h2><p class="card-subtitle">Sorted by actual house win; select any row for its history. Export contains all machines.</p></div><a class="button subtle" href="downloads/machine_summary.csv" download>Full-period audit</a></div><div class="table-wrap"><table><thead><tr><th>Machine</th><th>Latest zone in scope</th><th class="num">House win</th><th class="num">Theo</th><th class="num">Theo / avail. hour</th><th class="num">Availability</th><th class="num">Residual z</th><th class="num">Active days</th></tr></thead><tbody>${ordered.slice(0,30).map(r=>`<tr class="clickable" data-machine="${esc(r.machine_id)}"><td>${esc(r.machine_id)}${r.machine_id===selected.machine?" ◀":""}</td><td>${esc(r.zone_name)}</td><td class="num">${money(r.house_win_usd)}</td><td class="num">${money(r.theo_usd)}</td><td class="num">${money(r.theo_rate)}</td><td class="num">${pct(r.availability)}</td><td class="num ${r.luck_z < -3?"negative":""}">${r.luck_z.toFixed(2)}</td><td class="num">${r.active_days}</td></tr>`).join("")}</tbody></table></div><p class="note">Residual z = (actual house win − theo) / configured-model standard error. Filtered values are exploratory. The full-period export includes Bonferroni-adjusted screening across all 310 machines. Latest location labels do not imply a machine stayed there throughout the period.</p></article>
    <article class="card"><div class="card-head"><div><h2>${esc(chosen.machine_id)} · ${esc(chosen.theme)}</h2><p class="card-subtitle">Cumulative actual and expected win, reset at the start of the selected period</p></div><label class="control">Inspect machine <select id="machine-select">${[...machines].sort((a,b)=>a.machine_id.localeCompare(b.machine_id)).map(r=>`<option ${r.machine_id===selected.machine?"selected":""}>${esc(r.machine_id)}</option>`).join("")}</select></label></div><div id="machine-series" class="chart"></div><p class="note"><strong>Alternative explanation:</strong> payout luck, low exposure, location, game mix or an unverified configuration difference. A payout signal warrants inspection, not an accusation or automatic replacement. <button class="text-link" data-evidence="M-01">Full-period statistical evidence ↗</button></p></article>`;
  const traces=[...grouped(machines,"zone_name")].map(([name,rs],i)=>({x:rs.map(r=>r.theo_rate),y:rs.map(r=>r.win_rate),customdata:rs.map(r=>[r.machine_id,r.availability,r.active_days]),text:rs.map(r=>r.machine_id),name,type:"scatter",mode:"markers",marker:{size:rs.map(r=>5+Math.sqrt(r.coin_in_usd/Math.max(...machines.map(x=>x.coin_in_usd)))*10),color:palette[i%palette.length],opacity:.75},hovertemplate:"%{customdata[0]}<br>Theo / available hour: $%{x:.2f}<br>Actual win / available hour: $%{y:.2f}<br>Availability: %{customdata[1]:.1%}<extra>%{fullData.name}</extra>"}));
  const max=Math.max(...machines.map(r=>Math.max(r.theo_rate,r.win_rate)))*1.03;
  plot("machine-scatter",traces,{showlegend:false,xaxis:{title:{text:"Expected win / available hour",font:{size:10}},tickprefix:"$"},yaxis:{title:{text:"Actual win / available hour",font:{size:10}},tickprefix:"$"},shapes:[{type:"line",x0:0,y0:0,x1:max,y1:max,line:{color:"#b9924a",width:1,dash:"dot"}}]});
  $("#machine-scatter").on("plotly_click",event=>{selected.machine=event.points[0].customdata[0];renderMachines();});
  const zones=[...grouped(rows,"zone_name")].map(([name,rs])=>({name,hours:sum(rs,"downtime_hours")})).sort((a,b)=>a.hours-b.hours);
  plot("machine-downtime",[{x:zones.map(r=>r.hours),y:zones.map(r=>r.name),type:"bar",orientation:"h",marker:{color:"#b9924a"},hovertemplate:"%{y}<br>%{x:,.1f} unavailable hours<extra></extra>"}],{margin:{l:117,r:15,t:10,b:35},xaxis:{title:{text:"Unavailable machine-hours",font:{size:10}}}});
  let actual=0,theo=0;const a=[],t=[];for(const row of series){actual+=row.house_win_usd;theo+=row.theo_usd;a.push(actual);t.push(theo);}
  plot("machine-series",[{x:series.map(r=>r.gaming_date),y:a,name:"Actual house win",mode:"lines",line:{color:"#3e8074",width:2}},
    {x:series.map(r=>r.gaming_date),y:t,name:"Configured expected win",mode:"lines",line:{color:"#b9924a",width:2,dash:"dot"}}],{hovermode:"x unified",xaxis:{type:"date"},yaxis:{tickprefix:"$",tickformat:".2s"}});
}

function guestData() {
  const key=JSON.stringify([selected.guestStart,selected.guestEnd,selected.guestTier,selected.guestRegion,selected.guestAge]);
  if(guestCache?.key===key)return guestCache;
  const rows=GUESTS.filter(r=>r.period_month>=selected.guestStart&&r.period_month<=selected.guestEnd&&(!selected.guestTier||r.opening_tier===selected.guestTier)&&(!selected.guestRegion||r.home_region===selected.guestRegion)&&(!selected.guestAge||r.age_band===selected.guestAge));
  const people=new Map();for(const r of rows){if(!people.has(r.player_key))people.set(r.player_key,{coin:0,payout:0,net:0});const p=people.get(r.player_key);p.coin+=r.tracked_coin_in_usd;p.payout+=r.tracked_payout_usd;p.net+=r.tracked_net_usd;}
  const persons=[...people.values()],sorted=[...persons].sort((a,b)=>b.coin-a.coin),total=persons.reduce((a,r)=>a+r.coin,0);
  guestCache={key,rows,persons,sorted,total};return guestCache;
}
function options(values,current,allLabel){return `<option value="">${allLabel}</option>`+values.map(v=>`<option value="${esc(v)}" ${v===current?"selected":""}>${esc(v)}</option>`).join("");}
function renderGuests() {
  const g=guestData(),rows=g.rows,people=g.persons,n=people.length;
  const topShare=ratio(sum(g.sorted.slice(0,Math.ceil(n*.01)),"coin"),g.total);
  $("#view-guests").innerHTML=`<div class="scope-note"><strong>Complete-month guest analysis.</strong> Guests can visit many machines and zones; floor filters do not apply. Player net = payouts − wagers. Cohort labels use the player's opening tier, not future tier changes.</div>
    <div class="control"><label>First month<select id="guest-start">${DATA.meta.months.map(m=>`<option ${m===selected.guestStart?"selected":""}>${m}</option>`).join("")}</select></label><label>Last month<select id="guest-end">${DATA.meta.months.map(m=>`<option ${m===selected.guestEnd?"selected":""}>${m}</option>`).join("")}</select></label><label>Opening tier<select id="guest-tier">${options([...new Set(GUESTS.map(r=>r.opening_tier))].sort(),selected.guestTier,"All tiers")}</select></label><label>Home region<select id="guest-region">${options([...new Set(GUESTS.map(r=>r.home_region))].sort(),selected.guestRegion,"All regions")}</select></label><label>Age band<select id="guest-age">${options([...new Set(GUESTS.map(r=>r.age_band))].sort(),selected.guestAge,"All age bands")}</select></label></div>
    <div class="kpi-grid">${metric("Unique tracked players",num(n),"Deduplicated across selected months",true)}${metric("Tracked player gaming net",compact(sum(rows,"tracked_net_usd")),`${compact(sum(rows,"tracked_payout_usd"))} payouts − ${compact(g.total)} wagers`)}${metric("Players ahead",pct(ratio(people.filter(r=>r.net>0).length,n)),"Positive cumulative gaming net in selected months")}${metric("Top 1% share of wagers",pct(topShare),"Wager concentration · tracked players only")}</div>
    <div class="grid-equal">${chartCard("guest-outcomes","What tracked players received back","Selected cohort totals · wagers include replayed winnings")}${chartCard("guest-concentration","How concentrated is tracked wagering?","Cumulative wagers, players ordered from highest to lowest wagers")}</div>
    <div class="grid-equal">${chartCard("guest-comps","Did comp reinvestment change?","Selected cohort · redeemed economic cost ÷ theo")}${chartCard("guest-net","Distribution of player gaming results","Cumulative player net over selected complete months")}</div>
    <article class="card"><div class="card-head"><div><h2>Cohort evidence by month</h2><p class="card-subtitle">Monetary totals are additive; distinct player counts must be recomputed across months.</p></div><button class="text-link" data-evidence="G-01">Definitions & limitations ↗</button></div><div class="table-wrap"><table><thead><tr><th>Month</th><th class="num">Tracked wagers</th><th class="num">Payouts</th><th class="num">Player net</th><th class="num">Theo</th><th class="num">Comp cost</th><th class="num">Comp / theo</th></tr></thead><tbody>${[...grouped(rows,"period_month")].sort(([a],[b])=>a.localeCompare(b)).map(([month,rs])=>`<tr><td>${month}</td><td class="num">${money(sum(rs,"tracked_coin_in_usd"))}</td><td class="num">${money(sum(rs,"tracked_payout_usd"))}</td><td class="num">${money(sum(rs,"tracked_net_usd"))}</td><td class="num">${money(sum(rs,"theo_usd"))}</td><td class="num">${money(sum(rs,"comp_cost_usd"))}</td><td class="num">${pct(ratio(sum(rs,"comp_cost_usd"),sum(rs,"theo_usd")),2)}</td></tr>`).join("")}</tbody></table></div><p class="note">Comp costs are already in linked food & beverage cost of goods. Do not subtract them again. Changes in redemption timing or guest mix are alternatives to a policy effect. A payout is not a player's net gain.</p></article>
    <div class="callout"><strong>Use concentration to understand exposure and uncertainty.</strong><p>These data cover loyalty-card activity only. They do not describe every guest or justify promotions aimed at making heavy losers gamble more. A controlled, capped promotion can measure incremental visits and contribution without targeting individual losses.</p></div>`;
  plot("guest-outcomes",[{x:["Wagered","Paid back","Player net"],y:[g.total,sum(rows,"tracked_payout_usd"),sum(rows,"tracked_net_usd")],type:"bar",marker:{color:["#b9924a","#3e8074","#b9594a"]},hovertemplate:"%{x}: $%{y:,.0f}<extra></extra>"}],{yaxis:{tickprefix:"$",tickformat:".2s"}});
  let cumulative=0;const points=[{x:0,y:0}];g.sorted.forEach((p,i)=>{cumulative+=p.coin;if(i%Math.max(1,Math.floor(n/200))===0||i===n-1)points.push({x:(i+1)/n,y:ratio(cumulative,g.total)});});
  plot("guest-concentration",[{x:points.map(r=>r.x),y:points.map(r=>r.y),mode:"lines",fill:"tozeroy",fillcolor:"rgba(62,128,116,.09)",line:{color:"#3e8074",width:2},name:"Observed concentration",hovertemplate:"Top %{x:.1%} of players<br>%{y:.1%} of wagers<extra></extra>"},{x:[0,1],y:[0,1],mode:"lines",line:{color:"#b9924a",dash:"dot",width:1},name:"Equal-share reference",hoverinfo:"skip"}],{xaxis:{tickformat:".0%",title:{text:"Share of players, largest wagers first",font:{size:10}}},yaxis:{tickformat:".0%",range:[0,1]}});
  const months=[...grouped(rows,"period_month")].sort(([a],[b])=>a.localeCompare(b));
  plot("guest-comps",[{x:months.map(([m])=>m),y:months.map(([,rs])=>sum(rs,"comp_cost_usd")),type:"bar",name:"Comp cost",marker:{color:"#d7ddc9"},yaxis:"y"},{x:months.map(([m])=>m),y:months.map(([,rs])=>ratio(sum(rs,"comp_cost_usd"),sum(rs,"theo_usd"))),mode:"lines+markers",name:"Comp / theo",line:{color:"#3e8074",width:2},yaxis:"y2"}],{margin:{l:60,r:50,t:25,b:40},yaxis:{tickprefix:"$",tickformat:".2s"},yaxis2:{overlaying:"y",side:"right",tickformat:".1%",showgrid:false,zeroline:false}});
  const bins=[{name:"< −$5k",min:-Infinity,max:-5000},{name:"−$5k to −$1k",min:-5000,max:-1000},{name:"−$1k to $0",min:-1000,max:0},{name:"Exactly $0",min:0,max:0},{name:"$0 to $1k",min:0,max:1000},{name:"$1k to $5k",min:1000,max:5000},{name:"> $5k",min:5000,max:Infinity}];
  const counts=bins.map((b,i)=>people.filter(p=>i===3?p.net===0:i===4?p.net>0&&p.net<1000:p.net>=b.min&&p.net<b.max).length);
  plot("guest-net",[{x:bins.map(b=>b.name),y:counts,type:"bar",marker:{color:bins.map((_,i)=>i<3?"#b9924a":"#3e8074")},hovertemplate:"%{x}<br>%{y:,} players<extra></extra>"}],{xaxis:{tickangle:-18},yaxis:{title:{text:"Distinct players",font:{size:10}}}});
}

function costFor(action,quantity){return quantity*(action.unit_cost_cents+action.recurring_cost_cents_per_day*Math.max(0,30-action.lead_days))/100;}
function validatePlan() {
  const errors=[],ids=plan.filter(p=>p.quantity>0&&p.id!=="A-HOLD").map(p=>p.id);let total=0;const used=new Set();
  if(ids.length>3)errors.push("At most three funded action types are allowed.");
  if(new Set(ids).size!==ids.length)errors.push("Combine duplicate action types into one row.");
  if(ids.includes("A-COMP-PILOT")&&ids.includes("A-COMP-CHANGE"))errors.push("The comp pilot and floor-wide comp change cannot be combined.");
  for(const p of plan){const a=DATA.actions.find(a=>a.action_type_id===p.id);if(!Number.isInteger(p.quantity)||p.quantity<0||p.quantity>a.quantity_limit){errors.push(`${a.name}: quantity must be 0–${a.quantity_limit}.`);continue;}total+=costFor(a,p.quantity);if(!p.quantity)continue;
    const targets=p.targets.split(",").map(t=>t.trim()).filter(Boolean);
    if(["machine","bank","zone","manufacturer","technician_shift"].includes(a.unit)){
      if(new Set(targets).size!==p.quantity)errors.push(`${a.name}: specify ${p.quantity} distinct ${a.unit} target(s), separated by commas.`);
      const valid=a.unit==="machine"?new Set(DAILY.filter(r=>r.gaming_date==="2025-06-30").map(r=>r.machine_id)):a.unit==="bank"?new Set(DAILY.map(r=>r.bank_id)):a.unit==="manufacturer"?new Set(DAILY.map(r=>r.manufacturer)):a.unit==="zone"?new Set(DAILY.map(r=>r.zone_name)):new Set(["day","swing","grave"]);
      if(targets.some(t=>!valid.has(t)))errors.push(`${a.name}: a target is not in the observed data${a.unit==="technician_shift"?" (use day, swing, grave)":""}.`);
    }
    if(a.incompatibility_group==="same_machine"){
      const expanded=a.unit==="bank"?[...new Set(DAILY.filter(r=>r.gaming_date==="2025-06-30"&&targets.includes(r.bank_id)).map(r=>r.machine_id))]:targets;
      for(const target of expanded){if(used.has(target))errors.push(`${target} has conflicting moves or replacements.`);used.add(target);}
    }
  }
  const extra=Number($("#extra-comp")?.value||0);if(!Number.isFinite(extra)||extra<0)errors.push("Additional comp costs must be nonnegative.");else total+=extra;
  if(total>100000)errors.push("The plan exceeds the $100,000 operations budget.");
  return {errors:[...new Set(errors)],total};
}
function renderBudget() {
  $("#view-budget").innerHTML=`<div class="scope-note"><strong>Scenario lab, not a causal optimizer.</strong> Prices and lead times come from the supplied catalogue. Benefits below are assumptions you can change; they have not been measured as intervention effects.</div>
    <article class="card"><div class="card-head"><div><h2>Your 30-day action plan</h2><p class="card-subtitle">Up to three action types · quantities within catalogue limits · explicit targets</p></div><span class="pill gold">DRAFT FOR TEAM REVIEW</span></div><div id="plan-rows">${plan.map((p,i)=>{const a=DATA.actions.find(a=>a.action_type_id===p.id);return `<div class="budget-row" data-plan-row="${i}"><select aria-label="Action ${i+1}" data-plan-field="id">${DATA.actions.map(a=>`<option value="${a.action_type_id}" ${a.action_type_id===p.id?"selected":""}>${esc(a.name)}</option>`).join("")}</select><input aria-label="Quantity ${i+1}" data-plan-field="quantity" type="number" min="0" max="${a.quantity_limit}" value="${p.quantity}"><input class="target" aria-label="Targets ${i+1}" data-plan-field="targets" placeholder="Targets, separated by commas" value="${esc(p.targets)}"><span class="budget-cost">${money(costFor(a,p.quantity))}</span><button class="remove-row" data-remove-plan="${i}" aria-label="Remove action ${i+1}">×</button></div>`;}).join("")}</div><div class="plan-actions"><button class="button subtle" id="add-plan" ${plan.length>=3?"disabled":""}>+ Add action type</button><button class="button subtle" id="export-plan">Export scenario JSON</button></div><p class="note">Machine targets: e.g. M-1158. Bank: B-01. Zone: its displayed name. Manufacturer: its displayed name. Technician shift: day, swing or grave. Bank membership uses June's latest placement; execution still requires a feasible destination and schedule.</p><div class="control section-space"><label>Additional comp economic costs ($)<input id="extra-comp" type="number" min="0" value="0"></label></div><div class="budget-total"><span>Planned spend <strong id="plan-spend"></strong></span><span>Preserved budget <strong id="plan-unspent"></strong></span></div><div id="plan-validation"></div></article>
    <article class="card"><div class="card-head"><div><h2>What would have to be true for this to pay off?</h2><p class="card-subtitle">Change an assumption to see expected contribution and break-even. Zero effect is the default.</p></div><span class="pill">USER ASSUMPTIONS</span></div><div class="scenario-controls"><label>Incremental wagering demand<strong id="uplift-value">0%</strong><input id="uplift" type="range" min="-10" max="20" step="1" value="0"><small>Uniform change after the latest selected lead time; not a prediction of promotion lift.</small></label><label>Recoverable downtime<strong id="recovery-value">0%</strong><input id="recovery" type="range" min="0" max="100" step="5" value="0"><small>Fraction of June's peer-rate downtime opportunity recovered after lead time.</small></label><label>Recovered demand that is truly incremental<strong id="realization-value">50%</strong><input id="realization" type="range" min="0" max="100" step="5" value="50"><small>The rest is assumed to shift from other machines rather than increase casino-wide play.</small></label></div><div class="kpi-grid" id="scenario-kpis"></div><div id="scenario-waterfall" class="chart"></div><p class="note" id="scenario-method"></p><p class="note"><strong>Not an expected-value guarantee.</strong> This scenario omits interactions and operational constraints not supplied in the data. The demand band is not an intervention-effect interval. Promotion-weekend break-even is a whole-event dollar requirement, not evidence of a uniform month-long lift.</p></article>
    <div class="grid-equal"><article class="card"><h2>Draft recommendations</h2>${DATA.recommendations.map(r=>`<div class="evidence-card"><h3>${esc(r.title)}</h3><p class="note"><strong>${esc(r.action)}</strong> · ${money(r.cost_usd)}</p><p class="note">${esc(r.effect)}</p><p class="note">Measure: ${esc(r.measurement)}</p><button class="text-link" data-evidence="${r.evidence[0]}">Evidence ${r.evidence.join(", ")} ↗</button></div>`).join("")}</article><article class="card"><h2>Catalogue: what the budget can buy</h2><div class="table-wrap"><table><thead><tr><th>Action</th><th class="num">Unit cost, horizon</th><th class="num">Lead days</th><th class="num">Max units</th></tr></thead><tbody>${DATA.actions.map(a=>`<tr><td>${esc(a.name)}</td><td class="num">${money(a.cost_30_days_usd)}</td><td class="num">${a.lead_days}</td><td class="num">${a.quantity_limit}</td></tr>`).join("")}</tbody></table></div><p class="note">Unit cost includes recurring charges for max(0, 30 − lead days). A leased machine costs $2,500 + 16 × $55 = $3,380. Fixed package costs are paid in full. Installation/move downtime is additionally priced in the scenario when targets are identified.</p></article></div>`;
  const comparison=DATA.staffing_promotion_comparison,tech=comparison.technician,promo=comparison.promotion;
  $("#view-budget .scope-note").insertAdjacentHTML("afterend",`<div class="grid-equal">
    <article class="card"><div class="card-head"><div><h2>Staffing: one extra technician shift</h2><p class="card-subtitle">Catalogue staffing option · July 8–30 benefits</p></div><span class="pill gold">DOWNTIME RECOVERY</span></div>
      <div class="stat-row"><span>Full package cost</span><strong>${money(tech.cost_usd)}</strong></div>
      <div class="stat-row"><span>June-rate gross recovery opportunity (${tech.benefit_days} days)</span><strong>${money(tech.gross_recovery_scenario_usd)}</strong></div>
      <div class="stat-row"><span>Recovery needed to break even</span><strong class="negative">${pct(tech.break_even_recovery_fraction)}</strong></div>
      <div class="stat-row"><span>Net even at 100% gross recovery</span><strong class="negative">${money(tech.net_at_full_gross_recovery_usd)}</strong></div>
      <label class="range-label section-space" style="display:block">Assumed recovery of the gross opportunity <strong id="comparison-recovery-label"></strong><input id="comparison-recovery" type="range" min="0" max="100" step="5" value="${comparisonAssumptions.recovery}"></label>
      <div class="stat-row"><span>Net benefit under that assumption</span><strong id="comparison-tech-net"></strong></div>
      <p class="note">This optimistically assumes recovered play is all incremental. Recovery alone does not cover this package under June rates; other staffing benefits would need separate evidence.</p>
    </article>
    <article class="card"><div class="card-head"><div><h2>Promotion: one two-day weekend</h2><p class="card-subtitle">First eligible complete weekend · ${promo.dates.join(" → ")}</p></div><span class="pill">INCREMENTAL DEMAND</span></div>
      <div class="stat-row"><span>Promotion cost</span><strong>${money(promo.cost_usd)}</strong></div>
      <div class="stat-row"><span>Forecast baseline wagering over those two days</span><strong>${money(promo.baseline_wagers_usd)}</strong></div>
      <div class="stat-row"><span>Additional wagers needed to break even</span><strong>${money(promo.break_even_additional_wagers_usd)}</strong></div>
      <div class="stat-row"><span>Lift required above baseline weekend demand</span><strong>${pct(promo.break_even_lift_fraction)}</strong></div>
      <label class="range-label section-space" style="display:block">Assumed incremental two-day wagering lift <strong id="comparison-lift-label"></strong><input id="comparison-lift" type="range" min="0" max="20" step="1" value="${comparisonAssumptions.lift}"></label>
      <div class="stat-row"><span>Net benefit under that assumption</span><strong id="comparison-promo-net"></strong></div>
      <p class="note">Required lift is not predicted lift. Existing visits shifted from other dates are not incremental demand. Extra comp costs or displacement raise the break-even requirement.</p>
    </article></div><div class="callout"><strong>Compare the requirements, then decide what to test.</strong><p>The technician calculation is a recovery scenario; the promotion calculation is an incremental-wagering requirement. Neither is an estimated causal effect. These one-unit comparisons are separate from the editable multi-action plan below.</p><button class="text-link" data-evidence="B-02">See inputs, alternatives and measurement limits ↗</button></div>`);
  updateComparison();
  for(const [id,key] of [["uplift","uplift"],["recovery","recovery"],["realization","realization"],["extra-comp","extraComp"]])$("#"+id).value=scenario[key];
  updateScenario();
}
function updateComparison() {
  const c=DATA.staffing_promotion_comparison;
  comparisonAssumptions.recovery=Number($("#comparison-recovery").value);
  comparisonAssumptions.lift=Number($("#comparison-lift").value);
  $("#comparison-recovery-label").textContent=pct(comparisonAssumptions.recovery/100,0);
  $("#comparison-lift-label").textContent=pct(comparisonAssumptions.lift/100,0);
  $("#comparison-tech-net").textContent=money(c.technician.gross_recovery_scenario_usd*comparisonAssumptions.recovery/100-c.technician.cost_usd);
  $("#comparison-promo-net").textContent=money(c.promotion.baseline_wagers_usd*DATA.forecast.assumed_theo_hold*comparisonAssumptions.lift/100-c.promotion.cost_usd);
}
function updateScenario() {
  for(const [id,key] of [["uplift","uplift"],["recovery","recovery"],["realization","realization"],["extra-comp","extraComp"]])scenario[key]=Number($("#"+id).value);
  document.querySelectorAll("[data-plan-row]").forEach(row=>{const p=plan[Number(row.dataset.planRow)],a=DATA.actions.find(a=>a.action_type_id===p.id);row.querySelector(".budget-cost").textContent=money(costFor(a,p.quantity));});
  const {errors,total}=validatePlan(),uplift=Number($("#uplift").value)/100,recovery=Number($("#recovery").value)/100,realization=Number($("#realization").value)/100;
  $("#uplift-value").textContent=pct(uplift,0);$("#recovery-value").textContent=pct(recovery,0);$("#realization-value").textContent=pct(realization,0);
  $("#plan-spend").textContent=money(total);$("#plan-unspent").textContent=money(100000-total);
  $("#plan-validation").className=errors.length?"validation-error":"validation-ok";
  $("#plan-validation").textContent=errors.length?errors.join(" "):"Budget, action-count, target and policy-conflict checks pass. Operational feasibility and effect assumptions still need team review.";
  $("#export-plan").disabled=errors.length>0;
  const active=plan.filter(p=>p.quantity>0&&p.id!=="A-HOLD"),lead=active.length?Math.max(...active.map(p=>DATA.actions.find(a=>a.action_type_id===p.id).lead_days)):0;
  const eligible=DATA.future.slice(lead),baseline=sum(DATA.future,"expected_contribution_usd"),eligibleTheo=sum(eligible,"expected_theo_usd");
  const incremental=eligibleTheo*uplift,opportunity=DATA.summary.june_opportunity.opportunity_theo_per_day_usd*(30-lead)*recovery*realization;
  let outageCost=0;
  for(const p of active){const a=DATA.actions.find(a=>a.action_type_id===p.id),targets=p.targets.split(",").map(x=>x.trim()).filter(Boolean);
    if(!a.downtime_minutes)continue;
    const targeted=DATA.machines.filter(m=>a.unit==="machine"?targets.includes(m.machine_id):a.unit==="bank"?targets.includes(m.bank_id):a.unit==="manufacturer"?targets.includes(m.manufacturer):false);
    outageCost+=targeted.reduce((s,m)=>s+m.theo_per_available_hour_usd,0)*a.downtime_minutes/60;
  }
  const benefit=incremental+opportunity-outageCost,net=benefit-total,breakeven=ratio(total+outageCost,DATA.forecast.assumed_theo_hold);
  $("#scenario-kpis").innerHTML=metric("Baseline expected contribution",compact(baseline),"July · property-wide",true)+metric("Assumed incremental benefit",compact(benefit),"After action downtime; before action spend")+metric("Net scenario benefit",compact(net),errors.length?"Invalid plan: revise constraints first":"Versus doing nothing · assumed effect")+metric("Additional wagers to break even",compact(breakeven),"At June's expected hold; ignores F&B upside");
  plot("scenario-waterfall",[{type:"waterfall",orientation:"v",measure:["relative","relative","relative","relative","total"],x:["Demand effect","Downtime recovery","Action downtime","Action spend","Net effect"],y:[incremental,opportunity,-outageCost,-total,0],connector:{line:{color:"#c7cebd"}},increasing:{marker:{color:"#3e8074"}},decreasing:{marker:{color:"#b9924a"}},totals:{marker:{color:net>=0?"#153c35":"#b9594a"}},hovertemplate:"%{x}: $%{y:,.0f}<extra></extra>"}],{showlegend:false,yaxis:{tickprefix:"$",tickformat:".2s"}});
  $("#scenario-method").textContent=`Effects begin after ${lead} days (latest selected lead time), leaving ${30-lead} days. Incremental expected win = eligible forecast wagers × June expected hold × assumed demand lift. Recovery = June daily downtime opportunity × eligible days × recovery × incremental realization. Estimated action downtime opportunity cost: ${money(outageCost)}; peer-rate estimates are scenarios, not measured losses.`;
}

function renderEvidence() {
  const downloads=[
    ["tableau_exports.zip","All Tableau exports","CSV sources and dashboard build guides"],
    ["demand_bridge.csv","May–June demand bridge","Exposure, occupancy and wagering intensity"],
    ["staffing_promotion_comparison.json","Staffing vs promotion break-even","One technician package vs a two-day event"],
    ["property_day.csv","Daily property totals","181 days; demand, costs and contribution"],
    ["machine_day.csv","Machine-day data","Active days, exposure and payout variance"],
    ["machine_summary.csv","Machine diagnostics","Ranks and adjusted payout screening"],
    ["player_month.csv","Tracked player-months","Use COUNTD(player_id), not row counts"],
    ["guest_segment_month.csv","Guest cohort summaries","Small aggregated source; player-month counts"],
    ["forecast_holdout.csv","Holdout predictions","All models; May–June actuals and forecasts"],
    ["forecast_july.csv","July forecast & finances","Demand bands and contribution assumptions"],
    ["forecast_metrics.csv","Model validation","Pre-May CV and final holdout metrics"],
    ["action_catalog.csv","Action catalogue","Costs, lead times and incompatibilities"],
    ["TABLEAU_GUIDE.md","Tableau build guide","Connections, calculated fields and sheet recipes"],
    ["CLAIMS_AND_EVIDENCE.md","Claims & Evidence appendix","Trace claims, alternatives and limitations"],
    ["AI_DISCLOSURE.md","AI-use disclosure","Actual use; optional Gemini status"],
    ["PRESENTATION_OPTIONS.md","Presentation choices","Chart options and collaboration prompts"],
    ["forecast_methodology.json","Forecast methodology","Selection rule, calibration and validation"],
    ["input_audit.json","Input audit","SHA-256 hashes and accounting checks"]
  ];
  $("#view-evidence").innerHTML=`<div class="callout"><strong>${Object.values(DATA.meta.checks).filter(Boolean).length} build checks passed. ${DATA.summary.off_floor_rows_excluded.toLocaleString()} off-floor rows excluded.</strong><p>Inputs match the supplied manifest. Machine and property wagers, payouts, house win and theo reconcile; contribution subtracts comp costs once. Source release: ${esc(DATA.meta.release)}.</p></div>
    <article class="card"><h2>Tableau-ready exports & methods</h2><p class="card-subtitle" style="margin-bottom:18px">Use separate data sources for separate fact grains. All monetary exports are in USD unless their field explicitly says cents.</p><div class="download-grid">${downloads.map(([file,title,note])=>`<a class="download" href="downloads/${file}" download>${title} ↗<span>${note}</span></a>`).join("")}</div><p class="note">CSV downloads are generated from the same inputs as this dashboard. Chart PNG export is available in each chart's toolbar. Hosting serves the static analysis; live Gemini requires the local Python server and an explicitly enabled key.</p></article>
    <article class="card"><h2>Claims & Evidence</h2>${DATA.evidence.map(e=>`<section class="evidence-card"><h3><span class="pill">${e.id}</span> ${esc(e.claim)}</h3><dl><dt>Transformation</dt><dd>${esc(e.source)}</dd><dt>Result</dt><dd>${esc(e.result)}</dd><dt>Alternative</dt><dd>${esc(e.alternative)}</dd><dt>Limitation</dt><dd>${esc(e.limitation)}</dd></dl><button class="text-link" data-evidence="${e.id}">Open explanation ↗</button></section>`).join("")}</article>
    <article class="card"><h2>Submission checklist</h2><p class="note">A publicly accessible interactive dashboard or file with opening instructions; a video of at most two minutes; a main write-up of at most 400 words; one validated ML/time-series method; source code; up to three priced action types with uncertainty and measurement plans; AI-use disclosure; and the Claims & Evidence appendix. Draft findings should be reviewed by your team before submitting.</p></article>`;
}

async function explain(id) {
  const evidence=DATA.evidence.find(e=>e.id===id);if(!evidence)return;activeEvidence=id;
  $("#explanation-title").textContent=evidence.claim;
  $("#explanation-content").textContent=`${evidence.result}\n\nSource: ${evidence.source}\n\nAlternative explanation: ${evidence.alternative}\n\nLimitation: ${evidence.limitation}`;
  $("#gemini-explain").disabled=true;$("#gemini-status").textContent="Checking optional local Gemini connection…";$("#explanation-dialog").showModal();
  try{const response=await fetch("api/status");if(!response.ok)throw Error("Static deployment");const status=await response.json();$("#gemini-explain").disabled=!status.enabled;$("#gemini-status").textContent=status.enabled?`${status.attempts}/500 attempts · ${money(status.reserved_usd)} conservatively reserved. Cached replies are free.`:"Disabled. Run serve.py --enable-gemini with a server-side key to opt in.";}
  catch{$("#gemini-status").textContent="Static dashboard: no API calls. Optional Gemini runs through the local Python server.";}
}
function downloadJSON(filename,value) {const link=document.createElement("a");link.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"}));link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);}
document.addEventListener("click",event=>{
  const go=event.target.closest("[data-go]");if(go)setPage(go.dataset.go);
  const evidence=event.target.closest("[data-evidence]");if(evidence)explain(evidence.dataset.evidence);
  const machine=event.target.closest("[data-machine]");if(machine){selected.machine=machine.dataset.machine;renderMachines();}
  const mode=event.target.closest("[data-forecast-mode]");if(mode){selected.forecastMode=mode.dataset.forecastMode;renderForecast();}
  const remove=event.target.closest("[data-remove-plan]");if(remove){plan.splice(Number(remove.dataset.removePlan),1);renderBudget();}
  if(event.target.id==="add-plan"&&plan.length<3){plan.push({id:"A-PROMO",quantity:1,targets:""});renderBudget();}
  if(event.target.id==="export-plan"){
    const validation=validatePlan();if(validation.errors.length)return;
    downloadJSON("gilded-ace-scenario.json",{planning_horizon:"2025-07-01/2025-07-30",plan,spend_usd:validation.total,unspent_usd:100000-validation.total,
      additional_comp_costs_usd:Number($("#extra-comp").value),assumed_demand_lift:Number($("#uplift").value)/100,assumed_downtime_recovery:Number($("#recovery").value)/100,
      assumed_incremental_realization:Number($("#realization").value)/100,note:"Analyst assumptions, not causal estimates. Review measurement plans and operational feasibility before submission."});
  }
});
document.addEventListener("change",event=>{
  const id=event.target.id;
  if(["guest-start","guest-end","guest-tier","guest-region","guest-age"].includes(id)){
    selected[{"guest-start":"guestStart","guest-end":"guestEnd","guest-tier":"guestTier","guest-region":"guestRegion","guest-age":"guestAge"}[id]]=event.target.value;renderGuests();
  }
  if(id==="machine-select"){selected.machine=event.target.value;renderMachines();}
  if(event.target.dataset.planField){const row=event.target.closest("[data-plan-row]");const p=plan[Number(row.dataset.planRow)],key=event.target.dataset.planField;p[key]=key==="quantity"?Number(event.target.value):event.target.value;if(key==="id")renderBudget();else updateScenario();}
  if(id==="extra-comp")updateScenario();
});
document.addEventListener("input",event=>{if(["uplift","recovery","realization"].includes(event.target.id))updateScenario();if(["comparison-recovery","comparison-lift"].includes(event.target.id))updateComparison();});
$("#gemini-explain").addEventListener("click",async()=>{
  $("#gemini-explain").disabled=true;$("#gemini-status").textContent="Generating one bounded explanation…";
  try{const response=await fetch("api/explain",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({evidence_id:activeEvidence})});const result=await response.json();if(!response.ok)throw Error(result.error||"Explanation unavailable");$("#explanation-content").textContent=result.text;$("#gemini-status").textContent=result.cached?"Cached explanation · no new generation charge.":"Gemini-generated explanation · verify against the evidence appendix.";}
  catch(error){$("#gemini-status").textContent=error.message;}
});
async function boot() {
  try{
    const response=await fetch("data.json");if(!response.ok)throw Error("Chart data could not be loaded. Run build_analysis.py first.");DATA=await response.json();
    DAILY=unpack(DATA.daily);GUESTS=unpack(DATA.guests);delete DATA.daily;delete DATA.guests;
    plan=DATA.draft_plan.map(p=>({id:p.action_type_id,quantity:p.quantity,targets:p.targets.join(", ")}));
    $("#release-badge").textContent=`${DATA.meta.release} · synthetic`;
    for(const [selector,key] of [["#zone-filter","zone_name"],["#bank-filter","bank_id"],["#maker-filter","manufacturer"]]){
      const values=[...new Set(DAILY.map(r=>r[key]))].sort();for(const value of values){const option=document.createElement("option");option.value=value;option.textContent=value;$(selector).append(option);}
    }
    document.querySelectorAll(".nav-item").forEach(button=>button.addEventListener("click",()=>setPage(button.dataset.page)));
    for(const id of ["start-date","end-date","zone-filter","bank-filter","maker-filter"])$("#"+id).addEventListener("change",()=>{selected.machine="";render();});
    $("#reset-filters").addEventListener("click",()=>{$("#start-date").value="2025-01-01";$("#end-date").value="2025-06-30";for(const id of ["zone-filter","bank-filter","maker-filter"])$("#"+id).value="";render();});
    $("#print-button").addEventListener("click",()=>window.print());
    $("#loading").hidden=true;$("#app").hidden=false;setPage(location.hash.slice(1)||"briefing");
  }catch(error){$("#loading").hidden=true;$("#error").hidden=false;$("#error").textContent=`${error.message} Open this dashboard through python3 serve.py, not by double-clicking index.html.`;}
}
boot();
