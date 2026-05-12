import json
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are analyzing a financial transaction for risk signals.

IMPORTANT CONSTRAINTS:
- You CANNOT approve or deny the transaction
- You can only provide advisory analysis
- Your job is to explain risk, not decide
- Treat your output as input to a human reviewer

TASK:
1. Identify behavioral red flags in the transaction notes/metadata
2. Explain (in human-readable terms) why this transaction might be risky
3. Flag any linguistic patterns that suggest fraud/social engineering
4. Assign a small risk boost (0.0-0.2, where 0.2 is maximum)

OUTPUT JSON ONLY (no markdown, no explanation outside JSON):
{
  "behavioral_flags": ["list of flags found"],
  "explanation": "Plain language explanation for human reviewer",
  "risk_boost": 0.0,
  "confidence": "high"
}"""


class LMLayer:
    """
    LLM advisory layer. Supports multiple providers:
      - 'gemini'  → Google Gemini (free tier via google-generativeai)
      - 'openai'  → OpenAI GPT (paid)
      - anything else → silent fallback (no-op)

    THIS LAYER CANNOT APPROVE OR DENY TRANSACTIONS.
    It returns advisory signals only (max risk_boost = 0.2).
    """

    def __init__(self, provider: str, api_key: str = None):
        self.provider = provider.lower()
        self.api_key = api_key or self._resolve_api_key()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _resolve_api_key(self) -> str | None:
        """Pick the right env var based on provider."""
        if self.provider == 'gemini':
            return os.getenv('GEMINI_API_KEY')
        elif self.provider == 'openai':
            return os.getenv('OPENAI_API_KEY')
        return None

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    async def evaluate_async(self, transaction: dict, user: dict, signals_from_previous_layers: dict) -> dict:
        """Non-blocking wrapper — runs the sync evaluate() in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.evaluate,
            transaction,
            user,
            signals_from_previous_layers,
        )

    def evaluate(self, transaction: dict, user: dict, signals_from_previous_layers: dict) -> dict:
        """
        THIS FUNCTION CANNOT APPROVE TRANSACTIONS.
        Returns advisory extraction flags only. Max boost 0.2.
        """
        notes = transaction.get('notes', '')
        if not notes:
            return self._default_response(reason="No transaction notes provided for analysis.")

        context = {
            'notes': notes,
            'amount': transaction.get('amount'),
            'signals': signals_from_previous_layers,
        }

        analysis = self._call_llm(context)

        return {
            'behavioral_flags': analysis.get('flags', []),
            'explanation': analysis.get('narrative', ''),
            'risk_boost': analysis.get('risk_boost', 0.0),
            'warning': 'LLM output is advisory only, not a decision',
        }

    # ------------------------------------------------------------------ #
    # Provider dispatch                                                     #
    # ------------------------------------------------------------------ #

    def _call_llm(self, context: dict) -> dict:
        if self.provider == 'gemini':
            return self._call_gemini(context)
        elif self.provider == 'openai':
            return self._call_openai(context)
        else:
            return self._default_response_dict(f"Provider '{self.provider}' not supported")

    # ------------------------------------------------------------------ #
    # Gemini (free tier)                                                   #
    # ------------------------------------------------------------------ #

    def _call_gemini(self, context: dict) -> dict:
        """
        Calls Google Gemini via the new google-genai SDK.
        Free tier: 15 RPM / 1M tokens per day.
        """
        try:
            from google import genai
            from google.genai import types

            if not self.api_key:
                return self._default_response_dict("GEMINI_API_KEY not set")

            client = genai.Client(api_key=self.api_key)
            prompt = f"{SYSTEM_PROMPT}\n\nTransaction context:\n{json.dumps(context, default=str)}"

            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=512,
                    response_mime_type="application/json",
                )
            )
            content = response.text.strip()

            analysis = json.loads(content)

            return {
                'flags': analysis.get('behavioral_flags', []),
                'narrative': analysis.get('explanation', ''),
                'risk_boost': min(float(analysis.get('risk_boost', 0.0)), 0.2),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned non-JSON response: {e}")
            return self._default_response_dict("Gemini response was not valid JSON")
        except Exception as e:
            logger.warning(f"Gemini API error: {e}")
            return self._default_response_dict(f"Gemini API error: {e}")

    # ------------------------------------------------------------------ #
    # OpenAI (paid fallback)                                               #
    # ------------------------------------------------------------------ #

    def _call_openai(self, context: dict) -> dict:
        try:
            from openai import OpenAI

            if not self.api_key:
                return self._default_response_dict("OPENAI_API_KEY not set")

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context, default=str)},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            analysis = json.loads(content)

            return {
                'flags': analysis.get('behavioral_flags', []),
                'narrative': analysis.get('explanation', ''),
                'risk_boost': min(float(analysis.get('risk_boost', 0.0)), 0.2),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"OpenAI returned non-JSON response: {e}")
            return self._default_response_dict("OpenAI response was not valid JSON")
        except Exception as e:
            logger.warning(f"OpenAI API error: {e}")
            return self._default_response_dict(f"OpenAI API error: {e}")

    # ------------------------------------------------------------------ #
    # Fallback helpers                                                      #
    # ------------------------------------------------------------------ #

    def _default_response_dict(self, reason: str = "LLM service unavailable") -> dict:
        return {
            'flags': [],
            'narrative': reason,
            'risk_boost': 0.0,
        }

    def _default_response(self, reason: str = "LLM service unavailable") -> dict:
        base = self._default_response_dict(reason)
        return {
            'behavioral_flags': base['flags'],
            'explanation': base['narrative'],
            'risk_boost': base['risk_boost'],
            'warning': 'LLM output is advisory only, not a decision',
        }
