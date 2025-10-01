import os
from dotenv import load_dotenv
load_dotenv()
import openai
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
def explain_signal_natural_language(signal):
    if not OPENAI_API_KEY:
        return "OpenAI API key not set. Set OPENAI_API_KEY to get professional explanations."
    prompt = f"""You are a senior trader with 20-25 years experience specialized in Smart Money Concepts.
Describe the following trading signal like a professional trader, explaining the market structure, why entry/SL/TP make sense, and any context about order blocks, FVGs, liquidity, and timeframe confluence.

Signal: {signal}
Explain concisely but professionally."""
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=300,
            temperature=0.2
        )
        return resp['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"OpenAI call failed: {e}"
