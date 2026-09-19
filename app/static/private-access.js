"use strict";
const el = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const activating = location.pathname === "/activate";
const consenting = location.pathname === "/auth/consent";
let activationToken = location.hash.slice(1);
// Fragment secrets are not sent to the server; remove this one from current browser history.
if (activationToken) history.replaceState(null, "", location.pathname + location.search);
function nextPath() {
  const next = params.get("next") || "/";
  return next === "/" || /^\/auth\/consent\?request=[A-Za-z0-9_-]{32,128}$/.test(next) ? next : "/";
}
async function send(path, data, csrf) {
  const response = await fetch(path, {method:"POST", credentials:"same-origin", cache:"no-store",
    headers:{"Content-Type":"application/json", ...(csrf ? {"X-Edge-CSRF":csrf} : {})},
    body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Request rejected. Check your input.");
  return result;
}
if (activating) {
  el("title").textContent = "Activate your private app";
  el("description").textContent = "Choose a unique password of at least 15 characters. This one-time link creates the only owner account.";
  el("password").minLength = 15;
  el("password").autocomplete = "new-password";
  el("submit").textContent = "Activate private access";
  if (!activationToken) { el("message").textContent = "Open your complete private activation link."; el("submit").disabled = true; }
}
el("accessForm").addEventListener("submit", async event => {
  event.preventDefault(); el("submit").disabled = true; el("message").textContent = "Signing in…";
  try {
    const payload = {password:el("password").value};
    if (activating) payload.activation_token = activationToken;
    await send(activating ? "/auth/activate" : "/auth/login", payload);
    activationToken = ""; el("password").value = ""; location.replace(nextPath());
  } catch (error) {el("message").textContent = error.message; el("submit").disabled = false;}
});
if (consenting) {
  el("title").textContent = "Connect daily research";
  el("description").textContent = "Approve upload-only access to your private MultiSport database.";
  el("accessForm").hidden = true; el("consent").hidden = false;
  const decide = async approve => {
    el("approve").disabled = true; el("deny").disabled = true;
    try {
      const response = await fetch("/auth/me", {cache:"no-store",credentials:"same-origin"});
      if (!response.ok) throw new Error("Session expired. Sign in again.");
      const me = await response.json();
      const result = await send("/auth/consent", {request_id:params.get("request"), approve}, me.csrf);
      const redirect = new URL(result.redirect);
      if (redirect.protocol !== "https:" || redirect.hostname !== "chatgpt.com") throw new Error("Unexpected callback rejected.");
      location.replace(redirect.href);
    } catch (error) {el("message").textContent=error.message;el("approve").disabled=false;el("deny").disabled=false;}
  };
  el("approve").addEventListener("click",()=>decide(true));
  el("deny").addEventListener("click",()=>decide(false));
}
