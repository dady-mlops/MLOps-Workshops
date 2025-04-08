import os
import json
import logging
import requests
import concurrent.futures
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.agent import LLM
from crewai.tools import BaseTool, tool

# Initialize FireCrawl client
from firecrawl import FirecrawlApp as FireCrawlClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("news_agency")

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    logger.warning("No .env file found. Using environment variables.")

# Get API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WANDB_API_KEY = os.getenv("WANDB_API_KEY")
WANDB_PROJECT = os.getenv("WANDB_PROJECT", "ai-news-agency")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Initialize FireCrawl client
firecrawl_client = None
try:
    if FIRECRAWL_API_KEY:
        firecrawl_client = FireCrawlClient(api_key=FIRECRAWL_API_KEY)
        logger.info("Successfully initialized FireCrawl client")
    else:
        logger.warning("FireCrawl API key not set. URL analysis will be limited.")
except Exception as e:
    logger.error(f"Error initializing FireCrawl client: {str(e)}")

# Initialize weave for CrewAI tracking
try:
    # Check if API key is configured
    if WANDB_API_KEY and WANDB_API_KEY != "your_wandb_api_key_here":
        # Initialize weave with project settings
        import weave
        weave.init(
            project_name=WANDB_PROJECT
        )
        logger.info(f"Successfully initialized weave for CrewAI tracking")
    else:
        logger.warning("Weights & Bianas API key not set. Tracking disabled.")
except Exception as e:
    logger.error(f"Error initializing weave: {str(e)}")

# Default OpenAI model to use
DEFAULT_MODEL = LLM(model="gpt-4o-mini", temperature=0)

# Configure process for CrewAI
CREW_PROCESS = Process.sequential  # Use sequential process instead of hierarchical

