# USCIS API Testing Console

A Streamlit app for testing official USCIS Torch APIs.

## 🚀 Quick Start

### Local Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets (see below)
5. Deploy!

## 🔐 Secrets Configuration

Add these secrets in Streamlit Cloud (Settings → Secrets):

```toml
USCIS_CLIENT_ID = "your_client_id"
USCIS_CLIENT_SECRET = "your_client_secret"
USCIS_ENVIRONMENT = "sandbox"
CLAUDE_API_KEY = "sk-ant-xxxxx"
```

Or for local dev, create `.streamlit/secrets.toml`

## 📋 Available APIs

| API | Endpoint | Description |
|-----|----------|-------------|
| Case Status | `GET /case-status/{receipt}` | Check case status |
| FOIA Request | `POST /foia/request` | Create FOIA request |
| FOIA Status | `GET /foia/status/{number}` | Check FOIA status |

## 🧪 Sandbox Test Receipts

- `EAC9999103402` - I-130 Case Approval
- `WAC9999103402` - Test data
- `LIN9999103402` - Test data

## 📚 Resources

- [USCIS Developer Portal](https://developer.uscis.gov)
- [API Documentation](https://developer.uscis.gov/apis)
- [OAuth Guide](https://developer.uscis.gov/article/how-get-access-tokens-client-credentials)
