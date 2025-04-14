import json
import logging
from typing import Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("json_formatter")

class ArticleDataInput(BaseModel):
    """
    Input data schema for formatting an article in JSON.
    
    Attributes:
        article_title: Article title
        article_content: Article content
        article_summary: Brief article description (up to 160 characters)
        image_url: URL of the generated image
        image_local_path: Local path to the saved image
        image_relative_path: Relative path to the image for display on a web page
        image_prompt: Prompt used for image generation
        linkedin_post: LinkedIn post text
        twitter_post: Twitter/X post text
    """
    article_title: str = Field(..., description="Article title")
    article_content: str = Field(..., description="Full article text without the title")
    article_summary: str = Field(..., description="Brief article description (up to 160 characters) for SEO and preview")
    image_url: str = Field(..., description="URL of the generated DALL-E image")
    image_local_path: str = Field(..., description="Full path to the saved image")
    image_relative_path: str = Field(..., description="Relative path for display in the web interface")
    image_prompt: str = Field(..., description="Prompt used for image generation")
    linkedin_post: str = Field(..., description="Full LinkedIn post text")
    twitter_post: str = Field(..., description="Full Twitter/X post text")

class JSONFormatter(BaseTool):
    """
    Tool for formatting article data into a standardized JSON structure.
    Ensures that the result will be a valid JSON object in the expected format.
    """
    name: str = "Format Article JSON"
    description: str = """
    Formats article data, images, and social media posts into a standardized JSON structure.
    
    Use this tool to create a standardized JSON response with:
    1. Article title and content
    2. Image information (URL, paths, and generation prompt)
    3. LinkedIn and Twitter/X post texts
    
    The tool validates all fields for correctness and returns a valid JSON object.
    """
    args_schema: type[BaseModel] = ArticleDataInput
    
    def _run(
        self, 
        article_title: str,
        article_content: str,
        article_summary: str,
        image_url: str, 
        image_local_path: str, 
        image_relative_path: str,
        image_prompt: str,
        linkedin_post: str,
        twitter_post: str
    ) -> str:
        """
        Formats article data into a standardized JSON structure.
        
        Args:
            article_title: Article title
            article_content: Article content
            article_summary: Brief article description (up to 160 characters)
            image_url: URL of the generated image
            image_local_path: Local path to the saved image
            image_relative_path: Relative path to the image for display on a web page
            image_prompt: Prompt used for image generation
            linkedin_post: LinkedIn post text
            twitter_post: Twitter/X post text
            
        Returns:
            String in JSON format with all data organized in the expected structure
        """
        try:
            # Create structured JSON object
            article_data = {
                "article_title": article_title,
                "article_content": article_content,
                "article_summary": article_summary,
                "image_info": {
                    "original_url": image_url,
                    "local_path": image_local_path,
                    "relative_path": image_relative_path,
                    "prompt": image_prompt
                },
                "social_media": {
                    "linkedin": linkedin_post,
                    "twitter": twitter_post
                }
            }
            
            # Check summary length
            if len(article_summary) > 160:
                logger.warning(f"Article has a summary that is too long: {len(article_summary)} characters (recommended up to 160)")
            
            # Check all required fields
            for key in ["article_title", "article_content", "article_summary"]:
                if not article_data[key]:
                    logger.warning(f"Field {key} is empty or missing")
            
            for section in ["image_info", "social_media"]:
                if not article_data[section] or not isinstance(article_data[section], dict):
                    logger.warning(f"Section {section} is missing or is not a dictionary")
                else:
                    for key in article_data[section]:
                        if not article_data[section][key]:
                            logger.warning(f"Field {section}.{key} is empty or missing")
            
            # Convert to JSON string
            formatted_json = json.dumps(article_data, ensure_ascii=False, indent=None)
            logger.info("JSON successfully formed")
            
            return formatted_json
            
        except Exception as e:
            logger.error(f"Error formatting JSON: {str(e)}")
            error_response = {
                "error": f"Error formatting JSON: {str(e)}",
                "success": False
            }
            return json.dumps(error_response) 