import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class SupplierRiskLLMAgent:
    """
    LLM layer for explaining structured supplier-risk results.

    The deterministic Supplier Intelligence Agent remains responsible
    for calculating supplier-risk scores.

    This agent does not calculate supplier-risk scores and does not
    make payment or financing decisions.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")

        self.client: OpenAI | None = None

        if api_key:
            self.client = OpenAI(api_key=api_key)

    def explain_supplier_risk(
        self,
        supplier_risk: dict[str, Any],
    ) -> str:
        """
        Generate a concise explanation of deterministic
        supplier-risk information.

        If the OpenAI API is unavailable, a deterministic
        fallback explanation is returned.
        """

        if self.client is None:
            return self._fallback_explanation(supplier_risk)

        prompt = f"""
You are a Supplier Risk Analysis Assistant.

Analyze the following deterministic supplier-risk data.

Supplier risk:
{supplier_risk}

Explain:
1. The overall supplier risk.
2. The most important risk factors.
3. Any downstream or cascade implications.

Important rules:
- Treat all supplied numerical values as authoritative.
- Do not calculate, modify, or reinterpret the supplied scores.
- Do not invent missing data.
- Do not recommend payment actions.
- Do not recommend financing actions.
- Do not make decisions for the Decision Engine.
- Only explain the supplier-risk information provided.
"""

        try:
            response = self.client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
            )

            return response.output_text

        except Exception:
            # The LLM is an optional explanation layer.
            # Supplier-risk analysis must continue working
            # even if the external API is unavailable.
            return self._fallback_explanation(supplier_risk)

    def _fallback_explanation(
        self,
        supplier_risk: dict[str, Any],
    ) -> str:
        """
        Deterministic fallback explanation used when the
        OpenAI API is unavailable.
        """

        risk_level = supplier_risk.get(
            "risk_level",
            "UNKNOWN",
        )

        criticality = supplier_risk.get(
            "criticality_score",
            0,
        )

        distress = supplier_risk.get(
            "distress_score",
            0,
        )

        disruption = supplier_risk.get(
            "disruption_probability",
            0,
        )

        cascade = supplier_risk.get(
            "cascade_risk_score",
            0,
        )

        affected = supplier_risk.get(
            "affected_supplier_ids",
            [],
        )

        return (
            f"Supplier risk level: {risk_level}. "
            f"Criticality score: {criticality}. "
            f"Distress score: {distress}. "
            f"Disruption probability: {disruption}. "
            f"Cascade risk score: {cascade}. "
            f"Downstream affected suppliers: {len(affected)}."
        )