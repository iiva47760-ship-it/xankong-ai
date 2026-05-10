"""XanKong AI Pro - SaaS with monetization"""
import os, json
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import logging

from agent_config import API_DEBUG
from universal_agent import UniversalAIAgent
from data_provider import RealTimeDataProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS: Dict[str, Dict] = {}
PLANS = {
    "free":     {"requests_per_day": 10,  "price": 0},
    "pro":      {"requests_per_day": 500, "price": 9},
    "business": {"requests_per_day": 5000,"price": 29},
}

def today(): return datetime.now().strftime("%Y-%m-%d")

def get_user(key: str) -> Dict:
    if not key:
        return {"plan": "free", "requests_today": 0, "last_reset": today()}
    if key not in USERS:
        USERS[key] = {"plan": "free", "requests_today": 0, "last_reset": today()}
    u = USERS[key]
    if u["last_reset"] != today():
        u["requests_today"] = 0
        u["last_reset"] = today()
    return u

def check_limit(u: Dict) -> bool:
    return u["requests_today"] < PLANS[u["plan"]]["requests_per_day"]

class PromptRequest(BaseModel):
    prompt: str
    context: Optional[Dict] = None

class NewsRequest(BaseModel):
    topic: str
    limit: int = 10

agent = UniversalAIAgent()
data_provider = RealTimeDataProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("XanKong AI Pro v2 starting")
    yield

app = FastAPI(title="XanKong AI Pro", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
async def root(): return HTMLResponse(open("landing.html").read() if os.path.exists("landing.html") else "<h1>XanKong AI Pro</h1><a href=/app>Open App</a>")

@app.get("/app")
async def dashboard(): return HTMLResponse(open("app.html").read() if os.path.exists("app.html") else "<h1>App</h1>")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(),
            "agent_provider": agent.provider, "version": "2.0.0",
            "agent_capabilities": agent.get_capabilities()}

@app.get("/plans")
async def get_plans(): return {"plans": PLANS}

@app.post("/v1/prompt")
async def process_prompt(req: PromptRequest, x_api_key: Optional[str] = Header(None)):
    user = get_user(x_api_key or "")
    if not check_limit(user):
        raise HTTPException(429, f"Daily limit reached. Upgrade at xankong-ai-production.up.railway.app/#pricing")
    response = await agent.process_prompt(req.prompt, req.context)
    user["requests_today"] += 1
    remaining = PLANS[user["plan"]]["requests_per_day"] - user["requests_today"]
    return {"status": "success", "response": response, "provider": agent.provider,
            "plan": user["plan"], "requests_remaining": remaining, "timestamp": datetime.now().isoformat()}

@app.get("/v1/agent/capabilities")
async def capabilities(): return agent.get_capabilities()

@app.get("/v1/agent/history")
async def history(limit: int = 10):
    return {"history": agent.get_history(limit), "total": len(agent.task_history)}

@app.post("/v1/agent/clear-memory")
async def clear_memory():
    agent.clear_memory()
    return {"status": "success"}

@app.post("/v1/news/search")
async def news(req: NewsRequest, x_api_key: Optional[str] = Header(None)):
    user = get_user(x_api_key or "")
    if user["plan"] == "free":
        raise HTTPException(403, "News requires Pro plan ($9/mo)")
    articles = await data_provider.get_news(req.topic, req.limit)
    return {"status": "success", "articles": articles, "count": len(articles)}

@app.get("/v1/crypto/prices")
async def crypto(symbols: str = "BTC,ETH,XRP"):
    data = await data_provider.get_crypto_prices([s.strip().upper() for s in symbols.split(",")])
    return {"status": "success", "data": data, "timestamp": datetime.now().isoformat()}

@app.get("/v1/weather/{city}")
async def weather(city: str, x_api_key: Optional[str] = Header(None)):
    user = get_user(x_api_key or "")
    if user["plan"] == "free":
        raise HTTPException(403, "Weather requires Pro plan")
    data = await data_provider.get_weather(city)
    return {"status": "success", "data": data}

