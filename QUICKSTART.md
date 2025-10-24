# Quick Start

Get up and running in 3 steps:

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Your API Key

Create a file at `~/.env` with your Fathom API key:

```bash
echo "FATHOM_API_KEY=your_api_key_here" > ~/.env
```

Replace `your_api_key_here` with your actual Fathom API key.

## 3. Run the Test

```bash
python test_api.py
```

That's it! The script will test your Fathom API connection and display your teams and meetings.

---

**Need your API key?** Get it from your Fathom account settings at https://app.fathom.video/settings/api
