import os
import json
import logging
import re
from typing import List, Union, Optional, Dict, Any
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from firecrawl import FirecrawlApp as FireCrawlClient

# Configure basic logging for the module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("url_analyzer")

# Get FireCrawl API key from environment variables
# This key is required for accessing the FireCrawl service
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Initialize FireCrawl client with API key
# The client will be used for all URL content extraction operations
firecrawl_client = None
if FIRECRAWL_API_KEY:
    try:
        firecrawl_client = FireCrawlClient(api_key=FIRECRAWL_API_KEY)
        logger.info("FireCrawl client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing FireCrawl client: {str(e)}")

class NewsContent(BaseModel):
    """
    Schema defining the structure of extracted news content.
    This model is used to validate and structure the data returned by FireCrawl.
    
    Fields:
        title: The main headline of the news article
        main_text: The complete body text of the article
        author: The name of the article's author (optional)
        published_date: The date when the article was published (optional)
    """
    title: str = Field(..., description="The main title of the news article")
    main_text: str = Field(..., description="The main content of the news article")
    author: Optional[str] = Field(None, description="Author of the article if available")
    published_date: Optional[str] = Field(None, description="Publication date if available")

class URLAnalyzerInput(BaseModel):
    """
    Input schema for the URLAnalyzer tool.
    Defines the expected format of input URLs that can be processed.
    
    Fields:
        url_input: Can be either a single URL string or a list of URLs to analyze
    """
    url_input: Optional[Union[str, List[str]]] = Field(None, description="Either a single URL string or a list of URL strings to analyze")

class URLAnalyzer(BaseTool):
    """
    Tool for extracting main content from news articles using FireCrawl.
    This tool is designed to work with the CrewAI framework and provides
    a standardized way to extract and structure news content from URLs.
    """
    name: str = "Analyze URL Content"
    description: str = "Extracts main content from news articles using FireCrawl"
    args_schema: type[BaseModel] = URLAnalyzerInput
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from a text string"""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return re.findall(url_pattern, text)

    def _run(self, url_input: Optional[Union[str, List[str]]] = None) -> str:
        """
        Main method for extracting content from news URLs.
        
        Process:
        1. Validates the FireCrawl client is initialized
        2. Converts single URL input to list format
        3. Validates URLs are properly formatted
        4. Extracts content from each URL using FireCrawl
        5. Returns structured JSON response with extracted content
        
        Args:
            url_input: Either a single URL string or a list of URLs to process
            
        Returns:
            JSON string containing extracted content for each URL
            Format: {
                "results": {
                    "url1": {
                        "title": "...",
                        "main_text": "...",
                        "author": "...",
                        "published_date": "...",
                        "success": true/false
                    },
                    ...
                }
            }
        """
        # Check if FireCrawl client is properly initialized
        if not firecrawl_client:
            return json.dumps({"error": "FireCrawl client not initialized. Please set FIRECRAWL_API_KEY in .env file.", "success": False})

        # If no URL input was provided, try to extract from context
        if not url_input:
            # Get the current task context
            context = self.get_current_context()
            if context and isinstance(context, str):
                # Try to extract URLs from context
                extracted_urls = self.extract_urls_from_text(context)
                if extracted_urls:
                    url_input = extracted_urls
        
        # If we still don't have URLs, return an error
        if not url_input:
            return json.dumps({"error": "No URLs provided. Please provide one or more URLs to analyze.", "success": False})
            
        # Normalize input to always work with a list of URLs
        urls = [url_input] if isinstance(url_input, str) else url_input
        
        # Validate URLs have proper format (http:// or https://)
        valid_urls = [url for url in urls if url and isinstance(url, str) and 
                     (url.startswith('http://') or url.startswith('https://'))]
        
        if not valid_urls:
            return json.dumps({"error": "No valid URLs provided", "success": False})
        
        # Process each URL and store results
        results = {}
        for url in valid_urls:
            try:
                # Use FireCrawl's extract endpoint to get structured content
                response = firecrawl_client.extract(
                    urls=[url],
                    params={
                        'prompt': """
                        Extract the following information from the news article EXACTLY as it appears on the page, but remove any markdown formatting, HTML tags, or special characters:
                        1. The main title of the article (as plain text, no formatting)
                        2. The complete main text of the article (as plain text, preserving paragraphs but removing any formatting)
                        3. The author's name if available (as plain text)
                        4. The publication date if available (as plain text)
                        
                        IMPORTANT: 
                        - Return all text as plain text without any markdown (**, __, etc.), HTML tags, or special formatting
                        - Preserve the original paragraphs and punctuation
                        - Do not modify, summarize, or interpret the content
                        - Remove any markdown syntax, HTML tags, or special characters that might be present in the original text
                        """,
                        'schema': NewsContent.model_json_schema()
                    }
                )
                
                # Validate response format
                if not response or not response.get('success'):
                    raise ValueError(f"Invalid response from FireCrawl for URL: {url}")
                
                # Store extracted content in results
                results[url] = {
                    "title": response['data'].get('title', ''),
                    "main_text": response['data'].get('main_text', ''),
                    "author": response['data'].get('author', ''),
                    "published_date": response['data'].get('published_date', ''),
                    "url": url,
                    "success": True
                }
                
            except Exception as e:
                # Handle any errors during processing
                results[url] = {
                    "url": url,
                    "success": False,
                    "error": str(e)
                }
        
        # Return all results as JSON
        return json.dumps({"results": results})
        
    def get_current_context(self) -> Optional[str]:
        """
        Get the context from the current execution state.
        This is a helper method to access the task context at runtime.
        """
        try:
            # Access the task context through the CrewAI API
            from crewai.task import Task
            return getattr(self, "context", None)
        except (ImportError, AttributeError):
            logger.warning("Could not access task context")
            return None 