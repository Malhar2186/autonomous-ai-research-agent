import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from research_agent.config import config
from research_agent.llm.client import LLMClient
from research_agent.tools.search_tools import unified_search
from research_agent.tools.scraper_tools import scrape_url
from research_agent.agent.prompts import (
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT,
    EXTRACT_SYSTEM_PROMPT,
    EXTRACT_USER_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT,
)

logger = logging.getLogger(__name__)
console = Console()


def clean_json_text(text: str) -> str:
    """Extracts JSON substring from markdown fences or text."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


class AutonomousResearcher:
    """
    Autonomous AI Research Agent that plans, searches, scrapes, reflects,
    and synthesizes comprehensive research reports.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        self.llm = LLMClient(provider=provider, model=model)
        self.output_dir = output_dir or config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sources_consulted: List[Dict[str, str]] = []
        self.all_evidence: List[Dict[str, Any]] = []

    def plan(self, topic: str, depth: str = "standard", include_academic: bool = False) -> Dict[str, Any]:
        """
        Formulates an autonomous research plan and sub-questions.
        """
        console.print(Panel(f"[bold cyan]Planning Research for:[/bold cyan] {topic}\n[dim]Depth: {depth} | Academic Sources: {include_academic}[/dim]", title="Step 1: Research Planning"))

        prompt = PLAN_USER_PROMPT.format(
            topic=topic,
            depth=depth,
            include_academic=include_academic,
        )
        raw_response = self.llm.generate(prompt, system_prompt=PLAN_SYSTEM_PROMPT)
        cleaned = clean_json_text(raw_response)

        try:
            plan = json.loads(cleaned)
        except Exception:
            logger.warning("Failed to parse JSON research plan from LLM. Using fallback heuristic plan.")
            plan = {
                "title": f"Comprehensive Research on {topic}",
                "summary": f"In-depth investigation of {topic}",
                "sub_questions": [
                    f"What is {topic} and what are its key mechanisms and principles?",
                    f"What are the latest developments, applications, and real-world implementations of {topic}?",
                    f"What challenges, limitations, and future directions exist for {topic}?",
                ],
                "search_queries": [
                    f"{topic} overview fundamentals",
                    f"{topic} latest developments applications 2025 2026",
                    f"{topic} challenges future outlook",
                ],
            }

        table = Table(title="Research Sub-Questions & Queries", border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Sub-Question", style="green")
        table.add_column("Search Query", style="yellow")

        for idx, (q, query) in enumerate(zip(plan.get("sub_questions", []), plan.get("search_queries", [])), start=1):
            table.add_row(str(idx), q, query)

        console.print(table)
        return plan

    def investigate_subquestion(
        self,
        sub_question: str,
        initial_query: str,
        depth: str = "standard",
        include_academic: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Autonomous loop for a single sub-question:
        Search -> Scrape -> Evaluate -> Gap-Detection -> (Optional Follow-Up Search)
        """
        console.print(f"\n[bold green]➔ Investigating:[/bold green] {sub_question}")
        sub_evidence = []

        max_results = 5 if depth == "deep" else 3
        max_scrapes = 3 if depth == "deep" else 2

        # 1. Search
        search_results = unified_search(
            initial_query,
            max_results=max_results,
            include_academic=include_academic,
        )
        console.print(f"  [cyan]Found {len(search_results)} search results for query:[/cyan] '{initial_query}'")

        # 2. Scrape & Extract
        scraped_count = 0
        follow_up_needed = None

        for item in search_results:
            url = item.get("url", "")
            title = item.get("title", "")
            if not url or any(s["url"] == url for s in self.sources_consulted):
                continue

            if scraped_count >= max_scrapes:
                break

            console.print(f"  [blue]Scraping & Reading:[/blue] {title[:60]}... ([dim]{url}[/dim])")
            scraped = scrape_url(url)
            self.sources_consulted.append({"title": title, "url": url})
            scraped_count += 1

            if not scraped["success"]:
                continue

            # LLM Analysis of scraped content
            extract_prompt = EXTRACT_USER_PROMPT.format(
                question=sub_question,
                url=url,
                title=title,
                content=scraped["text"],
            )
            raw_eval = self.llm.generate(extract_prompt, system_prompt=EXTRACT_SYSTEM_PROMPT)
            cleaned_eval = clean_json_text(raw_eval)

            try:
                eval_data = json.loads(cleaned_eval)
            except Exception:
                # Heuristic fallback if offline
                eval_data = {
                    "key_findings": [scraped["text"][:300] + "..."],
                    "relevance_score": 7,
                    "credibility_notes": "Scraped web source",
                    "gap_identified": "",
                    "follow_up_query": "",
                }

            findings = eval_data.get("key_findings", [])
            score = eval_data.get("relevance_score", 5)

            if findings and score >= 4:
                console.print(f"    [green]✓ Extracted {len(findings)} key findings (Relevance: {score}/10)[/green]")
                sub_evidence.append({
                    "sub_question": sub_question,
                    "url": url,
                    "title": title,
                    "findings": findings,
                    "credibility": eval_data.get("credibility_notes", ""),
                })

            if eval_data.get("gap_identified") and eval_data.get("follow_up_query"):
                follow_up_needed = eval_data["follow_up_query"]

        # 3. Autonomous Reflection & Gap-filling (if deep mode and gap discovered)
        if depth in ("standard", "deep") and follow_up_needed:
            console.print(f"  [magenta]⚡ Autonomous Gap Reflection:[/magenta] Need deeper data. Triggering follow-up query: '{follow_up_needed}'")
            follow_up_results = unified_search(follow_up_needed, max_results=2, include_academic=include_academic)
            for item in follow_up_results:
                url = item.get("url", "")
                if url and not any(s["url"] == url for s in self.sources_consulted):
                    scraped = scrape_url(url)
                    self.sources_consulted.append({"title": item.get("title", ""), "url": url})
                    if scraped["success"]:
                        sub_evidence.append({
                            "sub_question": sub_question,
                            "url": url,
                            "title": item.get("title", ""),
                            "findings": [f"Follow-up context: {scraped['text'][:400]}..."],
                            "credibility": "Follow-up verification",
                        })
                    break

        return sub_evidence

    def synthesize(self, topic: str, depth: str, plan: Dict[str, Any]) -> str:
        """
        Synthesizes all gathered evidence and sources into a final report.
        """
        console.print(Panel("[bold yellow]Synthesizing final research report with cross-source validation...[/bold yellow]", title="Step 3: Synthesis"))

        evidence_blocks = []
        for item in self.all_evidence:
            findings_str = "\n".join(f"- {f}" for f in item["findings"])
            evidence_blocks.append(
                f"### Evidence for Sub-Question: {item['sub_question']}\n"
                f"Source: [{item['title']}]({item['url']})\n"
                f"Credibility Notes: {item.get('credibility', 'N/A')}\n"
                f"Findings:\n{findings_str}\n"
            )

        evidence_text = "\n\n".join(evidence_blocks) if evidence_blocks else "No direct evidence collected."
        sources_text = "\n".join(f"- [{s['title']}]({s['url']})" for s in self.sources_consulted)

        synthesis_prompt = SYNTHESIS_USER_PROMPT.format(
            topic=topic,
            depth=depth,
            evidence_text=evidence_text,
            sources_text=sources_text,
        )

        report = self.llm.generate(synthesis_prompt, system_prompt=SYNTHESIS_SYSTEM_PROMPT)
        return report

    def save_report(self, topic: str, report_content: str) -> Path:
        """
        Saves the markdown report and returns the file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^\w\-]", "_", topic.lower()).strip("_")[:40]
        filename = f"research_{slug}_{timestamp}.md"
        report_path = self.output_dir / filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        console.print(f"\n[bold green]✔ Research Report Saved:[/bold green] [cyan]{report_path.resolve()}[/cyan]")
        return report_path.resolve()

    def run(self, topic: str, depth: str = "standard", include_academic: bool = False) -> Path:
        """
        Executes the end-to-end autonomous research workflow.
        """
        start_time = datetime.now()
        console.print(f"\n[bold magenta]=====================================================[/bold magenta]")
        console.print(f"[bold magenta]     AUTONOMOUS AI RESEARCH AGENT INITIALIZED       [/bold magenta]")
        console.print(f"[bold magenta]=====================================================[/bold magenta]\n")
        console.print(f"[bold]Target Topic:[/bold] {topic}")
        console.print(f"[bold]Provider:[/bold] {self.llm.provider} ([dim]Model: {self.llm.model}[/dim])\n")

        # Step 1: Plan
        plan = self.plan(topic, depth=depth, include_academic=include_academic)

        # Step 2: Autonomous Investigation
        sub_questions = plan.get("sub_questions", [])
        search_queries = plan.get("search_queries", [])

        console.print(Panel("[bold green]Executing Autonomous Investigation Loop...[/bold green]", title="Step 2: Investigation"))

        for idx, (sub_q, query) in enumerate(zip(sub_questions, search_queries), start=1):
            evidence = self.investigate_subquestion(
                sub_question=sub_q,
                initial_query=query,
                depth=depth,
                include_academic=include_academic,
            )
            self.all_evidence.extend(evidence)

        # Step 3: Synthesis
        report = self.synthesize(topic, depth=depth, plan=plan)

        # Step 4: Save & Summary
        report_path = self.save_report(topic, report)

        elapsed = (datetime.now() - start_time).total_seconds()
        console.print(Panel(
            f"[bold green]Research Complete in {elapsed:.1f}s![/bold green]\n"
            f"Sources Consulted: [cyan]{len(self.sources_consulted)}[/cyan]\n"
            f"Evidence Items Extracted: [cyan]{len(self.all_evidence)}[/cyan]\n"
            f"Output Report: [bold underline]{report_path}[/bold underline]",
            title="Summary",
            border_style="green",
        ))

        return report_path

