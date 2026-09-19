"use strict";
(function () {
  const dashboard = document.querySelector('[data-page="dashboard"]');
  if (!dashboard) return;
  const panel = document.createElement("section");
  panel.className = "panel privateReport";
  panel.innerHTML = '<div class="panelHead"><div><small>PRIVATE DAILY RESEARCH · 00:00 SAST</small><h3>Your research report</h3></div><button id="privateLogout">Sign out</button></div>' +
    '<p id="reportConnection">Checking publishing connection…</p><p id="reportMeta">Loading report…</p>' +
    '<label for="reportHistory">Saved reports </label><select id="reportHistory"><option value="latest">Latest report</option></select>' +
    '<div id="privateReportBody"></div><details><summary>Connection controls</summary>' +
    '<p>ChatGPT connection address: <code>https://multisport-edge-ai.onrender.com/mcp</code></p>' +
    '<p>The publisher has upload-only permission. Connecting it requires your sign-in and consent. Consent alone does not confirm that the midnight task is configured.</p>' +
    '<button id="revokePublisher">Disconnect report publisher</button><p id="privateActionStatus" role="status"></p></details>';
  dashboard.prepend(panel);
  const get = id => document.getElementById(id);
  async function privateFetch(path, options) {
    const response = await fetch(path, {credentials:"same-origin",cache:"no-store",...options});
    if (response.status === 401) {document.body.replaceChildren();location.replace("/login");throw new Error("Sign-in required");}
    if (!response.ok) throw new Error("Private service unavailable (" + response.status + "). Try again shortly.");
    return response.json();
  }
  async function action(path) {
    const me = await privateFetch("/auth/me");
    return privateFetch(path,{method:"POST",headers:{"X-Edge-CSRF":me.csrf}});
  }
  function section(parent, title, value) {
    const heading = document.createElement("h4");heading.textContent=title;
    const content = document.createElement("p");content.className="reportText";content.textContent=value;
    parent.append(heading,content);
  }
  function render(data) {
    const body=get("privateReportBody");body.replaceChildren();
    if (!data.report) {get("reportMeta").textContent="Awaiting the first private report. No predictions have been invented.";return;}
    const report=data.report;
    const today=new Intl.DateTimeFormat("en-CA",{timeZone:"Africa/Johannesburg",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
    get("reportMeta").textContent=report.report_date+" · "+report.status.replaceAll("_"," ")+
      (report.report_date===today ? "" : " · HISTORICAL REPORT — not today's prices")+
      " · Generated "+new Date(report.generated_at).toLocaleString("en-ZA",{timeZone:"Africa/Johannesburg"})+" SAST";
    section(body,"Summary",report.summary);section(body,"Research and predictions",report.analysis);
    section(body,"Limitations",report.limitations);section(body,"Previous-day review",report.previous_day_review);
    const list=document.createElement("ul");
    for (const source of report.sources) {
      const item=document.createElement("li"), link=document.createElement("a");
      try {const url=new URL(source.url);if(url.protocol!=="https:"||url.username||url.password)continue;link.href=url.href;} catch (_) {continue;}
      link.textContent=source.name;link.target="_blank";link.rel="noopener noreferrer";
      item.append(link,document.createTextNode(" · "+source.status+" · "+source.note));list.append(item);
    }
    body.append(list);
    section(body,"Before acting","This is research, not a validated betting portfolio or a guarantee. Recheck current bookmaker prices, availability and team news. A score of 90/100 is not a 90% win probability.");
  }
  async function refresh() {
    const chosen=get("reportHistory").value;
    try {
      const [report,history,status]=await Promise.all([
        privateFetch("/v1/research-reports/"+encodeURIComponent(chosen)),
        privateFetch("/v1/research-reports"),privateFetch("/auth/publishing-status")]);
      render(report);
      get("reportConnection").textContent=status.connected?
        "Publisher consent active · delivery is confirmed only when a dated report appears below.":
        "Publisher not connected · your reports remain private. Connect ChatGPT and approve upload-only access.";
      const selector=get("reportHistory");selector.replaceChildren(new Option("Latest report","latest"));
      for(const saved of history.reports)selector.append(new Option(saved.report_date,saved.report_date));
      selector.value=chosen;
    } catch(error){get("reportMeta").textContent=error.message;}
  }
  get("reportHistory").addEventListener("change",refresh);
  get("privateLogout").addEventListener("click",async()=>{
    try{await action("/auth/logout");document.body.replaceChildren();location.replace("/login");}
    catch(error){get("privateActionStatus").textContent=error.message;}
  });
  get("revokePublisher").addEventListener("click",async()=>{
    if(!confirm("Revoke the publishing connection? Saved private reports will remain."))return;
    try{await action("/auth/revoke-publisher");get("privateActionStatus").textContent="Publisher disconnected.";await refresh();}
    catch(error){get("privateActionStatus").textContent=error.message;}
  });
  refresh();setInterval(refresh,120000);
})();
