import os

APP_NAME = os.getenv('APP_NAME', 'Trend2Sketch Studio')
DATA_DIR = os.getenv('TREND2SKETCH_DATA_DIR', '/var/data/trend2sketch-studio')
DB_PATH = os.path.join(DATA_DIR, 'studio.db')
IMAGE_DIR = os.path.join(DATA_DIR, 'designs')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
TEXT_MODEL = os.getenv('OPENAI_TEXT_MODEL', 'gpt-5.6-luna')
VISION_MODEL = os.getenv('OPENAI_VISION_MODEL', TEXT_MODEL)
IMAGE_MODEL = os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2')
IMAGE_QUALITY = os.getenv('OPENAI_IMAGE_QUALITY', 'low')
IMAGE_SIZE = os.getenv('OPENAI_IMAGE_SIZE', '1024x1024')

AUTO_INTERVAL_MINUTES = int(os.getenv('AUTO_INTERVAL_MINUTES', '30'))
AUTO_RUN_ON_START = os.getenv('AUTO_RUN_ON_START', 'true').lower() == 'true'
CONCEPT_POOL_SIZE = int(os.getenv('CONCEPT_POOL_SIZE', '300'))
MAX_RENDER_PER_CYCLE = int(os.getenv('MAX_RENDER_PER_CYCLE', '30'))
DISPLAY_THRESHOLD = int(os.getenv('DISPLAY_THRESHOLD', '95'))
GENERATION_CONCURRENCY = int(os.getenv('GENERATION_CONCURRENCY', '3'))

DAILY_API_BUDGET_USD = float(os.getenv('DAILY_API_BUDGET_USD', '10'))
EST_IMAGE_COST_USD = float(os.getenv('EST_IMAGE_COST_USD', '0.03'))
EST_TEXT_CYCLE_COST_USD = float(os.getenv('EST_TEXT_CYCLE_COST_USD', '0.08'))
MIN_FREE_DISK_GB = float(os.getenv('MIN_FREE_DISK_GB', '1.5'))
MAX_MEMORY_PERCENT = float(os.getenv('MAX_MEMORY_PERCENT', '82'))
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '30'))

APP_PASSWORD = os.getenv('APP_PASSWORD', '')
APP_PUBLIC_URL = os.getenv('APP_PUBLIC_URL', '')

RESEARCH_DOMAINS = [
    'tanishq.co.in',
    'malabargoldanddiamonds.com',
    'kalyanjewellers.net',
    'joyalukkas.in',
]
