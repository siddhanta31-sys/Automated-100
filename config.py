import os

APP_NAME = os.getenv('APP_NAME', 'Trend2Sketch Studio')
DATA_DIR = os.getenv('TREND2SKETCH_DATA_DIR', '/var/data/trend2sketch-studio')
DB_PATH = os.path.join(DATA_DIR, 'studio.db')
IMAGE_DIR = os.path.join(DATA_DIR, 'designs')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
TEXT_MODEL = os.getenv('OPENAI_TEXT_MODEL', 'gpt-5.6-terra')
VISION_MODEL = os.getenv('OPENAI_VISION_MODEL', TEXT_MODEL)
IMAGE_MODEL = os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2')
IMAGE_QUALITY = os.getenv('OPENAI_IMAGE_QUALITY', 'medium')
IMAGE_SIZE = os.getenv('OPENAI_IMAGE_SIZE', '1024x1024')

AUTO_INTERVAL_MINUTES = int(os.getenv('AUTO_INTERVAL_MINUTES', '1440'))
# V4 is manual-first. Automation can only run after the owner explicitly enables it.
AUTO_RUN_ON_START = os.getenv('AUTO_RUN_ON_START', 'false').lower() == 'true'
CONCEPT_POOL_SIZE = int(os.getenv('CONCEPT_POOL_SIZE', '12'))
MAX_RENDER_PER_CYCLE = int(os.getenv('MAX_RENDER_PER_CYCLE', '3'))
DISPLAY_THRESHOLD = int(os.getenv('DISPLAY_THRESHOLD', '95'))
PRE_RENDER_MIN_SCORE = float(os.getenv('PRE_RENDER_MIN_SCORE', '70'))
FINAL_PRE_WEIGHT = float(os.getenv('FINAL_PRE_WEIGHT', '0.20'))
FINAL_VISUAL_WEIGHT = float(os.getenv('FINAL_VISUAL_WEIGHT', '0.80'))
GENERATION_CONCURRENCY = int(os.getenv('GENERATION_CONCURRENCY', '3'))

API_TIMEOUT_SECONDS = float(os.getenv('API_TIMEOUT_SECONDS', '180'))
API_MAX_RETRIES = int(os.getenv('API_MAX_RETRIES', '3'))
CYCLE_STALE_MINUTES = int(os.getenv('CYCLE_STALE_MINUTES', '75'))
CONCEPT_BATCH_SIZE = int(os.getenv('CONCEPT_BATCH_SIZE', '40'))
CONCEPT_MAX_BATCHES = int(os.getenv('CONCEPT_MAX_BATCHES', '15'))
RENDER_RETRIES = int(os.getenv('RENDER_RETRIES', '2'))

DAILY_API_BUDGET_USD = float(os.getenv('DAILY_API_BUDGET_USD', '2'))
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
    'grtjewels.com',
    'vbjewellers.com',
    'nacjewellers.com',
    'pmjewels.com',
    'gia.edu',
]


# Live-selectable product categories. These are defaults for the UI only; users can also add custom categories.
PRODUCT_CATEGORIES = [
    'Choker',
    'Short Necklace',
    'Long Necklace / Haram',
    'Bridal Necklace',
    'Pendant',
    'Chain',
    'Mangalsutra',
    'Stud Earrings',
    'Drop Earrings',
    'Jhumka',
    'Chandbali',
    'Hoops',
    'Ring',
    'Cocktail Ring',
    'Bangle',
    'Kada',
    'Bracelet',
    'Vaddanam / Waist Belt',
    'Vanki / Armlet',
    'Maang Tikka / Nethi Chutti',
    'Matha Patti',
    'Nose Ring / Nath',
    'Anklet',
    'Toe Ring',
    'Brooch',
    'Hair Ornament / Jada Billa',
    'Temple Jewellery Set',
    'Bridal Set',
]

CATEGORY_PRESETS = {
    'All categories': PRODUCT_CATEGORIES,
    'Neckwear': ['Choker','Short Necklace','Long Necklace / Haram','Bridal Necklace','Pendant','Chain','Mangalsutra'],
    'Earrings': ['Stud Earrings','Drop Earrings','Jhumka','Chandbali','Hoops'],
    'Hand jewellery': ['Ring','Cocktail Ring','Bangle','Kada','Bracelet','Vanki / Armlet'],
    'South Indian bridal': ['Long Necklace / Haram','Bridal Necklace','Jhumka','Vaddanam / Waist Belt','Vanki / Armlet','Maang Tikka / Nethi Chutti','Hair Ornament / Jada Billa','Temple Jewellery Set','Bridal Set'],
    'Diamond everyday': ['Choker','Short Necklace','Pendant','Chain','Stud Earrings','Drop Earrings','Hoops','Ring','Bracelet','Mangalsutra'],
}


# Fast-pipeline defaults. Live speed mode can be changed in the app without redeploying.
FAST_CONCEPT_WORKERS = int(os.getenv('FAST_CONCEPT_WORKERS', '4'))
BALANCED_CONCEPT_WORKERS = int(os.getenv('BALANCED_CONCEPT_WORKERS', '3'))
DEEP_CONCEPT_WORKERS = int(os.getenv('DEEP_CONCEPT_WORKERS', '2'))
FAST_SCORE_WORKERS = int(os.getenv('FAST_SCORE_WORKERS', '4'))
BALANCED_SCORE_WORKERS = int(os.getenv('BALANCED_SCORE_WORKERS', '3'))
DEEP_SCORE_WORKERS = int(os.getenv('DEEP_SCORE_WORKERS', '2'))

# Design Director / R&D intelligence
DESIGN_DIRECTOR_VERSION = '1.0'
DEEP_RESEARCH_AGENTS = int(os.getenv('DEEP_RESEARCH_AGENTS', '3'))
DEEP_RENDER_POOL_MULTIPLIER = int(os.getenv('DEEP_RENDER_POOL_MULTIPLIER', '6'))
