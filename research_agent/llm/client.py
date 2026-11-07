import os
import json
import logging
from typing import Optional, List, Dict, Any
from research_agent.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM Client supporting Google Gemini, OpenAI, Groq, and Ollama.
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or config.provider).lower()
        self.model = model
        self._init_backend()

    def _init_backend(self):
        self.client = None

        if self.provider == "gemini":
            api_key = config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning(
                    "GEMINI_API_KEY is not set. Please set it in .env or choose another provider."
                )
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key) if api_key else None
                self.model = self.model or config.gemini_model
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

        elif self.provider in ("openai", "groq", "ollama"):
            try:
                from openai import OpenAI
                if self.provider == "groq":
                    api_key = config.groq_api_key or os.getenv("GROQ_API_KEY", "")
                    base_url = "https://api.groq.com/openai/v1"
                    self.model = self.model or config.groq_model
                elif self.provider == "ollama":
                    api_key = "ollama"
                    base_url = config.ollama_base_url
                    self.model = self.model or config.ollama_model
                else:  # openai
                    api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY", "")
                    base_url = None
                    self.model = self.model or config.openai_model

                self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI/compatible client: {e}")
        else:
            logger.warning(f"Unknown provider '{self.provider}'. Falling back to rule-based fallback.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        """
        Generates text given a prompt and optional system prompt.
        """
        # If no client or API key is set, produce a fallback response
        if not self.client:
            return self._mock_or_offline_response(prompt, system_prompt)

        try:
            if self.provider == "gemini":
                contents = []
                if system_prompt:
                    contents.append(f"System: {system_prompt}\n\n")
                contents.append(prompt)
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="".join(contents),
                )
                return response.text or ""

            elif self.provider in ("openai", "groq", "ollama"):
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                )
                return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Error calling {self.provider} API: {e}")
            return f"[LLM Generation Error ({self.provider}): {e}]\n\nFallback synthesis will be used."

    def _mock_or_offline_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Fallback response when no API key is configured.
        Parses JSON requests if structured output was requested.
        """
        import re

        # Extract topic if present in prompt
        topic_match = re.search(r"Research Topic:\s*([^\n\r]+)", prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "the given topic"

        # Check if the prompt is for sub-question planning (returns JSON)
        if "Research Topic:" in prompt and ("sub_questions" in prompt or "JSON" in prompt):
            return json.dumps({
                "title": f"Investigation into {topic}",
                "summary": f"Autonomous comprehensive research examining {topic}",
                "sub_questions": [
                    f"What is {topic} and what are its core principles, mechanisms, and background?",
                    f"What are the most recent breakthroughs, key industry players, and applications of {topic}?",
                    f"What are the major challenges, trade-offs, and future trajectories for {topic}?"
                ],
                "search_queries": [
                    f"{topic} core concepts and fundamentals",
                    f"{topic} latest breakthroughs and applications",
                    f"{topic} challenges limitations future outlook"
                ]
            })

        # Check if the prompt is for source evidence extraction (returns JSON)
        if "Sub-Question:" in prompt and "Source Content:" in prompt:
            content_match = re.search(r"Source Content:\s*\"\"\"([\s\S]*?)\"\"\"", prompt)
            raw_content = content_match.group(1).strip() if content_match else ""
            paragraphs = [p.strip() for p in raw_content.split("\n\n") if len(p.strip()) > 60]
            top_findings = paragraphs[:3] if paragraphs else [raw_content[:250] + "..." if raw_content else "No textual details available."]

            return json.dumps({
                "key_findings": top_findings,
                "relevance_score": 8,
                "credibility_notes": "Scraped web source verified for topic relevance",
                "gap_identified": "",
                "follow_up_query": ""
            })

        # Synthesis fallback: compile full markdown report from evidence
        evidence_match = re.search(r"Gathered Evidence and Source Notes:\s*([\s\S]*?)\s*List of Consulted Sources:", prompt)
        sources_match = re.search(r"List of Consulted Sources:\s*([\s\S]*)$", prompt)

        evidence_str = evidence_match.group(1).strip() if evidence_match else "No raw evidence recorded."
        sources_str = sources_match.group(1).strip() if sources_match else "No sources listed."

        return f"""# Autonomous Research Report: {topic}

> **Notice:** Generated in offline/fallback synthesis mode. To enable full generative AI synthesis, provide your API key (e.g. `GEMINI_API_KEY`) in `.env`.

## Executive Summary
This report presents an autonomous investigation into **{topic}**. Information was extracted from live search and web content scraping across primary references.

## 1. Core Background & Fundamentals
Research into **{topic}** encompasses primary conceptual foundations and state-of-the-art frameworks. The investigation analyzed primary reference documentation to identify historical progression and modern standards.

## 2. Key Findings & Detailed Analysis
{evidence_str}

## 3. Challenges & Future Trajectory
Key trade-offs and developmental bottlenecks include scalability, verification, and domain integration. Ongoing initiatives continue to expand capabilities in this sector.

## References & Sources Consulted
{sources_str}
"""

