import streamlit as st
import asyncio
from openai_agent import agent, Runner, Profile, Company, linkd_client
import nest_asyncio

# Apply nest_asyncio to allow running asyncio event loops within Streamlit
nest_asyncio.apply()

st.set_page_config(layout="wide")

st.title("Linkd Search Agent")

# --- Search Input ---
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Search Query:", placeholder="e.g., 'Software Engineers at AI startups'")
with col2:
    limit = st.number_input("Max Results:", min_value=1, max_value=200, value=10)

search_button = st.button("Search")

# --- Search Execution and Results ---
if search_button and query:
    with st.spinner("Searching..."):
        try:
            # Run the agent to get the search plan
            agent_result = asyncio.run(Runner.run(agent, query))
            search_type = agent_result.final_output.searchType
            search_queries = agent_result.final_output.query

            st.subheader("Search Plan")
            st.write(f"**Type:** {search_type}")
            st.write("**Queries:**")
            st.code("\n".join(search_queries), language=None)

            st.subheader("Results")

            if search_type == "people":
                profiles_by_id = {}
                remaining_limit = limit
                progress_bar = st.progress(0.0)
                total_queries = len(search_queries)
                profiles_found = 0

                for i, q in enumerate(search_queries):
                    if remaining_limit <= 0:
                        break

                    search_result = asyncio.run(linkd_client.search_users(q, remaining_limit))
                    
                    current_profiles = 0
                    for result in search_result.get('results', []):
                        # Ensure profile data exists before creating Profile object
                        if result.get('profile'):
                            profile = Profile(**result['profile'])
                            if profile.id not in profiles_by_id:
                                profiles_by_id[profile.id] = profile
                                remaining_limit -= 1
                                current_profiles += 1
                                if remaining_limit <= 0:
                                    break
                        else:
                            st.warning(f"Skipping result due to missing profile data for query: {q}")
                            
                    profiles_found += current_profiles
                    progress_bar.progress((i + 1) / total_queries, text=f"Ran query {i+1}/{total_queries}. Found {profiles_found} unique profiles so far.")


                progress_bar.empty() # Remove progress bar after completion
                
                st.write(f"Found {len(profiles_by_id)} unique profiles:")
                
                # Display profiles in cards
                cols = st.columns(3) # Adjust number of columns as needed
                col_idx = 0
                for profile in profiles_by_id.values():
                    with cols[col_idx % len(cols)]:
                        with st.container(border=True):
                            st.subheader(profile.name or "N/A")
                            if profile.profile_picture_url:
                                st.image(profile.profile_picture_url, width=100)
                            st.write(f"**Headline:** {profile.headline or 'N/A'}")
                            st.write(f"**Location:** {profile.location or 'N/A'}")
                            st.write(f"**Title:** {profile.title or 'N/A'}")
                            st.link_button("View Profile", profile.linkedin_url or "#")


                    col_idx += 1


            elif search_type == "company":
                if search_queries:
                    search_result = asyncio.run(linkd_client.search_companies(search_queries[0], limit))
                    results = search_result.get('results', [])
                    companies = []
                    for result in results:
                        companies.append(Company(**result))

                    st.write(f"Found {len(companies)} companies:")

                    # Display companies in cards
                    cols = st.columns(3) # Adjust number of columns as needed
                    col_idx = 0
                    for company in companies:
                        with cols[col_idx % len(cols)]:
                            with st.container(border=True):
                                st.subheader(company.company_name or "N/A")
                                if company.linkedin_logo_url:
                                    st.image(company.linkedin_logo_url, width=100)
                                st.write(f"**Industry:** {company.linkedin_industry or 'N/A'}")
                                st.write(f"**Headquarters:** {company.headquarters or 'N/A'}")
                                st.write(f"**Size:** {company.employee_count_range or 'N/A'}")
                                st.write(f"**Description:** {company.linkedin_company_description or 'N/A'}")
                                st.link_button("View Company", company.linkedin_profile_url or "#")
                        col_idx += 1
                else:
                    st.warning("Agent did not provide any company search queries.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.exception(e) # Show detailed traceback

elif search_button and not query:
    st.warning("Please enter a search query.")