@app.get("/v1/stocks/quote/{symbol}")
async def stock(symbol: str):
    data = await data_provider.get_stock_quote(symbol.upper())
    return {"status": "success", "data": data}

@app.get("/v1/trending")
async def trending():
    return {"status": "success", "topics": await data_provider.get_trending_topics()}

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            response = await agent.process_prompt(data.get("prompt", ""), data.get("context"))
            await websocket.send_json({"status": "success", "response": response})
    except WebSocketDisconnect:
        pass



# ── Stripe Checkout ──────────────────────────────────────────
@app.get("/checkout/{plan}")
async def checkout(plan: str, request: Request):
    import os
    base = str(request.base_url).rstrip("/")
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return HTMLResponse("""<html><body style='font-family:sans-serif;background:#0a0a0f;color:#fff;padding:40px;text-align:center'>
<h2 style='color:#a78bfa'>Stripe Setup Required</h2>
<p style='color:#888;margin:16px 0'>Add STRIPE_SECRET_KEY to Railway environment variables</p>
<a href='/' style='color:#667eea'>Back to Home</a></body></html>""")
    try:
        import stripe
        stripe.api_key = stripe_key
        prices = {"pro": os.getenv("STRIPE_PRICE_PRO",""), "business": os.getenv("STRIPE_PRICE_BUSINESS","")}
        if plan not in prices or not prices[plan]:
            raise HTTPException(400, f"Plan {plan} price not configured in Railway env vars")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": prices[plan], "quantity": 1}],
            mode="subscription",
            success_url=base + "/success?plan=" + plan,
            cancel_url=base + "/#pricing",
        )
        from fastapi.responses import RedirectResponse
        return RedirectResponse(session.url)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/success")
async def success(plan: str = "pro"):
    return HTMLResponse(f"""<html><body style='font-family:sans-serif;background:#0a0a0f;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;flex-direction:column;text-align:center'>
<div style='font-size:4em;margin-bottom:20px'>🎉</div>
<h1 style='color:#a78bfa'>Payment Successful!</h1>
<p style='color:#888;margin:16px 0 32px'>Welcome to XanKong AI {plan.title()} plan!</p>
<a href='/app' style='padding:14px 32px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:10px;text-decoration:none;font-weight:700'>Open Dashboard</a>
</body></html>""")

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    import os, stripe
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        return {"status": "webhook_not_configured"}
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
        if event["type"] == "checkout.session.completed":
            logger.info(f"Payment completed!")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, str(e))




# ── Trend Intelligence Routes ─────────────────────────────────
from trend_engine import trend_engine as _te

@app.get("/v1/trends")
async def get_trends(refresh: bool = False, x_api_key: str = None):
    user = get_user(x_api_key or "")
    data = await _te.get(force=refresh)
    if user["plan"] == "free":
        return {"status": "success", "plan": "free",
                "hot_topics": data.get("hot_topics", [])[:3],
                "updated_at": data.get("updated_at"),
                "upgrade_msg": "Upgrade to Pro for full AI insights + crypto trends",
                "upgrade_url": "/checkout/pro"}
    return {"status": "success", "plan": user["plan"], **data}

@app.get("/v1/trends/crypto")
async def crypto_trends():
    data = await _te.get()
    return {"status": "success", "trending": data.get("crypto_trending", []), "updated_at": data.get("updated_at")}

@app.get("/v1/trends/insights")
async def ai_insights(x_api_key: str = None):
    user = get_user(x_api_key or "")
    if user["plan"] == "free":
        raise HTTPException(403, "AI insights require Pro plan. Upgrade at /checkout/pro")
    data = await _te.get()
    return {"status": "success", "insights": data.get("ai_insights"), "updated_at": data.get("updated_at")}

@app.post("/v1/trends/refresh")
async def refresh_trends(x_api_key: str = None):
    user = get_user(x_api_key or "")
    if user["plan"] == "free":
        raise HTTPException(403, "Manual refresh requires Pro plan")
    data = await _te.get(force=True)
    return {"status": "refreshed", "updated_at": data.get("updated_at")}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", "8888")))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug" if API_DEBUG else "info")
