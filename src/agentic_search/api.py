"""FastAPI HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agentic_search.pipeline import run_pipeline

app = FastAPI(title="Agentic Search", version="0.1.0")


class QueryIn(BaseModel):
    topic: str = Field(min_length=1, max_length=500)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/search")
async def search(body: QueryIn):
    try:
        result = await run_pipeline(body.topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return result.model_dump()


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agentic Search</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}
textarea,input{width:100%;box-sizing:border-box}
table{border-collapse:collapse;width:100%;margin-top:1rem}
th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top}
th{background:#f5f5f5}
pre{white-space:pre-wrap;font-size:12px;background:#fafafa;padding:8px}
</style></head><body>
<h1>Agentic Search</h1>
<p>Enter a topic. Results include citations per cell (field → URL + quote).</p>
<textarea id="q" rows="3" placeholder="e.g. AI startups in healthcare"></textarea><br>
<button id="go">Search</button>
<div id="out"></div>
<script>
document.getElementById('go').onclick = async () => {
  const topic = document.getElementById('q').value.trim();
  if (!topic) return;
  document.getElementById('out').textContent = 'Loading…';
  const r = await fetch('/search', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic})});
  const j = await r.json();
  if (!r.ok) { document.getElementById('out').textContent = JSON.stringify(j); return; }
  const ents = j.entities || [];
  let html = '<table><thead><tr><th>Name</th><th>Summary</th><th>Attributes</th><th>Citations</th></tr></thead><tbody>';
  for (const e of ents) {
    const attrs = e.attributes ? Object.entries(e.attributes).map(([k,v])=>k+': '+v).join('<br>') : '';
    const cites = (e.citations||[]).map(c=>'<b>'+c.field+'</b> — <a href="'+c.url+'">'+c.url+'</a><pre>'+c.quote+'</pre>').join('');
    html += '<tr><td>'+escapeHtml(e.name)+'</td><td>'+escapeHtml(e.summary)+'</td><td>'+attrs+'</td><td>'+cites+'</td></tr>';
  }
  html += '</tbody></table>';
  document.getElementById('out').innerHTML = html;
};
function escapeHtml(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
</script>
</body></html>"""
