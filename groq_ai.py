"""
Groq AI — Narrative Writer ONLY.
Groq NEVER determines bias, entry, SL, TP, or any price level.
It only receives pre-calculated facts and writes readable summaries.
Strict anti-hallucination enforcement via system prompt.
"""
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

STRICT_SYSTEM_PROMPT = """You are a professional forex trading analyst for SMC Lens, an SMC/ICT trading platform.

YOUR ONLY JOB IS TO WRITE NARRATIVE SUMMARIES based on data provided to you.

ABSOLUTE RULES — NEVER BREAK THESE:
1. NEVER guess, invent, assume, or hallucinate any price level, bias, or market data.
2. NEVER determine bias yourself — bias is given to you as a FACT.
3. NEVER generate price levels — all prices come from the data provided.
4. If data is missing or marked as unavailable, say "Data unavailable for [timeframe]" — never fill in gaps.
5. If conflicting data is given, report the conflict honestly.
6. Write EXACTLY 5 sentences minimum. No more than 7 sentences.
7. Use professional trading language. Be concise and direct.
8. Never add disclaimers, recommendations to "consult a financial advisor", or generic warnings.
9. Never say "I think", "I believe", "probably", "likely" — state facts from the data only.
10. If the signal is invalid due to HTF conflict, clearly state why it's invalid.

OUTPUT FORMAT: Plain text only. No markdown. No bullet points. No headers."""


def generate_signal_narrative(
    pair: str,
    bias: str,
    monthly_bias: str,
    weekly_bias: str,
    daily_bias: str,
    h4_bias: str,
    entry_price: float,
    sl_price: float,
    tp1_price: float,
    tp2_price: float,
    rr1: float,
    confluence_score: int,
    candlestick_pattern: str,
    volume_status: str,
    premium_discount_zone: str,
    signal_valid: bool,
    conflict_reason: str = None
) -> str:
    """
    Generate entry signal narrative. All values pre-calculated by code.
    """
    if not signal_valid:
        data_prompt = f"""
Generate a 5-sentence analyst note explaining why this setup is INVALID.

Pair: {pair}
Bias: {bias}
Conflict: {conflict_reason or 'HTF timeframes in conflict'}
Confluence Score: {confluence_score}/13 (minimum 8 required)
Monthly: {monthly_bias} | Weekly: {weekly_bias} | Daily: {daily_bias} | 4H: {h4_bias}

State clearly why the trade is not valid. Do not soften this — be direct.
"""
    else:
        data_prompt = f"""
Write a 5-sentence signal summary for this trade setup. Use ONLY the data below.

Pair: {pair}
Overall Bias: {bias}
Monthly Bias: {monthly_bias}
Weekly Bias: {weekly_bias}
Daily Bias: {daily_bias}
4H Confirmation: {h4_bias}
Premium/Discount Zone: {premium_discount_zone}
Entry Price: {entry_price}
Stop Loss: {sl_price}
Take Profit 1: {tp1_price}
Take Profit 2: {tp2_price}
Risk/Reward: 1:{rr1}
Confluence Score: {confluence_score}/13
Candlestick Pattern: {candlestick_pattern}
Volume: {volume_status}

Write exactly 5 sentences covering: HTF bias alignment, entry zone, trade levels, confluence strength, and recommended stance.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {"role": "user", "content": data_prompt}
        ],
        temperature=0.3,
        max_tokens=400
    )

    return response.choices[0].message.content.strip()


def generate_htf_summary(
    pair: str,
    monthly_bias: str,
    weekly_bias: str,
    daily_bias: str,
    h4_bias: str,
    overall_bias: str,
    entry_tf: str,
    entry_tf_bias: str,
    key_htf_level: float,
    premium_discount: str,
    trade_valid: bool,
    conflicts: list
) -> str:
    """
    Generate HTF top-down bias summary for Pro users.
    All timeframe biases pre-calculated by code.
    """
    conflicts_text = "; ".join(conflicts) if conflicts else "None"

    data_prompt = f"""
Write a 5-sentence top-down analysis summary for {pair}.

Use ONLY this data:
Monthly Bias: {monthly_bias}
Weekly Bias: {weekly_bias}
Daily Bias: {daily_bias}
4H Confirmation: {h4_bias}
Overall HTF Bias: {overall_bias}
Entry TF ({entry_tf}): {entry_tf_bias}
Key HTF Level: {key_htf_level}
Price Zone: {premium_discount}
Trade Valid: {'YES' if trade_valid else 'NO'}
Conflicts: {conflicts_text}

Sentence structure:
1. Monthly and Weekly bias statement
2. Daily confirmation and key HTF level
3. 4H alignment statement
4. Entry TF alignment with HTF
5. Recommended stance based on alignment

If Trade Valid is NO, the final sentence must clearly state "No trade — [conflict reason]."
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {"role": "user", "content": data_prompt}
        ],
        temperature=0.3,
        max_tokens=400
    )

    return response.choices[0].message.content.strip()


def generate_trial_narrative(
    pair: str,
    bias: str,
    confluence_score: int,
    entry_price: float,
    sl_price: float,
    tp1_price: float,
    rr1: float
) -> str:
    """
    Short 2-sentence narrative for trial users.
    Teases the full analysis available on Pro.
    """
    data_prompt = f"""
Write exactly 2 sentences summarizing this setup for {pair}.

Bias: {bias}
Entry: {entry_price}
SL: {sl_price}
TP1: {tp1_price}
RR: 1:{rr1}
Confluence: {confluence_score}/13

First sentence: state the bias and entry zone.
Second sentence: state the RR and confluence score.
Do not add anything else.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {"role": "user", "content": data_prompt}
        ],
        temperature=0.2,
        max_tokens=120
    )

    return response.choices[0].message.content.strip()
