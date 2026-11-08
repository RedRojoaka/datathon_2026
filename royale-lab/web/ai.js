"use strict";
const $=selector=>document.querySelector(selector);
const escapeHTML=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dollars=value=>"$"+Number(value||0).toFixed(4);
let state={topics:[],insights:[],status:{enabled:false},local_server:false},active="forecast",running=false;

function render(){
  if(!state.topics.length){$("#ai-question").textContent="Evidence is unavailable";return;}
  if(!state.topics.some(t=>t.key===active))active=state.topics[0].key;
  const topic=state.topics.find(t=>t.key===active),insight=state.insights.find(row=>row.topic===active);
  $("#ai-topics").innerHTML=state.topics.map(t=>`<button class="topic-button ${t.key===active?"active":""}" data-topic="${t.key}" aria-pressed="${t.key===active}"><strong>${escapeHTML(t.title)}</strong><span>${escapeHTML(t.question)}</span></button>`).join("");
  $("#ai-question").textContent=topic.question;$("#ai-scope").textContent=topic.scope;
  $("#ai-answer").textContent=insight?insight.explanation:"The evidence is ready below. Generate a short explanation when your local Gemini connection is configured.";
  $("#ai-badge").textContent=insight?"SAVED GEMINI RESPONSE":"AUDITED EVIDENCE";
  $("#ai-provenance").textContent=insight?`${insight.model} · ${insight.generated_at_utc} · Evidence: ${insight.evidence_ids}`:"No AI-generated explanation exists for this topic yet.";
  $("#ai-generate").disabled=running||!state.status.enabled;
  $("#ai-generate").textContent=running?"Generating…":insight?"Reuse saved explanation":"Generate with Gemini";
  $("#ai-call-note").textContent=insight?"This saved response can be reused without a new generation.":state.status.enabled?`One new explanation reserves at most ${dollars(state.status.max_request_usd)}. No automatic retry.`:"Use the local setup below to enable new generations.";
  $("#ai-copy").disabled=!insight;$("#ai-download").disabled=!state.insights.length;$("#ai-markdown").disabled=!state.insights.length;
  $("#ai-reserved").textContent=dollars(state.status.reserved_usd);
  $("#ai-allowance-note").textContent=state.local_server?`${state.status.attempts||0}/500 generation attempts · ${dollars(state.status.max_total_reserve_usd||1.85)} maximum local token reserve at configured prices.`:"Hosted reading mode. New generations run through your local Python server with a persistent spending allowance.";
  $("#ai-connection").textContent=state.status.enabled?"Key configured · ready to request":state.local_server?"Local server · Gemini generation disabled":"Hosted reading mode";
  $("#ai-usage").textContent=state.status.enabled?"A request is sent only when you click Generate.":"Saved explanations and their evidence remain available without new API calls.";
  $("#ai-evidence").innerHTML=topic.facts.map(f=>`<article class="fact"><strong>${escapeHTML(f.id)} · ${escapeHTML(f.claim)}</strong><p>${escapeHTML(f.result)}</p><p><b>Alternative:</b> ${escapeHTML(f.alternative)}</p><p><b>Limitation:</b> ${escapeHTML(f.limitation)}</p><p><b>Transformation:</b> ${escapeHTML(f.source)}</p></article>`).join("");
}
function download(filename,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const link=document.createElement("a");link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function csvCell(value){let text=String(value??"");if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';}
document.addEventListener("click",event=>{const button=event.target.closest("[data-topic]");if(button){active=button.dataset.topic;history.replaceState(null,"","#"+active);$("#ai-error").hidden=true;render();}});
$("#ai-generate").addEventListener("click",async()=>{
  const topic=state.topics.find(t=>t.key===active);if(!topic||running||!state.status.enabled)return;
  running=true;$("#ai-error").hidden=true;render();
  try{
    const response=await fetch("api/explain",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({evidence_id:topic.id})});
    const result=await response.json();if(!response.ok)throw Error(result.error||"Explanation unavailable");
    const refreshed=await fetch("api/briefing",{cache:"no-store"});if(!refreshed.ok)throw Error("Response saved; reload this page to view it.");state=await refreshed.json();
    if(result.export_warning){$("#ai-error").textContent=result.export_warning;$("#ai-error").hidden=false;}
  }catch(error){$("#ai-error").textContent=error.message;$("#ai-error").hidden=false;
    try{const status=await fetch("api/status",{cache:"no-store"});if(status.ok)state.status=await status.json();}catch{}
  }finally{running=false;render();}
});
$("#ai-copy").addEventListener("click",async()=>{const row=state.insights.find(r=>r.topic===active);if(!row)return;try{await navigator.clipboard.writeText(row.explanation+"\n\nEvidence: "+row.evidence_ids+"\nScope: "+row.scope);$("#ai-copy").textContent="Copied";setTimeout(()=>$("#ai-copy").textContent="Copy explanation",1500);}catch{$("#ai-error").textContent="Clipboard unavailable. Use Download briefing to save the text.";$("#ai-error").hidden=false;}});
$("#ai-download").addEventListener("click",()=>{if(!state.insights.length)return;const columns=["topic","title","explanation","evidence_ids","scope","model","generated_at_utc","context_digest","source"];const lines=[columns.map(csvCell).join(","),...state.insights.map(row=>columns.map(key=>csvCell(row[key])).join(","))];download("gemini_insights.csv","\ufeff"+lines.join("\r\n"),"text/csv;charset=utf-8");});
$("#ai-markdown").addEventListener("click",()=>{const content="# Gemini management briefing\n\n"+state.insights.map(row=>`## ${row.title}\n\n${row.explanation}\n\nEvidence: ${row.evidence_ids}\n\nScope: ${row.scope}\n\nModel: ${row.model} · Generated: ${row.generated_at_utc}`).join("\n\n");download("GEMINI_BRIEF.md",content,"text/markdown;charset=utf-8");});
async function boot(){
  try{const response=await fetch("api/briefing",{cache:"no-store"});if(!response.ok)throw Error("Reading mode");state=await response.json();}
  catch{try{const response=await fetch("ai_topics.json");if(!response.ok)throw Error("Rebuild the analysis to create ai_topics.json.");const context=await response.json();state.topics=context.topics;try{const saved=await fetch("downloads/gemini_insights.json");if(saved.ok){const rows=await saved.json();if(Array.isArray(rows))state.insights=rows.filter(row=>state.topics.some(t=>t.key===row.topic&&t.context_digest===row.context_digest));}}catch{}}catch(error){$("#ai-error").textContent=error.message;$("#ai-error").hidden=false;}}
  const hash=location.hash.slice(1);if(hash)active=hash;
  $("#ai-setup").open=!state.status.enabled;render();
}
boot();
