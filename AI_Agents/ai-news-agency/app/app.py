from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sys
import os
import json
import time
import logging
import threading
import traceback
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from journalist_agent.main import generate_article
import jinja2
from markupsafe import Markup
import re
import html

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
logger.info("Environment variables loaded from .env file")

# Add debug information
debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
if debug_mode:
    logger.info("DEBUG MODE ENABLED")
    logger.info("Environment variables:")
    for key in ['DB_TYPE', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_SSL', 'DB_SSL_REJECT_UNAUTHORIZED']:
        # Hide password in logs
        if key == 'DB_PASSWORD' and os.getenv(key):
            logger.info(f"  {key}: ***MASKED***")
        else:
            logger.info(f"  {key}: {os.getenv(key)}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')  # Use value from .env

# Database configuration
DB_TYPE = os.getenv('DB_TYPE', 'postgres')  # postgres by default

if DB_TYPE == 'postgres':
    # PostgreSQL configuration
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')  # Changed to localhost for local run
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'news_agency')
    DB_SSL = os.getenv('DB_SSL', 'false').lower() == 'true'
    DB_SSL_REJECT_UNAUTHORIZED = os.getenv('DB_SSL_REJECT_UNAUTHORIZED', 'true').lower() == 'true'
    
    # Form connection string with SSL parameters
    if DB_SSL:
        ssl_mode = "verify-full" if DB_SSL_REJECT_UNAUTHORIZED else "require"
        app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={ssl_mode}'
        logger.info(f"Using PostgreSQL database at {DB_HOST}:{DB_PORT}/{DB_NAME} with SSL mode: {ssl_mode}")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        logger.info(f"Using PostgreSQL database at {DB_HOST}:{DB_PORT}/{DB_NAME} without SSL")
else:
    # SQLite configuration (default)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news_v3.db'
    logger.info("Using SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'info'

# Add nl2br filter for converting line breaks to HTML
@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return ""
    return Markup(text.replace('\n', '<br>'))

class User(UserMixin, db.Model):
    """User model for authentication and article ownership"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    articles = db.relationship('Article', backref='author', lazy=True, cascade="all, delete-orphan")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Set password hash from plain text password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if plain text password matches hash"""
        return check_password_hash(self.password_hash, password)

class Article(db.Model):
    """Article model for storing generated news articles"""
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    urls = db.Column(db.Text, nullable=False)  # Stored as JSON string
    content = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(300), nullable=True)  # Article title
    summary = db.Column(db.String(250), nullable=True)  # Brief description for social media and SEO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, error
    # New fields for extended functionality
    image_url = db.Column(db.String(500), nullable=True)  # URL of generated image
    image_path = db.Column(db.String(500), nullable=True)  # Local path to saved image
    image_prompt = db.Column(db.Text, nullable=True)  # Prompt used for image generation
    linkedin_post = db.Column(db.Text, nullable=True)  # Post content for LinkedIn
    twitter_post = db.Column(db.Text, nullable=True)  # Post content for Twitter/X
    raw_response = db.Column(db.Text, nullable=True)  # Raw response from the LLM

    def set_urls(self, url_list):
        """Convert URL list to JSON string for storage"""
        self.urls = json.dumps(url_list)

    def get_urls(self):
        """Convert stored JSON string to URL list"""
        return json.loads(self.urls)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return db.session.get(User, int(user_id))

def create_default_admin():
    """Create default admin user if it doesn't exist"""
    default_admin = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
    default_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')
    
    if not db.session.query(User).filter_by(username=default_admin).first():
        logger.info(f"Creating default admin user: {default_admin}")
        admin = User(username=default_admin)
        admin.set_password(default_password)
        db.session.add(admin)
        db.session.commit()
        logger.info("Default admin user created successfully")

# Initialize database and create default admin
with app.app_context():
    try:
        logger.info("Initializing database")
        # Always create tables when starting the application
        db.create_all()
        create_default_admin()
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"User logged in: {username}")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            logger.warning(f"Failed login attempt for username: {username}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    flash('You have been successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User with this username already exists', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=username)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user registered: {username}")
            flash('Registration successful! You can now log in', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user {username}: {str(e)}")
            flash('Error during registration. Please try again later.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/')
@login_required
def index():
    """Display user's articles"""
    articles = Article.query.filter_by(user_id=current_user.id).order_by(Article.created_at.desc()).all()
    return render_template('index.html', articles=articles)

def escape_html_for_status(text):
    """
    Escapes HTML tags in text so they are displayed as text, not as markup.
    """
    return html.escape(text) if text else ""

def safe_json_loads(json_str):
    """
    Safe JSON parser with additional string preprocessing.
    """
    if not json_str:
        return None
        
    # Handle special characters and formatting issues
    # 1. Replace unescaped backslashes
    processed_str = re.sub(r'([^\\])\\([^\\"/bfnrtu])', r'\1\\\\\2', processed_str)
    
    # 2. Replace unescaped quotes inside strings
    processed_str = re.sub(r'([^\\])"([^"]*[^\\])"([^:,\s\}\]])', r'\1"\2\\"\3', processed_str)
    
    # 3. Use existing logic for processing the rest of the string
    processed_str = re.sub(r'(\s)(\$\d+)([MBK])(\s)', r'\1"\2\3"\4', processed_str)
    
    # 4. Remove invisible characters and control sequences
    processed_str = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', processed_str)
    
    # 5. Remove BOM and other byte order markers
    processed_str = processed_str.replace('\ufeff', '')
    
    try:
        return json.loads(processed_str)
    except json.JSONDecodeError as e:
        try:
            # Try to recover from an improperly formatted JSON
            # 1. Add quotes around keys without quotes
            fixed_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', processed_str)
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            try:
                # 2. Try to fix unclosed quotes
                fixed_str = processed_str
                # Find unclosed keys and values
                open_quotes = [m.start() for m in re.finditer(r'(?<![\\])"(?![\s]*[:,\]}])', fixed_str)]
                for pos in open_quotes:
                    # Add closing quote before comma or closing brace
                    next_delimiter = re.search(r'[,\]}]', fixed_str[pos:])
                    if next_delimiter:
                        close_pos = pos + next_delimiter.start()
                        fixed_str = fixed_str[:close_pos] + '"' + fixed_str[close_pos:]
                return json.loads(fixed_str)
            except (json.JSONDecodeError, IndexError, AttributeError):
                logger.warning(f"Error parsing JSON even after processing: {e}")
                return None

def find_value_in_nested_json(json_obj, key_to_find, visited=None):
    """
    Recursively searches for a key in JSON of any nesting.
    Returns the first found value or None if the key is not found.
    
    Args:
        json_obj: JSON object (dict, list, or primitive)
        key_to_find: Key to search for
        visited: Set of already visited objects to avoid cyclic references
    
    Returns:
        Found value or None
    """
    if visited is None:
        visited = set()
        
    # Protection against cyclic references and primitive types
    if not isinstance(json_obj, (dict, list)) or id(json_obj) in visited:
        return None
    
    visited.add(id(json_obj))
    
    if isinstance(json_obj, dict):
        # Direct key search
        if key_to_find in json_obj:
            return json_obj[key_to_find]
        
        # Search with key variations (with prefixes article_, image_ and etc.)
        variations = [
            key_to_find,
            f"article_{key_to_find}",
            f"image_{key_to_find}",
            f"social_media_{key_to_find}",
            key_to_find.replace("_", ""),
            key_to_find.replace("_", "-")
        ]
        
        for var in variations:
            if var in json_obj:
                return json_obj[var]
        
        # Recursive search in values
        for value in json_obj.values():
            result = find_value_in_nested_json(value, key_to_find, visited)
            if result is not None:
                return result
    
    elif isinstance(json_obj, list):
        # Recursive search in list items
        for item in json_obj:
            result = find_value_in_nested_json(item, key_to_find, visited)
            if result is not None:
                return result
    
    return None

def extract_all_values_from_json(json_obj, keys_to_find):
    """
    Extracts all values for specified keys from JSON object,
    regardless of JSON structure.
    
    Args:
        json_obj: JSON object
        keys_to_find: List of keys to search for
    
    Returns:
        Dictionary of found values in format {key: value}
    """
    result = {}
    for key in keys_to_find:
        value = find_value_in_nested_json(json_obj, key)
        if value is not None:
            result[key] = value
    return result

def sanitize_json_data(article, data_dict):
    """
    Cleans and normalizes data before saving to database.
    
    Args:
        article: Article object
        data_dict: Dictionary with data for update
    """
    for key, value in data_dict.items():
        if not value:
            continue
            
        if isinstance(value, str):
            # Unescape HTML entities
            value = html.unescape(value)
            
            # Remove invisible control characters
            value = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', value)
            
            # Set attribute value if it exists in the model
            if hasattr(article, key):
                setattr(article, key, value)
                logger.info(f"Updated article.{key} with value of length: {len(value) if value else 0}")

def generate_article_async(article_id):
    # Create application context
    with app.app_context():
        try:
            article = Article.query.get(article_id)
            if not article:
                logger.error(f"Article with ID {article_id} not found")
                return

            article.status = 'processing'
            db.session.commit()
            logger.info(f"Article status updated to processing: {article_id}")

            # Load URLs from JSON string
            urls = json.loads(article.urls)
            logger.info(f"Loaded URLs: {urls}")

            # Create and run the crew
            result = generate_article(urls=urls, topic=article.topic, article_id=article.id)
            logger.info(f"Result received for article ID {article_id} with length: {len(result)}")

            # Store the raw response
            article.raw_response = result
            
            # Clean the result for removal of control characters, but keep HTML and line breaks
            clean_result = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', result)  # Remove control characters, keep line breaks, tabs, and HTML
            
            logger.info(f"Cleaned result for article ID {article_id}")
            
            # Check if the result contains JSON
            contains_json = '{' in clean_result and '}' in clean_result
            logger.info(f"Contains JSON: {contains_json}")
            
            # All fields we want to extract
            expected_fields = [
                'content', 'title', 'summary', 'article_content', 'article_title', 'article_summary',
                'image_url', 'image_path', 'image_relative_path', 'image_prompt', 
                'linkedin_post', 'twitter_post'
            ]
            
            # Try to parse the result as JSON
            result_json = None
            json_parsed = False
            
            try:
                # First attempt: try to parse the entire result using safe parser
                result_json = safe_json_loads(clean_result)
                if result_json:
                    logger.info("Successfully parsed result as JSON with safe parser")
                    json_parsed = True
                else:
                    # Standard JSON parsing as fallback
                    result_json = json.loads(clean_result)
                    logger.info("Successfully parsed result as JSON with standard parser")
                    json_parsed = True
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse result as JSON directly: {e}")
                json_parsed = False
                result_json = None
                
                if contains_json:
                    # Second attempt: try to extract JSON using regex
                    logger.info("Attempting to extract JSON with regex")
                    # Try to find a JSON object in the text
                    json_patterns = [
                        r'({[\s\S]*})',  # Most greedy pattern
                        r'({[^{}]*})'     # Less greedy pattern for simple objects
                    ]
                    
                    all_matches = []
                    for pattern in json_patterns:
                        matches = re.findall(pattern, clean_result)
                        all_matches.extend(matches)
                    
                    # Sort matches by length (longest first) to prioritize complete JSON objects
                    all_matches.sort(key=len, reverse=True)
                    
                    for match in all_matches:
                        # Try with safe parser first
                        candidate_json = safe_json_loads(match)
                        if not candidate_json:
                            # If safe parser fails, try standard parse with try/except
                            try:
                                candidate_json = json.loads(match)
                            except json.JSONDecodeError:
                                continue
                                
                        # Check if JSON contains at least one of the expected keys
                        if isinstance(candidate_json, dict) and any(find_value_in_nested_json(candidate_json, key) is not None for key in expected_fields):
                            result_json = candidate_json
                            json_parsed = True
                            logger.info(f"Successfully extracted and parsed JSON")
                            break
            
            # Extract and update article data
            if json_parsed and result_json:
                # Extract all relevant fields from the JSON using our universal function
                extracted_data = extract_all_values_from_json(result_json, expected_fields)
                logger.info(f"Found {len(extracted_data)} fields in JSON: {list(extracted_data.keys())}")
                
                # Map extracted fields to model fields
                field_mapping = {
                    'article_content': 'content',
                    'article_title': 'title',
                    'article_summary': 'summary',
                    'image_relative_path': 'image_path'
                }
                
                # Normalize keys according to the model
                normalized_data = {}
                for key, value in extracted_data.items():
                    normalized_key = field_mapping.get(key, key)
                    normalized_data[normalized_key] = value
                
                # Sanitize and save data
                sanitize_json_data(article, normalized_data)
                
                # If content was not found in JSON, use raw_result
                if 'content' not in normalized_data and 'article_content' not in normalized_data:
                    article.content = clean_result
                    logger.info(f"Content not found in JSON, using cleaned raw result")
            else:
                # If JSON parsing failed, use the raw result as content
                logger.warning("No valid JSON found. Using raw result as content.")
                article.content = clean_result
                
                # In case of JSON failure, try to extract key data through regular expressions
                regex_patterns = {
                    'title': r'"(?:article_)?title":\s*"([^"]+(?:\\.[^"]+)*)"',
                    'summary': r'"(?:article_)?summary":\s*"([^"]+(?:\\.[^"]+)*)"',
                    'linkedin_post': r'"linkedin_post":\s*"([^"]+(?:\\.[^"]+)*)"',
                    'twitter_post': r'"twitter_post":\s*"([^"]+(?:\\.[^"]+)*)"',
                    'image_path': r'"image_path":\s*"([^"]+)"',
                    'image_relative_path': r'"image_relative_path":\s*"([^"]+)"',
                    'image_prompt': r'"image_prompt":\s*"([^"]+(?:\\.[^"]+)*)"',
                    'image_url': r'"image_url":\s*"([^"]+)"'
                }
                
                regex_data = {}
                for field, pattern in regex_patterns.items():
                    match = re.search(pattern, article.raw_response)
                    if match:
                        value = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
                        regex_data[field] = value
                        logger.info(f"Extracted {field} using regex")
                
                # Apply extracted data
                sanitize_json_data(article, regex_data)
                
                # Special handling for image_relative_path
                if 'image_relative_path' in regex_data and not article.image_path:
                    article.image_path = regex_data['image_relative_path']
                    logger.info(f"Set image_path from image_relative_path: {article.image_path}")
            
            # Final check and processing
            # 1. Ensure article has a title
            if not article.title and article.topic:
                article.title = article.topic.capitalize()
                logger.info(f"Used topic as title: {article.title}")
            
            # 2. Check for image URLs
            if article.image_path and not article.image_path.startswith('images/'):
                # Possible full path - extract only relative part
                match = re.search(r'(?:images|static)/.*?$', article.image_path)
                if match:
                    article.image_path = match.group(0)
                    logger.info(f"Fixed image path to relative: {article.image_path}")
            
            # 3. Fix URLs in content
            if article.content:
                # Replace potential broken URLs in text
                article.content = re.sub(r'(href|src)=([\'"])((?!https?://)[^\'"]+)([\'"])', 
                                        r'\1=\2https://\3\4', article.content)
                
                # Convert text URLs to HTML links
                article.content = re.sub(r'(?<![\'"=])(https?://[^\s<>"\']+)', r'<a href="\1" target="_blank">\1</a>', article.content)
            
            # Convert text URLs to links in social media posts
            if article.linkedin_post:
                article.linkedin_post = convert_markdown_to_html(article.linkedin_post)
                # Convert simple URLs to HTML links (not affected by Markdown)
                article.linkedin_post = re.sub(r'(?<![\'"=])((?:https?://)[^\s<>"\']+)(?![^<]*>)', r'<a href="\1" target="_blank">\1</a>', article.linkedin_post)
                
            if article.twitter_post:
                article.twitter_post = convert_markdown_to_html(article.twitter_post)
                # Convert simple URLs to HTML links (not affected by Markdown)
                article.twitter_post = re.sub(r'(?<![\'"=])((?:https?://)[^\s<>"\']+)(?![^<]*>)', r'<a href="\1" target="_blank">\1</a>', article.twitter_post)
            
            if article.content:
                article.content = convert_markdown_to_html(article.content)
                # Convert simple URLs to HTML links (not affected by Markdown)
                article.content = re.sub(r'(?<![\'"=])((?:https?://)[^\s<>"\']+)(?![^<]*>)', r'<a href="\1" target="_blank">\1</a>', article.content)
            
            # Final data saving
            article.status = 'completed'
            db.session.commit()
            logger.info(f"Article generation completed successfully: {article_id}")
            return "Article generated successfully"
            
        except Exception as e:
            logger.error(f"Error generating article: {str(e)}")
            traceback.print_exc()
            
            # Update article status to error
            try:
                article = Article.query.get(article_id)
                if article:
                    article.status = 'error'
                    db.session.commit()
                    logger.info(f"Article status updated to error: {article_id}")
            except Exception as update_error:
                logger.error(f"Error updating article status: {str(update_error)}")
                
            return f"Error: {str(e)}"

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Handle article creation"""
    if request.method == 'POST':
        topic = request.form['topic']
        urls = request.form.getlist('urls')  # Get all URLs from the form
        
        # Remove empty URLs
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            flash('Please enter at least one URL', 'warning')
            return redirect(url_for('create'))

        try:
            logger.info(f"Creating article on topic '{topic}' with {len(urls)} URLs")
            
            # Create article in database with temporary content
            article = Article(
                topic=topic,
                content="Article is being generated... Please wait. This may take a few minutes.",
                user_id=current_user.id,
                status='pending'
            )
            article.set_urls(urls)
            
            db.session.add(article)
            db.session.commit()
            article_id = article.id
            logger.info(f"Article created in database with ID: {article_id}, status: pending")
            
            # Start asynchronous article generation in a separate thread
            thread = threading.Thread(
                target=generate_article_async,
                args=(article_id,)
            )
            thread.daemon = True  # Thread will terminate when the main thread terminates
            thread.start()
            logger.info(f"Started async article generation thread for ID: {article_id}")
            
            flash('Article is being generated! You can close this window and come back later.', 'info')
            return redirect(url_for('view_article', article_id=article_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating article: {str(e)}")
            flash(f'Error creating article: {str(e)}', 'danger')
            return redirect(url_for('create'))

    return render_template('create.html')

@app.route('/article/<int:article_id>')
@login_required
def view_article(article_id):
    """Display a specific article"""
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    
    # Check if the article belongs to the current user
    if article.user_id != current_user.id:
        flash('You do not have access to this article', 'danger')
        return redirect(url_for('index'))
    
    return render_template('article.html', article=article)

@app.route('/article/<int:article_id>/delete', methods=['POST'])
@login_required
def delete_article(article_id):
    """Delete an article"""
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    
    # Check if article belongs to current user
    if article.user_id != current_user.id:
        flash('You do not have access to this article', 'danger')
        return redirect(url_for('index'))
    
    # Delete the article
    db.session.delete(article)
    db.session.commit()
    
    flash('Article successfully deleted', 'success')
    return redirect(url_for('index'))

@app.route('/regenerate/<int:article_id>')
@login_required
def regenerate_article(article_id):
    """Regenerate an existing article"""
    try:
        # Get the article
        article = db.session.get(Article, article_id)
        
        # Check if article exists and belongs to current user
        if not article or article.user_id != current_user.id:
            flash('Article not found or you do not have permission to regenerate it.', 'danger')
            return redirect(url_for('index'))
        
        # Reset article status to pending
        article.status = 'pending'
        db.session.commit()
        flash('Article regeneration started.', 'info')
        
        # Start async regeneration
        thread = threading.Thread(target=generate_article_async, args=(article_id,))
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('view_article', article_id=article_id))
    except Exception as e:
        logger.error(f"Error in regenerate_article: {str(e)}")
        flash('An error occurred while regenerating the article.', 'danger')
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    return render_template('error.html', error_code=404, message='Page not found'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(e)}")
    return render_template('error.html', error_code=500, message='Internal server error'), 500

def convert_markdown_to_html(text):
    """
    Converts basic Markdown formatting to HTML.
    
    Args:
        text: text in Markdown format
    
    Returns:
        text with HTML formatting
    """
    if not text:
        return text
    
    # Convert Markdown-style links [text](link) - do this before paragraph conversion
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # Convert formatting and author information
    text = re.sub(r'Author:\s+([^\n]+)', r'<strong>Author:</strong> \1', text)
    text = re.sub(r'Published Date:\s+([^\n]+)', r'<strong>Published Date:</strong> \1', text)
    text = re.sub(r'Source URL:\s+', r'<strong>Source URL:</strong> ', text)
        
    # Convert \n\n to paragraph separators <p>
    text = re.sub(r'\n\n+', '</p>\n\n<p>', text)
    
    # Wrap all text in <p> if not already
    if not text.startswith('<p>'):
        text = '<p>' + text
    if not text.endswith('</p>'):
        text = text + '</p>'
    
    # Headers (## Header -> <h2>Header</h2>)
    text = re.sub(r'<p>#{6}\s+(.+?)</p>', r'<h6>\1</h6>', text)
    text = re.sub(r'<p>#{5}\s+(.+?)</p>', r'<h5>\1</h5>', text)
    text = re.sub(r'<p>#{4}\s+(.+?)</p>', r'<h4>\1</h4>', text)
    text = re.sub(r'<p>#{3}\s+(.+?)</p>', r'<h3>\1</h3>', text)
    text = re.sub(r'<p>#{2}\s+(.+?)</p>', r'<h2>\1</h2>', text)
    text = re.sub(r'<p>#\s+(.+?)</p>', r'<h1>\1</h1>', text)
    
    # Bold text (**text** -> <strong>text</strong>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Italic text (*text* -> <em>text</em>)
    text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)
    
    # Convert line breaks to <br>
    text = text.replace('\n', '<br>')
    
    return text

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)
