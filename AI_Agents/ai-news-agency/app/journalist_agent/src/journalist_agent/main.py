#!/usr/bin/env python
import sys
import warnings
import os
import logging
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import argparse
import json

from journalist_agent.crew import JournalistAgent

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    urls = ["https://example.com"]
    topic = "AI LLMs"
    inputs = {
        'topic': topic,
        'current_year': str(datetime.now().year)
    }
    
    try:
        JournalistAgent(urls=urls, topic=topic).crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    urls = ["https://example.com"]
    topic = "AI LLMs"
    inputs = {
        "topic": topic
    }
    try:
        JournalistAgent(urls=urls, topic=topic).crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        JournalistAgent().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    urls = ["https://example.com"]
    topic = "AI LLMs"
    inputs = {
        "topic": topic,
        "current_year": str(datetime.now().year)
    }
    try:
        JournalistAgent(urls=urls, topic=topic).crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def generate_article(urls: List[str] = None, topic: str = None, article_id: int = None) -> str:
    """
    Generate a news article using the journalist agent crew.
    
    Args:
        urls: List of URLs to analyze
        topic: Topic of the article to generate
        article_id: ID of the article in the database (needed for image download)
        
    Returns:
        The generated article content
    """
    try:
        # Extended logging
        logger.info(f"generate_article called with: topic={topic}, article_id={article_id}")
        logger.info(f"URLs received: {urls}")
        
        if not urls or not isinstance(urls, list) or len(urls) == 0:
            logger.error("No valid URLs provided to generate_article")
            return "Error: No valid URLs provided for analysis"
            
        # Check each URL
        valid_urls = []
        for url in urls:
            if url and isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
                valid_urls.append(url)
            else:
                logger.warning(f"Invalid URL format: {url}")
                
        if not valid_urls:
            logger.error("No valid formatted URLs found in the input")
            return "Error: No valid formatted URLs found (URLs must start with http:// or https://)"
            
        logger.info(f"Valid URLs for processing: {valid_urls}")
        
        # Create agent
        agent = JournalistAgent(urls=valid_urls, topic=topic, article_id=article_id)
        
        # Create crew
        crew = agent.crew()
        
        # Prepare inputs for kickoff
        inputs = {
            "urls": valid_urls,
            "topic": topic,
            "article_id": article_id,
            "current_year": str(datetime.now().year)
        }
        
        # Run crew kickoff with inputs
        logger.info(f"Starting CrewAI execution for topic: {topic}")
        result = crew.kickoff(inputs=inputs)
        logger.info("CrewAI execution completed successfully")
        
        # Add additional logging
        logger.info(f"Result type: {type(result)}")
        if isinstance(result, str):
            logger.info(f"Result first 200 chars: {result[:200]}")
            # Check for JSON in result
            if '{' in result:
                logger.info("JSON detected in result string")
        elif isinstance(result, dict):
            logger.info(f"Result keys: {list(result.keys())}")
        
        return str(result)
    except Exception as e:
        error_msg = f"Error generating article: {str(e)}"
        logger.error(error_msg)
        return error_msg

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="Generate a news article from URLs")
    parser.add_argument("--urls", nargs="+", help="URLs to analyze", default=["https://example.com"])
    parser.add_argument("--topic", help="Topic of the article", default="Latest AI Technology")
    parser.add_argument("--output", help="Output file path", default=None)
    
    args = parser.parse_args()
    
    # Process arguments
    urls = args.urls
    topic = args.topic
    output_path = args.output
    
    # Generate article
    logger.info(f"Generating article on topic '{topic}' from URLs: {urls}")
    article = generate_article(urls=urls, topic=topic)
    
    # Output handling
    if output_path:
        try:
            with open(output_path, "w") as f:
                f.write(article)
            logger.info(f"Article saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving article to file: {e}")
            print(article)
    else:
        print(article)
    
    return 0

if __name__ == "__main__":
    exit(main())

