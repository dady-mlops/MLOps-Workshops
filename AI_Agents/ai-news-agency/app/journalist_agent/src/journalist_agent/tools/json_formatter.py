import json
import logging
from typing import Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleDataInput(BaseModel):
    """
    Input data schema for formatting article in JSON.
    
    Fields:
    article_title: Article title
    article_content: Article content
    article_summary: Brief article description (up to 160 characters)
    image_url: URL of the generated image
    image_local_path: Local path to the saved image
    image_relative_path: Relative path to the saved image
    image_prompt: Prompt used for image generation
    linkedin_post: LinkedIn post content
    twitter_post: Twitter post content
    """
    article_title: str = Field(..., description="Article title")
    article_content: str = Field(..., description="Article content")
    article_summary: str = Field(..., description="Brief article description (up to 160 characters)")
    image_url: str = Field(..., description="URL of the generated image")
    image_local_path: str = Field(..., description="Local path to the saved image")
    image_relative_path: str = Field(..., description="Relative path to the saved image")
    image_prompt: str = Field(..., description="Prompt used for image generation")
    linkedin_post: str = Field(..., description="LinkedIn post content")
    twitter_post: str = Field(..., description="Twitter post content")

class JSONFormatter(BaseTool):
    """
    Input data schema for formatting article in JSON.
    
    Fields:
    article_title: Article title
    article_content: Article content
    article_summary: Brief article description (up to 160 characters)
    image_url: URL of the generated image
    image_local_path: Local path to the saved image
    image_relative_path: Relative path to the saved image
    image_prompt: Prompt used for image generation
    linkedin_post: LinkedIn post content
    twitter_post: Twitter post content
    """
    
    name = "JSONFormatter"
    description = "Formats article data into a standardized JSON structure"
    
    def _run(self, content: str) -> str:
        """
        Formats the provided content into a standardized JSON structure.
        
        Args:
            content: Text content to format into JSON
            
        Returns:
            Formatted JSON string
        """
        try:
            # Try to parse if content is already JSON
            try:
                data = json.loads(content)
                logger.info("Content was already in JSON format")
            except json.JSONDecodeError:
                # If not JSON, try to extract key information
                logger.info("Content is not JSON, extracting information")
                data = self._extract_data_from_text(content)
            
            # Ensure all required fields are present
            required_fields = [
                'article_title',
                'article_content',
                'article_summary',
                'image_url',
                'image_local_path',
                'image_relative_path',
                'image_prompt',
                'linkedin_post',
                'twitter_post'
            ]
            
            # Initialize missing fields with None
            for field in required_fields:
                if field not in data:
                    data[field] = None
                    logger.warning(f"Field {field} was missing and initialized as None")
            
            # Format the final JSON
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            logger.info("Successfully formatted content to JSON")
            
            return formatted_json
            
        except Exception as e:
            error_msg = f"Error formatting JSON: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
    
    def _extract_data_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured data from unstructured text.
        
        Args:
            text: Unstructured text to parse
            
        Returns:
            Dictionary with extracted data
        """
        data = {}
        
        # Try to find title
        title_markers = ["Title:", "# ", "Article Title:"]
        for marker in title_markers:
            if marker in text:
                lines = text.split('\n')
                for line in lines:
                    if line.strip().startswith(marker):
                        data['article_title'] = line.replace(marker, '').strip()
                        break
                if 'article_title' in data:
                    break
        
        # Try to find content
        content_markers = ["Content:", "Article Content:", "## Content"]
        for marker in content_markers:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    data['article_content'] = parts[1].strip()
                    break
        
        # Try to find summary
        summary_markers = ["Summary:", "Article Summary:", "TL;DR:"]
        for marker in summary_markers:
            if marker in text:
                lines = text.split('\n')
                for line in lines:
                    if line.strip().startswith(marker):
                        data['article_summary'] = line.replace(marker, '').strip()
                        break
                if 'article_summary' in data:
                    break
        
        logger.info(f"Extracted {len(data)} fields from text")
        return data 