# Create a custom tool for URL analysis
@tool("Analyze URL Content")
def analyze_url_content(url_input: Union[str, List[str]]) -> str:
    """
    Universal URL analyzer that processes URLs using FireCrawl to extract content and metadata
    
    Args:
        url_input: Either a single URL string or a list of URL strings
        
    Returns:
        JSON string with analysis results including title, content, metadata, and more
    """
    # Convert input to list if it's a single URL
    urls = [url_input] if isinstance(url_input, str) else url_input
    
    # Validate URLs
    valid_urls = [url for url in urls if url and isinstance(url, str) and 
                 (url.startswith('http://') or url.startswith('https://'))]
    
    if not valid_urls:
        error_msg = "No valid URLs provided. URLs must start with http:// or https://"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "success": False})
    
    # Check if FireCrawl client is available
    if not firecrawl_client:
        error_msg = "FireCrawl client not initialized. Please set FIRECRAWL_API_KEY in .env file."
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "success": False, "urls": valid_urls})
    
    # Process URLs with FireCrawl
    logger.info(f"Using FireCrawl to analyze {len(valid_urls)} URLs")
    results = {}
    
    # Process each URL separately
    for url in valid_urls:
        try:
            logger.info(f"Analyzing URL with FireCrawl: {url}")
            
            # Call FireCrawl API to get data with markdown and HTML formats
            response = firecrawl_client.scrape_url(
                url=url, 
                params={'formats': ['markdown', 'html']}
            )
            
            # Check if response is valid
            if not response or not isinstance(response, dict):
                raise ValueError(f"Invalid response from FireCrawl for URL: {url}")
            
            # Extract content and metadata
            markdown_content = response.get("markdown", "")
            html_content = response.get("html", "")
            metadata = response.get("metadata", {})
            
            # Limit content size to prevent token limit errors
            if markdown_content and len(markdown_content) > 8000:
                logger.warning(f"Truncating markdown content for URL {url} from {len(markdown_content)} to 8000 characters")
                markdown_content = markdown_content[:8000] + "... [content truncated]"
            
            if html_content and len(html_content) > 4000:
                logger.warning(f"Truncating HTML content for URL {url} from {len(html_content)} to 4000 characters")
                html_content = html_content[:4000] + "... [content truncated]"
            
            # Extract metadata with fallbacks
            title = metadata.get("title", "")
            description = metadata.get("description", "")
            
            # Extract title from markdown if not in metadata
            if not title and markdown_content:
                import re
                title_match = re.search(r'#\s+(.+?)(?:\n|$)', markdown_content)
                if title_match:
                    title = title_match.group(1).strip()
                    logger.info(f"Extracted title from markdown: {title}")
                elif markdown_content.strip():
                    # Use first line as fallback
                    title = markdown_content.split('\n')[0].strip()
                    logger.info(f"Using first line as title: {title}")
            
            # Extract description from content if not in metadata
            if not description and markdown_content:
                paragraphs = [p for p in markdown_content.split('\n\n') if p.strip()]
                if len(paragraphs) > 1:
                    description = paragraphs[1].strip()
                    logger.info("Extracted description from second paragraph")
                elif paragraphs:
                    description = paragraphs[0].strip()
                    logger.info("Extracted description from first paragraph")
                
                # Limit description length
                if description and len(description) > 200:
                    description = description[:197] + "..."
                    logger.info("Truncated description to 200 characters")
            
            # Store results
            results[url] = {
                "title": title,
                "description": description,
                "author": metadata.get("author", ""),
                "published_time": metadata.get("publishedTime", ""),
                "language": metadata.get("language", ""),
                "text": markdown_content,
                "html": html_content,
                "metadata": metadata,
                "url": url,
                "success": True,
                "word_count": len(markdown_content.split()) if markdown_content else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully analyzed URL: {url}")
        except Exception as e:
            error_msg = f"Error analyzing URL {url} with FireCrawl: {str(e)}"
            logger.error(error_msg)
            results[url] = {
                "url": url,
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    # Add summary statistics
    summary = {
        "total_urls": len(valid_urls),
        "successful": sum(1 for url in results if results[url].get("success", False)),
        "failed": sum(1 for url in results if not results[url].get("success", False)),
        "total_word_count": sum(results[url].get("word_count", 0) for url in results if results[url].get("success", False))
    }
    
    logger.info(f"Analysis summary: {summary}")
    
    # Return results as JSON
    return json.dumps({"results": results, "summary": summary})

class NewsAgencyCrew:
    """
    Main class for the AI News Agency system that orchestrates multiple AI agents
    to analyze URLs, search for additional information, and generate news articles
    """
    
    def __init__(self):
        """Initialize the NewsAgencyCrew"""

    def create_agents(self):
        """Create and configure all the AI agents needed for the news generation process"""
        # URL Research Journalist
        url_researcher = Agent(
            role='URL Research Journalist',
            goal='Extract key information from provided URLs',
            backstory="""You are a skilled research journalist who specializes in 
            extracting and analyzing information from online sources. You have a 
            keen eye for detail and can identify the most important facts, quotes, 
            and statistics from any article or webpage. You are also adept at 
            verifying information and identifying credible sources.""",
            tools=[analyze_url_content],
            verbose=True,
            llm=DEFAULT_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Content Aggregator
        aggregator = Agent(
            role='Content Aggregator',
            goal='Organize and structure information from multiple sources',
            backstory="""You are an expert content organizer who excels at taking 
            information from multiple sources and creating a coherent, structured 
            outline. You can identify common themes, create logical groupings, and 
            establish a clear narrative flow. You also have a strong understanding 
            of SEO principles and know how to incorporate keywords naturally.""",
            tools=[],
            verbose=True,
            llm=DEFAULT_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Writer Agent
        writer = Agent(
            role='News Writer',
            goal='Create a comprehensive, SEO-optimized news article that reads naturally',
            backstory="""You are a talented news writer who excels at transforming 
            structured information into engaging, readable articles. You know how 
            to craft compelling narratives while maintaining factual accuracy. You have
            a deep understanding of SEO principles but never sacrifice readability for
            keyword optimization. Your articles always include key dates, statistics, and
            factual information presented in a way that sounds like it was written by a skilled
            human journalist, not AI.""",
            tools=[],
            verbose=True,
            llm=DEFAULT_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Editor Agent
        editor = Agent(
            role='Chief Editor',
            goal='Ensure quality, accuracy, and natural flow of the news article',
            backstory="""You are a seasoned editor who ensures all content meets 
            high journalistic standards, properly cites sources, and presents 
            information accurately and objectively. You have an exceptional eye for
            detail and can identify and remove any text that sounds artificial or
            AI-generated. You make sure articles include proper dates, relevant statistics,
            and flow naturally while still being optimized for search engines.""",
            tools=[],
            verbose=True,
            llm=DEFAULT_MODEL,
            openai_api_key=OPENAI_API_KEY
        )
        
        return url_researcher, aggregator, writer, editor

    def create_tasks(self, urls: List[str], topic: str, url_researcher, aggregator, writer, editor):
        """Create tasks for each agent with appropriate dependencies between them"""
        # URL Analysis Task
        url_analysis_task = Task(
            description=f"""Analyze the following URLs: {urls}
            
            IMPORTANT: The URL Analyzer tool can process multiple URLs at once for efficiency.
            If there are multiple URLs, pass the entire list to the tool at once.
            
            For each URL:
            1. Extract main content, key points, and factual information
            2. Identify important quotes, statistics, and numerical data
            3. Pay special attention to dates and timeline information
            4. Verify source credibility and publication dates
            5. Extract author names and expert opinions
            
            After analyzing all URLs:
            1. Identify common themes and information
            2. Note any contradictions or different perspectives
            3. Create a summary of findings with emphasis on when events occurred
            4. Highlight the most newsworthy aspects of the topic
            
            Compile all information into a structured research brief that will serve
            as the foundation for a high-quality news article on: {topic}""",
            expected_output="A comprehensive research brief with analysis of all provided URLs, including key content, quotes, statistics, timeline information, and publication dates.",
            agent=url_researcher
        )

        # Aggregation Task
        aggregation_task = Task(
            description=f"""Combine and organize information from the URL analysis results:
            1. Identify the most important facts and information
            2. Organize information by subtopics or themes
            3. Create a clear timeline of events
            4. Highlight key statistics, quotes, and expert opinions
            5. Identify primary keywords and related terms for SEO optimization
            6. Create a structured outline with a logical flow
            
            Your goal is to provide a well-organized foundation for the writer to create 
            a comprehensive, SEO-friendly news article on: {topic}
            
            The outline should include:
            - A compelling headline suggestion that includes the primary keyword
            - Subheadings that incorporate related keywords
            - Placement of key facts, statistics, and quotes
            - A logical progression that tells the complete story
            - Suggestions for meta description and focus keywords""",
            expected_output="A well-organized outline for the article with key information organized by themes, a clear timeline, suggested headlines, subheadings, and SEO elements.",
            agent=aggregator,
            context=[url_analysis_task] 
        )

        # Writing Task
        writing_task = Task(
            description=f"""Using the aggregated information, write a comprehensive news article:
            1. Create an engaging, SEO-optimized headline that includes the primary keyword
            2. Write a compelling introduction that summarizes the key news and when it happened
            3. Follow the structure provided by the aggregator
            4. Develop a coherent narrative that incorporates all key information
            5. Include relevant quotes, statistics, and expert opinions with proper attribution
            6. Use a natural, journalistic writing style that doesn't sound AI-generated
            7. Incorporate primary and secondary keywords naturally throughout the text
            8. Ensure the article clearly states when events occurred
            9. Focus on the topic: {topic}
            
            SEO Guidelines:
            - Include the primary keyword in the first paragraph
            - Use subheadings (H2, H3) that incorporate secondary keywords
            - Keep paragraphs short and scannable (3-4 sentences)
            - Include transition phrases between sections
            - Use bullet points or numbered lists where appropriate
            - Aim for a reading level that is accessible but informative
            
            IMPORTANT: The article should read like it was written by a skilled human journalist.
            Avoid awkward phrasing, overly complex sentences, and repetitive patterns that
            sound artificial.""",
            expected_output="A comprehensive, well-written news article with an engaging headline, clear timeline, proper attribution of sources, and natural integration of SEO elements.",
            agent=writer,
            context=[aggregation_task] 
        )

        # Editing Task
        editing_task = Task(
            description=f"""Review and edit the article to ensure it meets the highest standards:
            1. Verify all source attributions and factual information
            2. Ensure dates and timeline information are clearly presented
            3. Check for and remove any awkward phrasing or AI-sounding text
            4. Improve clarity, flow, and readability
            5. Verify that SEO elements are incorporated naturally
            6. Ensure the article has a consistent, journalistic tone
            7. Check that the article provides value to readers interested in: {topic}
            
            Pay special attention to:
            - The opening and closing paragraphs
            - Transition between sections
            - Natural incorporation of keywords
            - Proper citation of sources and quotes
            - Clarity of timeline and factual information
            
            IMPORTANT: Create a concise summary of the article (maximum 160 characters) that:
            1. Captures the essence of the news story
            2. Includes the most important keywords
            3. Mentions when the event occurred
            4. Entices readers to read the full article
            5. Is optimized for social media sharing and Google search results
            
            Format your response with the summary clearly separated at the beginning:
            
            SUMMARY: [Your 160-character summary here]
            
            ARTICLE: [The full edited article]
            
            The final article should be indistinguishable from one written by a top human journalist,
            while still being optimized for search engines.""",
            expected_output="A final, polished version of the article with verified facts, proper citations, improved clarity, natural SEO optimization, a human-like writing style, and a concise 160-character summary for social media and SEO.",
            agent=editor,
            context=[writing_task] 
        )

        return [url_analysis_task, aggregation_task, writing_task, editing_task]

    def run_crew(self, urls: List[str], topic: str):
        """
        Run the news generation crew to create an article based on the provided URLs and topic
        
        Args:
            urls: List of URLs to analyze
            topic: Topic of the article to generate
            
        Returns:
            Dictionary with article content and summary
        """
        try:
            # Create agents
            url_researcher, aggregator, writer, editor = self.create_agents()
            
            # Create tasks
            tasks = self.create_tasks(urls, topic, url_researcher, aggregator, writer, editor)
            
            # Create crew with sequential process
            crew = Crew(
                agents=[url_researcher, aggregator, writer, editor],
                tasks=tasks,
                process=CREW_PROCESS,  # Use the sequential process
                verbose=True,  # Enable verbose output to see all details
                openai_api_key=OPENAI_API_KEY,  # Explicitly pass OpenAI API key
                planning=True
            )
            
            # Execute crew tasks
            logger.info(f"Starting CrewAI execution for topic: {topic}")
            result = crew.kickoff()
            logger.info("CrewAI execution completed successfully")
            
            # Extract summary and article content
            summary = ""
            content = str(result)
            
            # Look for the SUMMARY: marker in the result
            if "SUMMARY:" in content and "ARTICLE:" in content:
                parts = content.split("ARTICLE:", 1)
                summary_part = parts[0]
                content_part = parts[1].strip()
                
                # Extract summary
                if "SUMMARY:" in summary_part:
                    summary = summary_part.split("SUMMARY:", 1)[1].strip()
                    logger.info(f"Extracted summary: {summary[:100]}...")
                
                # Use content part as the main content
                content = content_part
                logger.info(f"Extracted article content of length: {len(content)}")
            
            return {
                "content": content,
                "summary": summary
            }
        except Exception as e:
            # Log the exception
            logger.error(f"Error in CrewAI execution: {str(e)}")
            # Raise the exception further
            raise RuntimeError(f"Error running news generation crew: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Example URLs
    urls = [
        "https://www.nytimes.com/section/technology",
        "https://techcrunch.com/"
    ]
    topic = "Latest Technology Trends"
    
    # Run the full news generation system
    news_crew = NewsAgencyCrew()
    result = news_crew.run_crew(urls, topic)
    print("\nFinal Article:")
    print(result)
