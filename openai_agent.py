from agents import Agent, ModelSettings, Runner, function_tool, set_default_openai_key
from linkd import LinkdClient, Profile, Company
from pydantic import BaseModel
from typing import Literal
import asyncio
import argparse
import requests
import os
import dotenv

dotenv.load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINKD_API_KEY = os.getenv("LINKD_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

set_default_openai_key(OPENAI_API_KEY)

linkd_client = LinkdClient(api_key=LINKD_API_KEY)

@function_tool
async def find_companies(query: str, limit: int | None = None) -> str:
    """Find companies matching a description.
    
    Args:
        query: The search query string
        limit: The number of results to return (max 100)
    """
    print(f"Searching for companies: {query} with limit: {limit}")
    results = (await linkd_client.search_companies(query, limit or 10))['results']

    if not results:
        return "No results found"

    # Create TSV header with base fields and criteria columns
    base_headers = ["Name", "Type", "Headquarters", "Employee Count Range", "Description", 
                   "Year Founded", "Category", "Industry", "Specialty", "Relevance Score"]

    # Get criteria keys from the first company
    criteria_keys = list(results[0].get('criteria', {}).keys())

    # Add criteria columns to headers
    all_headers = base_headers + criteria_keys
    tsv_lines = ['\t'.join(all_headers)]

    # Add each company as a TSV row
    for company in results:
        # Base company info
        row = [
            company['company_name'] or '',
            company['company_type'] or '',
            company['headquarters'] or '',
            company['employee_count_range'] or '',
            company['linkedin_company_description'] or '',
            (company['year_founded'] or '')[:4],
            company['crunchbase_category'] or '',
            company['linkedin_industry'] or '',
            company['linkedin_speciality'] or '',
            f"{company['relevance_score']:.3f}"
        ]

        # Add criteria values
        criteria = company.get('criteria', {})
        for key in criteria_keys:
            row.append(criteria.get(key, ''))

        tsv_lines.append('\t'.join(row))

    return '\n'.join(tsv_lines)

# @function_tool
async def search_users(query: str, max_results: int = 10) -> list[Profile]:
    """Search for people on LinkedIn.
    
    Args:
        query: The search query string
        max_results: The number of results to return (default 10)
    """
    results = await linkd_client.search_users(query, max_results)
    return [Profile(**result['profile']) for result in results['results']]

# @function_tool
async def search_perplexity(query: str) -> str:
    """Search the web using Perplexity.
    
    Args:
        query: The search query string
    """
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}"}
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Be precise and concise."},
            {"role": "user", "content": query},
        ]
    }
    response = requests.post(url, headers=headers, json=payload).json()
    return response["choices"][0]["message"]["content"]

class SearchQuery(BaseModel):
    searchType: Literal["people", "company"]
    query: list[str]


agent = Agent(
    name="Linkd search agent",
    model="gpt-4.1-mini",
    tools=[find_companies],
    instructions="""You are a LinkedIn search agent. Given a search query, decide whether the user is looking for people or companies. Then, output a natural language search query to the corresponding endpoint.

If the user is looking for people at a class of companies (for instance, "engineers at AI unicorns"), you may use the find_companies tool to find companies matching that description (for instance, "AI unicorns"). In this case, output a list of people search queries (one for each company returned).
You do not need to use the find_companies tool if the user is looking for people at a single company, or searching for companies. In those cases, output a query directly.
Use Perplexity if you need to search the web for general information.
""",
    output_type=SearchQuery,
    model_settings=ModelSettings(temperature=0)
)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LinkedIn search agent")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results (default: 10)")
    args = parser.parse_args()
    
    # Run the agent
    result = await Runner.run(agent, args.query)

    # Print the final output without relying on specific structure
    print("\n=== Search Queries ===")
    print(f"Search Type: {result.final_output.searchType}")
    print(f"Queries: {result.final_output.query}")
    
    if result.final_output.searchType == "people":
        profiles_by_id = {}
        remaining_limit = args.limit
        
        # Search sequentially until we hit the limit
        for query in result.final_output.query:
            if remaining_limit <= 0:
                break
                
            search_result = await linkd_client.search_users(query, remaining_limit)
            for result in search_result['results']:
                profile = Profile(**result['profile'])
                if profile.id not in profiles_by_id:
                    profiles_by_id[profile.id] = profile
                    remaining_limit -= 1
                    if remaining_limit <= 0:
                        break
        
        print(f"\n=== Results ({len(profiles_by_id)} unique profiles) ===")
        print(list(profiles_by_id.values()))
    else:
        search_result = await linkd_client.search_companies(result.final_output.query[0], args.limit)
        results = search_result['results']
        companies = [Company(**result) for result in results]
        print(f"\n=== Results ({len(companies)} companies) ===")
        print(companies)

if __name__ == "__main__":
    asyncio.run(main())