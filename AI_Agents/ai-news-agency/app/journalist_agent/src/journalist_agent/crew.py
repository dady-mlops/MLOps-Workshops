from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, tool, before_kickoff
from crewai.tasks.task_output import TaskOutput
from typing import List, Optional, Dict, Any, Tuple
from .tools.url_analyzer import URLAnalyzer
from .tools.image_downloader import ImageDownloader
from .tools.json_formatter import JSONFormatter
import os
import logging
from dotenv import load_dotenv
from crewai_tools import DallETool
import weave  # Added import for weave

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Initialize weave for tracing
project_name = os.getenv("WANDB_PROJECT", "news_agency")
wandb_api_key = os.getenv("WANDB_API_KEY")
wandb_entity = os.getenv("WANDB_ENTITY")

if not wandb_api_key:
    logger.warning("WANDB_API_KEY not found in environment variables")
else:
    logger.info(f"Found WANDB_API_KEY in environment variables")

if not wandb_entity:
    logger.info("WANDB_ENTITY not set, using default")
else:
    logger.info(f"Using WANDB_ENTITY: {wandb_entity}")

logger.info(f"Initializing W&B Weave with project name: {project_name}")
weave.init(project_name=project_name)

# Get LLM model from environment variable
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
logger.info(f"Using LLM model from .env: {MODEL_NAME}")

# Check that API key is configured
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables")

# Decorate your guardrail function with `@weave.op()`
@weave.op(name="guardrail-validate_social_media_content")
def validate_social_media_content(result: TaskOutput) -> Tuple[bool, Any]:
    # Get raw string result
    result_text = result.raw

    """Validate social media content meets requirements."""
    try:
        # Check word count
        word_count = len(result_text.split())
        
        if word_count > 50:
            logger.warning(f"Social media content exceeds 50 words (found {word_count} words)")
            # Return False but with the original text as the second element
            # This might allow CrewAI to proceed with the original content
            return (False, result_text.strip())
        
        logger.info(f"Social media content validated: {word_count} words")
        return (True, result_text.strip())
    except Exception as e:
        logger.error(f"Error validating social media content: {str(e)}")
        # Return True on error to allow process to continue
        return (True, result_text)

