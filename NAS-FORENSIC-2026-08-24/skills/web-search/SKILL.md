---
name: web-search
description: Search the live web and return summarised answers with sources.
---
## Instructions
When the user asks for web search, use this skill.
You can search by describing what you want to find.

Example:
User: "Search for the latest AI news"
You: Use the web-search skill to fetch recent AI articles.

**Implementation:**
- Use the `/web_search` endpoint if available.
- Otherwise, use DuckDuckGo or SearXNG.
- Always include sources.
