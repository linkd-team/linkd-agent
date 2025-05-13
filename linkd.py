from typing import Dict, List, Optional
from dataclasses import dataclass
import requests

@dataclass
class Profile:
    id: str
    name: str
    location: str
    headline: str
    description: Optional[str] = None
    title: Optional[str] = None
    profile_picture_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    websites: Optional[List[Dict[str, str]]] = None
    criteria: Optional[Dict[str, str]] = None

@dataclass
class Company:
    id: int
    company_id: int
    company_name: str
    company_type: str
    company_website: str
    headquarters: str
    employee_count_range: str
    linkedin_company_description: str
    relevance_score: float
    criteria: Optional[Dict[str, str]] = None
    company_website_domain: Optional[str] = None
    hq_country: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    linkedin_logo_url: Optional[str] = None
    year_founded: Optional[str] = None
    crunchbase_category: Optional[str] = None
    linkedin_industry: Optional[str] = None
    linkedin_speciality: Optional[str] = None
    linkedin_headcount: Optional[int] = None

class LinkdError(Exception):
    """Base exception for Linkd API errors"""

class LinkdClient:
    BASE_URL = "https://search.linkd.inc/api"
    
    def __init__(self, api_key: str):
        """Initialize the Linkd API client.
        
        Args:
            api_key (str): Your Linkd API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and raise appropriate exceptions.
        
        Args:
            response (requests.Response): The API response
            
        Returns:
            Dict: The JSON response data
            
        Raises:
            LinkdError: If the API returns an error
        """
        if response.status_code == 200:
            return response.json()
        
        error_messages = {
            400: "Bad Request - Invalid parameters",
            401: "Unauthorized - Invalid or missing API key",
            402: "Payment Required - Insufficient credits",
            422: "Validation Error - Missing required fields",
            500: "Internal Server Error",
            503: "Service Unavailable"
        }
        
        error_msg = error_messages.get(response.status_code, "Unknown error")
        raise LinkdError(f"{error_msg}: {response.text}")

    async def search_users(
        self,
        query: str,
        limit: int = 10,
        school: Optional[List[str]] = None
    ) -> Dict:
        """Search for users based on a query.
        
        Args:
            query (str): The search query string
            limit (int, optional): Maximum number of results to return (max: 30). Defaults to 10.
            school (List[str], optional): Filter results by school name(s)
            
        Returns:
            Dict: Search results containing profiles and metadata
            
        Raises:
            LinkdError: If the API request fails
        """
        # if limit > 30:
        #     raise ValueError("Limit cannot exceed 30")
            
        params = {
            "query": query,
            "limit": limit
        }
        if school:
            params["school"] = school
            
        response = self.session.get(f"{self.BASE_URL}/search/users", params=params)
        return self._handle_response(response)

    async def search_companies(
        self,
        query: str,
        limit: int = 10
    ) -> Dict:
        """Search for companies based on a query.
        
        Args:
            query (str): The search query string
            limit (int, optional): Maximum number of results to return (max: 30). Defaults to 10.
            
        Returns:
            Dict: Search results containing companies and metadata
            
        Raises:
            LinkdError: If the API request fails
        """
        # if limit > 30:
        #     raise ValueError("Limit cannot exceed 30")
            
        params = {
            "query": query,
            "limit": limit
        }
        
        response = self.session.get(f"{self.BASE_URL}/search/companies", params=params)
        return self._handle_response(response)
