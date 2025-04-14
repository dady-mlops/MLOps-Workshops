import os
import json
import logging
import requests
import time
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_downloader")

class ImageDownloaderInput(BaseModel):
    """
    Input schema for the image downloader tool.
    
    Attributes:
        image_url: URL of the image to download
        article_id: Article ID for creating the corresponding directory
        filename: Optional custom filename
    """
    image_url: str = Field(..., description="URL of the image to download")
    article_id: int = Field(..., description="Article ID for creating the corresponding directory")
    filename: Optional[str] = Field(None, description="Optional custom filename")

class ImageDownloader(BaseTool):
    """
    Tool for downloading images from remote URLs and saving them 
    to the local filesystem. Used by the collector agent to 
    save generated DALL-E images.
    """
    name: str = "Download Image"
    description: str = "Downloads an image from the specified URL and saves it to disk"
    args_schema: type[BaseModel] = ImageDownloaderInput
    
    def _run(self, image_url: str, article_id: int, filename: Optional[str] = None) -> str:
        """
        Downloads an image and saves it in the article's image directory.
        
        Args:
            image_url: URL of the image to download
            article_id: Article ID for creating the corresponding directory
            filename: Optional filename
            
        Returns:
            JSON string with download results, including the local path to the saved file
        """
        try:
            # Base directory for storing images
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 
                                    "static", "images", str(article_id))
            
            # Create directory if it doesn't exist
            os.makedirs(base_dir, exist_ok=True)
            logger.info(f"Image directory created: {base_dir}")
            
            # Determine filename
            if filename:
                # If custom filename is provided
                base_filename = filename
                if not (base_filename.endswith('.jpg') or base_filename.endswith('.png') or base_filename.endswith('.jpeg')):
                    base_filename += '.jpg'  # Add extension if not specified
            else:
                # Use article ID and timestamp
                base_filename = f"article_{article_id}_image.jpg"
            
            # Generate unique filename if file already exists
            file_path = os.path.join(base_dir, base_filename)
            if os.path.exists(file_path):
                # Filename already exists, add timestamp
                name_parts = os.path.splitext(base_filename)
                timestamp = int(time.time())
                new_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
                file_path = os.path.join(base_dir, new_filename)
                logger.info(f"File with name {base_filename} already exists. Creating new file with name {new_filename}")
                filename = new_filename
            else:
                filename = base_filename
            
            # Download image
            response = requests.get(image_url, stream=True)
            response.raise_for_status()  # Check request success
            
            # Save image to disk
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Calculate relative path for web application use
            relative_path = os.path.join("images", str(article_id), filename)
            
            logger.info(f"Image successfully downloaded and saved: {file_path}")
            
            # Return result
            return json.dumps({
                "success": True,
                "local_path": file_path,
                "relative_path": relative_path,
                "filename": filename
            })
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }) 