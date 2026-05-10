"""Real-time data: news, crypto, weather, web search."""
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from agent_config import NEWS_API_KEY, WEATHER_API_KEY

logger = logging.getLogger(__name__)


class RealTimeDataProvider:
    def __init__(self):
        self.cache: Dict = {}
        self.cache_ttl = 3600

    def _is_cached(self, key: str) -> bool:
        if key not in self.cache:
            return False
        age = (datetime.now() - datetime.fromisoformat(
            self.cache[key]["timestamp"])).total_seconds()
        return age < self.cache_ttl

    def _cache_set(self, key: str, data: Any):
        self.cache[key] = {"data": data, "timestamp": datetime.now().isoformat()}

    def _cache_get(self, key: str) -> Any:
        return self.cache[key]["data"]

    async def get_news(self, query: str, limit: int = 10) -> List[Dict]:
        key = f"news_{query}"
        if self._is_cached(key):
            return self._cache_get(key)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://newsapi.org/v2/everything",
                    params={"q": query, "sortBy": "publishedAt", "language": "en",
                            "pageSize": limit, "apiKey": NEWS_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        data = await r.json()
                        articles = [{"title": a["title"], "source": a["source"]["name"],
                            "url": a["url"], "description": a.get("description", ""),
                            "published": a["publishedAt"]}
                            for a in data.get("articles", [])]
                        self._cache_set(key, articles)
                        return articles
        except Exception as e:
            logger.error(f"News error: {e}")
        return []

    async def get_crypto_prices(self, symbols: List[str] = None) -> Dict:
        if not symbols:
            symbols = ["BTC", "ETH", "XRP"]
        key = f"crypto_{'_'.join(symbols)}"
        if self._is_cached(key):
            return self._cache_get(key)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": ",".join(symbols).lower(), "vs_currencies": "usd",
                            "include_24hr_change": "true"},
                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        data = await r.json()
                        self._cache_set(key, data)
                        return data
        except Exception as e:
            logger.error(f"Crypto error: {e}")
        return {}

    async def get_weather(self, city: str, country_code: str = "") -> Dict:
        key = f"weather_{city}"
        if self._is_cached(key):
            return self._cache_get(key)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.openweathermap.org/data/2.5/weather",
                    params={"q": f"{city},{country_code}".rstrip(","),
                            "appid": WEATHER_API_KEY, "units": "metric"},
                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        d = await r.json()
                        weather = {"city": d.get("name"), "temperature": d["main"]["temp"],
                            "feels_like": d["main"]["feels_like"],
                            "humidity": d["main"]["humidity"],
                            "description": d["weather"][0]["description"],
                            "wind_speed": d["wind"]["speed"]}
                        self._cache_set(key, weather)
                        return weather
        except Exception as e:
            logger.error(f"Weather error: {e}")
        return {}

    async def get_stock_quote(self, symbol: str) -> Dict:
        key = f"stock_{symbol}"
        if self._is_cached(key):
            return self._cache_get(key)
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            d = t.info
            quote = {"symbol": symbol, "price": d.get("currentPrice"),
                     "change_percent": d.get("regularMarketChangePercent"),
                     "market_cap": d.get("marketCap")}
            self._cache_set(key, quote)
            return quote
        except Exception as e:
            logger.error(f"Stock error: {e}")
        return {}

    async def get_trending_topics(self) -> List[str]:
        return ["Artificial Intelligence", "Cryptocurrency", "Climate Change",
                "Quantum Computing", "Space Exploration", "Machine Learning"]

    async def search_web(self, query: str) -> List[Dict]:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return [{"title": r.get("title"), "url": r.get("href"),
                         "snippet": r.get("body")}
                        for r in ddgs.text(query, max_results=10)]
        except Exception as e:
            logger.error(f"Web search error: {e}")
        return []
