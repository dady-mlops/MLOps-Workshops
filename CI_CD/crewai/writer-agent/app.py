from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from news_agency import NewsAgencyCrew
import json
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import logging
import threading

try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("Warning: wandb not available. Install it with 'pip install wandb'")

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
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgres'

if DB_TYPE == 'postgres':
    # PostgreSQL configuration
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
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
    summary = db.Column(db.String(250), nullable=True)  # Brief description for social media and SEO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, error

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

def generate_article_async(article_id, urls=None, topic=None, wandb_run=None):
    """
    Asynchronously generates an article and updates it in the database
    
    Args:
        article_id: Article ID in the database
        urls: List of URLs to analyze (optional, will be retrieved from article if not provided)
        topic: Article topic (optional, will be retrieved from article if not provided)
        wandb_run: Not used, kept for backward compatibility
    """
    with app.app_context():
        try:
            # Get the article
            article = db.session.get(Article, article_id)
            if not article:
                logger.error(f"Article not found for ID: {article_id}")
                return
            
            # Update status to processing
            article.status = 'processing'
            db.session.commit()
            logger.info(f"Article status updated to 'processing' for ID: {article_id}")
            
            # Get topic and URLs from article if not provided
            topic = topic or article.topic
            urls = urls or article.get_urls()
            
            logger.info(f"Starting async article generation for topic '{topic}' with {len(urls)} URLs")
            
            # Initialize CrewAI
            crew = NewsAgencyCrew()
            
            try:
                # Generate article with CrewAI
                result = crew.run_crew(urls, topic)
                
                # Update article with generated content
                article.content = result.get('content', 'No content generated')
                article.summary = result.get('summary', '')
                article.status = 'completed'
                article.generated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Article successfully generated with CrewAI")
                logger.info(f"Article updated with generated content for ID: {article_id}")
                
            except Exception as e:
                logger.error(f"Error in CrewAI generation: {str(e)}")
                article.content = f"Error generating article: {str(e)}"
                article.status = 'error'
                db.session.commit()
                logger.error(f"Article status updated to 'error' for ID: {article_id}")
                logger.error(f"Error generating article: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in async article generation: {str(e)}")
            try:
                article = db.session.get(Article, article_id)
                if article:
                    article.status = 'error'
                    article.content = f"Error: {str(e)}"
                    db.session.commit()
                    logger.error(f"Article status updated to 'error' for ID: {article_id}")
            except Exception as inner_e:
                logger.error(f"Error updating article status: {str(inner_e)}")

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
                content="Article is being generated...\n\nPlease wait. This may take a few minutes.",
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
                args=(article_id, urls, topic, None)
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

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)
