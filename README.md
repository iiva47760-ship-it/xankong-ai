# XanKong AI Agent

Universal AI Agent with Gemini, real-time data, and REST API.

## Deploy on Railway

1. Fork/push this repo to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add environment variables (see .env.example)
4. Done — Railway gives you a public HTTPS URL

## Local run

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python api_server.py
```

Open http://localhost:8888
