# AI News Agency

A multi-agent system for automatically creating news articles based on provided URLs using CrewAI and FireCrawl.

## Description

AI News Agency is a web application that uses CrewAI technology to create a team of AI agents working together as a news editorial team. The system analyzes provided URLs using FireCrawl, and creates comprehensive news articles with images and ready-to-publish social media posts.

### Key Features

- **Advanced URL Content Analysis**: The system extracts content from multiple sources using FireCrawl with improved metadata extraction
- **Content Size Management**: Automatic truncation of large content to prevent token limit issues
- **Information Aggregation**: Combining data from different sources into a coherent structure
- **Article Creation**: Writing structured and informative news articles
- **Image Generation**: Creating relevant images for articles using DALL-E
- **Social Media Content**: Generating ready-to-publish posts for LinkedIn and Twitter/X
- **Web Interface**: User-friendly interface for creating and viewing articles
- **Authentication**: Registration and login system for users
- **Tracking**: Integration with Weights & Bianas for tracking agent activities
- **Memory System**: Built-in memory system enabling agents to reference previous interactions
- **LLM Flexibility**: Support for different language models via environment variables

## System Architecture

The system consists of 7 specialized AI agents working in a sequential and parallel process:

1. **URL Research Journalist**: Analyzes provided URLs using FireCrawl and extracts key information
2. **Content Aggregator**: Combines and structures information from all sources into a coherent outline
3. **News Writer**: Creates a comprehensive news article based on the aggregated data
4. **Chief Editor**: Checks and edits the final version of the article, ensuring quality and readability
5. **Image Generator**: Creates relevant images for the article using DALL-E
6. **Social Media Writer**: Generates optimized social media posts for LinkedIn and Twitter/X
7. **Final Collector**: Integrates all content (article, image, social media posts) for publication

### System Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│  URL Research   │────▶│    Content      │────▶│   News Writer   │────▶│  Chief Editor   │
│   Journalist    │     │   Aggregator    │     │                 │     │                 │
│                 │     │                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                                                │
                                                                                │
                          ┌───────────────────────────────────────────┬─────────┘
                          │                                           │
                          ▼                                           ▼
                ┌─────────────────┐                     ┌─────────────────┐
                │                 │                     │                 │
                │ Image Generator │                     │ Social Media    │
                │                 │                     │ Writer          │
                │                 │                     │                 │
                └───────┬─────────┘                     └────────┬────────┘
                        │                                        │
                        └──────────────────┬─────────────────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │                 │
                                  │ Final Collector │
                                  │                 │
                                  │                 │
                                  └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │                 │
                                  │  Final Result   │
                                  │  Article+Image  │
                                  │  +Social Media  │
                                  └─────────────────┘
```

The workflow operates as follows:
1. The URL Research Journalist uses FireCrawl to analyze URLs and extract content with enhanced metadata extraction
2. The Content Aggregator organizes the information into a structured outline
3. The News Writer creates a comprehensive article following the outline
4. The Chief Editor polishes the article and creates a summary for social media and SEO
5. After the article is edited, the Image Generator and Social Media Writer work in parallel
6. The Image Generator creates a relevant image for the article using DALL-E
7. The Social Media Writer creates optimized posts for LinkedIn and Twitter/X
8. The Final Collector integrates all components (article, image, social media posts) for publication
9. The final result is saved to the database and displayed in the web interface

## Project Structure Overview

The project is organized into several major components:

```
AI-Agents/
├── app/                      # Main application directory
│   ├── journalist_agent/     # News article generation module (CrewAI)
│   │   ├── src/
│   │   │   └── journalist_agent/
│   │   │       ├── config/   # YAML configuration files
│   │   │       ├── tools/    # Custom tools for the agents
│   │   │       ├── crew.py   # CrewAI agent and task definitions
│   │   │       └── main.py   # Entry points for running the crew
│   │
│   ├── static/               # Static assets for web interface
│   │   ├── css/              # CSS styles
│   │   ├── js/               # JavaScript files
│   │   └── images/           # Generated and static images
│   ├── templates/            # HTML templates for web interface
│   └── app.py                # Flask web application
│
├── infra/                    # Infrastructure configuration
└── README.md                 # This documentation file
```