@CrewBase
class JournalistAgent():
    """JournalistAgent crew for news article generation"""

    def __init__(self, urls: List[str] = None, topic: str = None, article_id: int = None):
        """
        Initialize the JournalistAgent with URLs and topic
        
        Args:
            urls: List of URLs to analyze
            topic: Topic of the article to generate
            article_id: ID of the article in the database (needed for image storage)
        """
        self.urls = urls or []
        self.topic = topic or ""
        self.article_id = article_id
        
        # Create a common LLM instance for all agents
        llm_config = {"model": MODEL_NAME}
        
        # Add API configuration if using a non-standard API key
        # (sk-proj-* is typically used with non-standard providers)
        if OPENAI_API_KEY.startswith("sk-proj-"):
            logger.info("Detected provider-specific API key, configuring accordingly")
            # Configuration for alternative API providers
            api_base = os.getenv("OPENAI_API_BASE", "")
            if api_base:
                llm_config["base_url"] = api_base
                logger.info(f"Using custom API base URL: {api_base}")
        
        self.llm = LLM(**llm_config)
        logger.info(f"LLM configured with model: {MODEL_NAME}")
        
        # Variables for formatting in YAML
        self.format_args = {
            "urls": self.urls,
            "topic": self.topic,
            "article_id": self.article_id
        }
    
    @before_kickoff
    def prepare_inputs(self, inputs: dict):
        """Prepare inputs before running the crew"""
        # Ensure URLs are passed to the task
        if not self.urls and "urls" in inputs:
            self.urls = inputs["urls"]
        
        if not self.topic and "topic" in inputs:
            self.topic = inputs["topic"]
            
        if not self.article_id and "article_id" in inputs:
            self.article_id = inputs["article_id"]
            
        # Update format args
        self.format_args = {
            "urls": self.urls,
            "topic": self.topic,
            "article_id": self.article_id
        }
        
        # Make sure we have at least some default values
        if not self.urls:
            self.urls = ["https://example.com"]
        
        if not self.topic:
            self.topic = "AI Technology"
            
        if not self.article_id:
            self.article_id = 1
            
        return inputs
    
    @tool
    def url_analyzer(self):
        """Get the URL Analyzer tool"""
        return URLAnalyzer()
        
    @tool
    def dalle_tool(self):
        """Get the DALL-E image generation tool"""
        return DallETool(
            model="dall-e-2",
            size="512x512",
            n=1
        )
        
    @tool
    def image_downloader(self):
        """Get the Image Downloader tool"""
        return ImageDownloader()
        
    @tool
    def json_formatter(self):
        """Get the JSON Formatter tool"""
        return JSONFormatter()
        
    @agent
    def url_researcher(self):
        """URL Research Journalist agent"""
        return Agent(
            config=self.agents_config["agents"]["url_researcher"],
            tools=[self.url_analyzer()],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def content_aggregator(self) -> Agent:
        """Content Aggregator agent"""
        return Agent(
            config=self.agents_config["agents"]["content_aggregator"],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def writer(self) -> Agent:
        """News Writer agent"""
        return Agent(
            config=self.agents_config["agents"]["writer"],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def editor(self) -> Agent:
        """News Editor agent"""
        return Agent(
            config=self.agents_config["agents"]["editor"],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def image_generator(self) -> Agent:
        """Image Generation Specialist agent"""
        return Agent(
            config=self.agents_config["agents"]["image_generator"],
            tools=[self.dalle_tool()],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def social_media_writer(self) -> Agent:
        """Social Media Content Specialist agent"""
        return Agent(
            config=self.agents_config["agents"]["social_media_writer"],
            memory=True,
            llm=self.llm
        )
        
    @agent
    def collector(self) -> Agent:
        """Content Integration Specialist agent"""
        return Agent(
            config=self.agents_config["agents"]["collector"],
            tools=[self.image_downloader(), self.json_formatter()],
            memory=True,
            llm=self.llm
        )
        
    @task
    def url_research_task(self) -> Task:
        """URL research task"""
        task_config = dict(self.tasks_config["url_research_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.url_researcher()
        )
        
    @task
    def content_aggregation_task(self) -> Task:
        """Content aggregation task"""
        # Get reference to URL research task for context
        url_task = self.url_research_task()
        
        # Format the task description
        task_config = dict(self.tasks_config["content_aggregation_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.content_aggregator(),
            context=[url_task]
        )
        
    @task
    def writing_task(self) -> Task:
        """Writing task"""
        # Get reference to tasks for context
        url_task = self.url_research_task()
        content_task = self.content_aggregation_task()
        
        # Format the task description for writing
        task_config = dict(self.tasks_config["writing_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.writer(),
            context=[content_task, url_task]
        )
        
    @task
    def editing_task(self) -> Task:
        """Editing task"""
        # Get reference to tasks for context
        url_task = self.url_research_task()
        writing_task = self.writing_task()
        content_task = self.content_aggregation_task()
        
        # Format the task description for editing
        task_config = dict(self.tasks_config["editing_task"])
            
        return Task(
            config=task_config,
            agent=self.editor(),
            context=[writing_task, url_task, content_task]
        )
        
    @task
    def image_generation_task(self) -> Task:
        """Image generation task"""
        # Get reference to editing task for context
        editing_task = self.editing_task()
        
        # Format the task description for image generation
        task_config = dict(self.tasks_config["image_generation_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.image_generator(),
            context=[editing_task]
        )
        
    @task
    def social_media_task(self) -> Task:
        """Social media task"""
        # Get reference to editing task for context
        editing_task = self.editing_task()
        
        # Format the task description for social media content
        task_config = dict(self.tasks_config["social_media_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.social_media_writer(),
            context=[editing_task]
        )
        
    @task
    def collection_task(self) -> Task:
        """Collection task"""
        # Get reference to tasks for context
        editing_task = self.editing_task()
        image_task = self.image_generation_task()
        social_task = self.social_media_task()
        
        # Format the task description for collection
        task_config = dict(self.tasks_config["collection_task"])
        task_config["description"] = task_config["description"].format(**self.format_args)
            
        return Task(
            config=task_config,
            agent=self.collector(),
            context=[editing_task, image_task, social_task]
        )

    @crew
    def crew(self):
        """
        Define the crew with agents and tasks configuration
        """
        # Check for parallel execution support
        try:
            # First part of the process - sequential execution up to article creation
            sequential_part = Crew(
                agents=[
                    self.url_researcher(),
                    self.content_aggregator(),
                    self.writer(),
                    self.editor()
                ],
                tasks=[
                    self.url_research_task(),
                    self.content_aggregation_task(), 
                    self.writing_task(),
                    self.editing_task()
                ],
                process=Process.sequential,
                verbose=True
            )
            
            # Second part of the process - sequential creation of image and social media posts
            # Changed to sequential process instead of parallel for compatibility
            parallel_part = Crew(
                agents=[
                    self.image_generator(),
                    self.social_media_writer()
                ],
                tasks=[
                    self.image_generation_task(),
                    self.social_media_task()
                ],
                process=Process.sequential,  # Changed to sequential process
                verbose=True
            )
            
            # Third part - final assembly
            final_part = Crew(
                agents=[self.collector()],
                tasks=[self.collection_task()],
                process=Process.sequential,
                verbose=True
            )
            
            # Combined process that executes parts sequentially
            crew = Crew(
                crews=[sequential_part, parallel_part, final_part],
                process=Process.sequential,
                verbose=True,
                memory=True,
                embedder={
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small"
                    }
                }
            )
            
            logger.info(f"Created crew with topic: {self.topic} and memory enabled")
                
            return crew
            
        except Exception as e:
            logger.error(f"Error creating crew structure: {str(e)}")
            
            # Alternative configuration - all in one sequential Crew
            logger.info("Falling back to simple sequential crew configuration")
            
            crew = Crew(
                agents=[
                    self.url_researcher(),
                    self.content_aggregator(),
                    self.writer(),
                    self.editor(),
                    self.image_generator(),
                    self.social_media_writer(),
                    self.collector()
                ],
                tasks=[
                    self.url_research_task(),
                    self.content_aggregation_task(), 
                    self.writing_task(),
                    self.editing_task(),
                    self.image_generation_task(),
                    self.social_media_task(),
                    self.collection_task()
                ],
                process=Process.sequential,
                verbose=True,
                memory=True,
                embedder={
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small"
                    }
                }
            )
            
            return crew
