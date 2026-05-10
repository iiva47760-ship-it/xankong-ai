import asyncio, aiohttp, json, os
from datetime import datetime, timedelta

class TrendEngine:
    def __init__(self):
        self.cache = {}
        self.last_update = datetime.min
        self.ttl = 3600

    async def get(self, force=False):
        age = (datetime.now() - self.last_update).total_seconds()
        if force or age > self.ttl or not self.cache:
            await self._refresh()
        return self.cache

    async def _refresh(self):
        try:
            crypto = await self._crypto()
        except Exception:
            crypto = []
        try:
            news = await self._news()
        except Exception:
            news = []
        insight = await self._ai_insight(crypto, news)
        self.cache = {
            "updated_at": datetime.now().isoformat(),
            "next_update": (datetime.now() + timedelta(hours=1)).isoformat(),
            "crypto_trending": crypto,
            "news_trending": news,
            "ai_insights": insight,
            "hot_topics": [c.get("name","") + " (" + c.get("symbol","") + ")" for c in crypto[:3]] + [n.get("topic","")[:50] for n in news[:3]]
        }
        self.last_update = datetime.now()

    async def _crypto(self):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.coingecko.com/api/v3/search/trending", timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    d = await r.json()
                    return [{"name": c["item"]["name"], "symbol": c["item"]["symbol"], "rank": c["item"].get("market_cap_rank","N/A")} for c in d.get("coins",[])[:7]]
        return []

    async def _news(self):
        key = os.getenv("NEWS_API_KEY","")
        if not key:
            return [{"topic":"AI Agents","heat":95},{"topic":"Bitcoin ETF","heat":90},{"topic":"LLM Models","heat":85},{"topic":"DeFi 2.0","heat":78},{"topic":"AI SaaS","heat":72},{"topic":"Quantum Computing","heat":65}]
        async with aiohttp.ClientSession() as s:
            async with s.get("https://newsapi.org/v2/top-headlines", params={"category":"technology","pageSize":8,"apiKey":key}, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    d = await r.json()
                    return [{"topic":a["title"][:80],"source":a["source"]["name"],"url":a["url"],"heat":70+(i*3)} for i,a in enumerate(d.get("articles",[])[:8])]
        return []

    async def _ai_insight(self, crypto, news):
        key = os.getenv("GEMINI_KEY","")
        if not key:
            return "Add GEMINI_KEY for AI trend analysis."
        try:
            prompt = "Analyze these market trends and give 3 specific actionable opportunities for investors. Be concise. CRYPTO: " + json.dumps(crypto[:4]) + " NEWS: " + json.dumps(news[:4])
            async with aiohttp.ClientSession() as s:
                async with s.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + key, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=aiohttp.ClientTimeout(total=20)) as r:
                    if r.status == 200:
                        d = await r.json()
                        return d["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return "Analysis error: " + str(e)
        return "Market analysis unavailable."

trend_engine = TrendEngine()
