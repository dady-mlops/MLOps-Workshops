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

# Check