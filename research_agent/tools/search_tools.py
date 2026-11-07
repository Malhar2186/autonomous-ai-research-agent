import logging
import warnings
from typing import List, Dict, Any
from research_agent.config import config

# Suppress library rename warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)


def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Performs web search using DDGS / DuckDuckGo.
    """
    results = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "source": "duckduckgo",
                })
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    return results


def search_wikipedia(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches Wikipedia articles and returns summaries.
    """
    results = []
    try:
        import wikipedia
        wikipedia.set_user_agent("AutonomousResearchAgent/1.0 (https://github.com/agent/research-bot)")
        search_titles = wikipedia.search(query, results=max_results)
        for title in search_titles:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                summary = page.summary
                if len(summary) > 800:
                    summary = summary[:800] + "..."
                results.append({
                    "title": f"Wikipedia: {page.title}",
                    "url": page.url,
                    "snippet": summary,
                    "source": "wikipedia",
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")
    return results


def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches arXiv for scientific research papers and abstracts.
    """
    results = []
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        for result in client.results(search):
            summary = result.summary.replace("\n", " ").strip()
            if len(summary) > 800:
                summary = summary[:800] + "..."
            results.append({
                "title": f"arXiv: {result.title}",
                "url": result.entry_id,
                "snippet": f"Authors: {', '.join(a.name for a in result.authors[:3])}. Abstract: {summary}",
                "source": "arxiv",
            })
    except Exception as e:
        logger.warning(f"arXiv search error: {e}")
    return results


def unified_search(query: str, max_results: int = 5, include_academic: bool = False) -> List[Dict[str, Any]]:
    """
    Performs unified search combining DuckDuckGo, Wikipedia, and optionally arXiv.
    Deduplicates URLs and snippets.
    """
    combined = []
    seen_urls = set()

    # 1. DuckDuckGo primary web search
    ddg_res = search_duckduckgo(query, max_results=max_results)
    for r in ddg_res:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            combined.append(r)

    # 2. Wikipedia lookup (if query is conceptual or informative)
    if len(combined) < max_results:
        wiki_res = search_wikipedia(query, max_results=2)
        for r in wiki_res:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                combined.append(r)

    # 3. Academic papers if requested or if topic looks technical/scientific
    if include_academic:
        arxiv_res = search_arxiv(query, max_results=3)
        for r in arxiv_res:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                combined.append(r)

    return combined[:max_results]

