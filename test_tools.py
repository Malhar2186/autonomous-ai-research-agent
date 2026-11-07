"""
Unit / Integration tests for Research Agent tools
"""

from research_agent.tools.scraper_tools import scrape_url
from research_agent.tools.search_tools import search_duckduckgo, search_wikipedia, unified_search


def test_wikipedia():
    print("Testing Wikipedia search...")
    res = search_wikipedia("Artificial Intelligence", max_results=2)
    print(f"Wikipedia returned {len(res)} results.")
    assert len(res) > 0
    assert "url" in res[0]
    print(f"Sample Wiki title: {res[0]['title']}")


def test_duckduckgo():
    print("Testing DuckDuckGo search...")
    res = search_duckduckgo("Python programming language", max_results=2)
    print(f"DuckDuckGo returned {len(res)} results.")
    if res:
        print(f"Sample DDG title: {res[0]['title']}")


def test_scraper():
    print("Testing Scraper on python.org...")
    scraped = scrape_url("https://www.python.org", max_chars=500)
    print(f"Scrape success: {scraped['success']}, title: {scraped['title']}")
    print(f"Snippet:\n{scraped['text'][:150]}...")
    assert scraped["success"]


if __name__ == "__main__":
    test_wikipedia()
    test_duckduckgo()
    test_scraper()
    print("All tool tests passed successfully!")

