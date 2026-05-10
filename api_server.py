"""FastAPI server for Universal AI Agent."""
import os
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from agent_config import API_DEBUG
from universal_agent import UniversalAIAgent
from data_provider import RealTimeDataProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Models ──────────────────────────────────────────────────
class PromptRequest(BaseModel):
    prompt: str
    context: Optional[Dict] = None

class NewsRequest(BaseModel):
    topic: str
    limit: int = 10

class WebSearchRequest(BaseModel):
    query: str
    limit: int = 10

# ── App ─────────────────────────────────────────────────────
agent = UniversalAIAgent()
data_provider = RealTimeDataProvider()
active_ws: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Agent API starting...")
    yield
    logger.info("🛑 Shutting down...")

app = FastAPI(title="Universal AI Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routes ───────────────────────────────────────────────────
@app.get("/")
async def root():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(),
            "agent_provider": agent.provider,
            "agent_capabilities": agent.get_capabilities()}

@app.post("/v1/prompt")
async def process_prompt(req: PromptRequest):
    try:
        response = await agent.process_prompt(req.prompt, req.context)
        return {"status": "success", "response": response,
                "provider": agent.provider, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/v1/agent/capabilities")
async def capabilities():
    return agent.get_capabilities()

@app.get("/v1/agent/history")
async def history(limit: int = 10):
    return {"history": agent.get_history(limit), "total": len(agent.task_history)}

@app.post("/v1/agent/clear-memory")
async def clear_memory():
    agent.clear_memory()
    return {"status": "success"}

@app.post("/v1/news/search")
async def news(req: NewsRequest):
    try:
        articles = await data_provider.get_news(req.topic, req.limit)
        return {"status": "success", "articles": articles, "count": len(articles)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/v1/crypto/prices")
async def crypto(symbols: str = "BTC,ETH,XRP"):
    try:
        data = await data_provider.get_crypto_prices(
            [s.strip().upper() for s in symbols.split(",")])
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/v1/weather/{city}")
async def weather(city: str, country: str = ""):
    try:
        data = await data_provider.get_weather(city, country)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/v1/stocks/quote/{symbol}")
async def stock(symbol: str):
    try:
        data = await data_provider.get_stock_quote(symbol.upper())
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/v1/trending")
async def trending():
    return {"status": "success", "topics": await data_provider.get_trending_topics()}

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    active_ws.append(websocket)
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            response = await agent.process_prompt(data.get("prompt", ""), data.get("context"))
            await websocket.send_json({"status": "success", "response": response,
                                       "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        active_ws.remove(websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        await websocket.close()

# ── Dashboard HTML ───────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>XanKong AI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh}
.wrap{max-width:900px;margin:0 auto;padding:30px 20px}
.card{background:#fff;border-radius:12px;padding:30px;margin-bottom:24px;
      box-shadow:0 8px 30px rgba(0,0,0,.12)}
h1{color:#667eea;font-size:2em;margin-bottom:6px}
h2{color:#667eea;margin-bottom:16px}
textarea,input{width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:8px;
               font-size:15px;font-family:inherit;margin-bottom:12px}
textarea{min-height:100px;resize:vertical}
textarea:focus,input:focus{outline:none;border-color:#667eea}
button{padding:12px 28px;background:linear-gradient(135deg,#667eea,#764ba2);
       color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer;font-weight:600}
button:hover{opacity:.9}
.box{background:#f5f5f5;border-left:4px solid #667eea;padding:16px;border-radius:8px;
     margin-top:16px;white-space:pre-wrap;font-family:monospace;font-size:14px;
     max-height:400px;overflow-y:auto;display:none}
.status{display:inline-block;width:10px;height:10px;border-radius:50%;
        background:#4caf50;margin-right:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>🤖 XanKong AI Agent</h1>
    <p><span class="status"></span>Online · Gemini 1.5 Flash</p>
  </div>
  <div class="card">
    <h2>💬 Chat with AI</h2>
    <textarea id="prompt" placeholder="Ask me anything..."></textarea>
    <button onclick="send()">Send →</button>
    <div class="box" id="resp"></div>
  </div>
  <div class="card">
    <h2>📊 Crypto Prices</h2>
    <input id="syms" value="BTC,ETH" placeholder="BTC,ETH,XRP">
    <button onclick="getCrypto()">Get Prices</button>
    <div class="box" id="crypto"></div>
  </div>
  <div class="card">
    <h2>🌤️ Weather</h2>
    <input id="city" value="London" placeholder="City name">
    <button onclick="getWeather()">Get Weather</button>
    <div class="box" id="weather"></div>
  </div>
</div>
<script>
const API = '';
async function send(){
  const p=document.getElementById('prompt').value.trim();
  if(!p)return;
  const b=document.getElementById('resp');
  b.style.display='block';b.textContent='⏳ Thinking...';
  try{
    const r=await fetch(API+'/v1/prompt',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
    const d=await r.json();
    b.textContent=d.response||d.detail||'No response';
  }catch(e){b.textContent='❌ '+e.message}
}
async function getCrypto(){
  const s=document.getElementById('syms').value;
  const b=document.getElementById('crypto');
  b.style.display='block';b.textContent='Loading...';
  try{
    const r=await fetch(API+'/v1/crypto/prices?symbols='+s);
    const d=await r.json();
    b.textContent=JSON.stringify(d.data,null,2);
  }catch(e){b.textContent='❌ '+e.message}
}
async function getWeather(){
  const c=document.getElementById('city').value;
  const b=document.getElementById('weather');
  b.style.display='block';b.textContent='Loading...';
  try{
    const r=await fetch(API+'/v1/weather/'+encodeURIComponent(c));
    const d=await r.json();
    b.textContent=JSON.stringify(d.data,null,2);
  }catch(e){b.textContent='❌ '+e.message}
}
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter')send()});
</script>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", "8888")))
    logger.info(f"🚀 Starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port,
                log_level="debug" if API_DEBUG else "info")
