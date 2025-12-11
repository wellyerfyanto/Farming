import os
import logging
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)

def setup_chrome_driver():
    """Setup Chrome/Chromium driver untuk Railway"""
    try:
        logger.info("Setting up Chrome/Chromium driver for Railway...")
        
        # Cek ketersediaan browser dan driver dulu
        if not check_chrome_availability():
            logger.error("Chrome/Chromium not available, cannot setup driver")
            raise RuntimeError("Chrome not available")
        
        # Setup Chrome options
        chrome_options = Options()
        
        # Railway-specific settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--remote-debugging-port=9222')
        
        # Performance & Security options
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--no-default-browser-check')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Set user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Gunakan system chromedriver
        chromedriver_path = find_system_chromedriver()
        if not chromedriver_path:
            raise RuntimeError("System chromedriver not found")
            
        logger.info(f"Using system chromedriver: {chromedriver_path}")
        
        # Set browser binary location jika ditemukan
        browser_path = find_chromium_binary()
        if browser_path:
            chrome_options.binary_location = browser_path
            logger.info(f"Using browser binary: {browser_path}")
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        logger.info("Chrome driver setup successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        raise

def find_chromium_binary():
    """Cari binary Chromium/Chrome"""
    possible_paths = [
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/local/bin/chromium',
        '/usr/local/bin/chromium-browser'
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            logger.info(f"Found browser binary at: {path}")
            return path
    
    # Cek environment variables
    env_path = os.environ.get('CHROME_BIN')
    if env_path and os.path.exists(env_path):
        logger.info(f"Found browser via CHROME_BIN: {env_path}")
        return env_path
    
    logger.warning("No browser binary found")
    return None

def find_system_chromedriver():
    """Cari chromedriver di system paths"""
    possible_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        '/usr/lib/chromium-browser/chromedriver',
        '/snap/bin/chromium.chromedriver'
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            logger.info(f"Found executable chromedriver at: {path}")
            return path
    
    # Coba dengan which command
    try:
        result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.exists(path):
                logger.info(f"Found chromedriver via which: {path}")
                return path
    except Exception as e:
        logger.warning(f"Which command failed: {e}")
    
    # Cek environment variable
    env_path = os.environ.get('CHROMEDRIVER_PATH')
    if env_path and os.path.exists(env_path):
        logger.info(f"Found chromedriver via CHROMEDRIVER_PATH: {env_path}")
        return env_path
    
    logger.error("No system chromedriver found")
    return None

def check_chrome_availability():
    """Check if Chrome/Chromium is available in the system"""
    try:
        # Cek browser binary
        browser_path = find_chromium_binary()
        if not browser_path:
            logger.error("No browser binary found")
            return False
        
        # Cek chromedriver
        chromedriver_path = find_system_chromedriver()
        if not chromedriver_path:
            logger.error("No chromedriver found")
            return False
        
        # Test browser version
        try:
            browser_result = subprocess.run([browser_path, '--version'], capture_output=True, text=True, timeout=10)
            if browser_result.returncode == 0:
                logger.info(f"Browser version: {browser_result.stdout.strip()}")
            else:
                logger.warning(f"Browser version check failed: {browser_result.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Browser version check error: {e}")
            return False
        
        # Test chromedriver version
        try:
            driver_result = subprocess.run([chromedriver_path, '--version'], capture_output=True, text=True, timeout=10)
            if driver_result.returncode == 0:
                logger.info(f"Chromedriver version: {driver_result.stdout.strip()}")
            else:
                logger.warning(f"Chromedriver version check failed: {driver_result.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Chromedriver version check error: {e}")
            return False
        
        logger.info("Chrome/Chromium availability check passed")
        return True
        
    except Exception as e:
        logger.error(f"Chrome availability check failed: {e}")
        return False

def get_browser_info():
    """Get detailed browser information untuk debug"""
    info = {
        'browser_available': False,
        'browser_binary': None,
        'browser_version': None,
        'chromedriver_available': False,
        'chromedriver_path': None,
        'chromedriver_version': None,
        'environment_variables': {
            'CHROME_BIN': os.environ.get('CHROME_BIN'),
            'CHROME_PATH': os.environ.get('CHROME_PATH'),
            'CHROMEDRIVER_PATH': os.environ.get('CHROMEDRIVER_PATH')
        }
    }
    
    try:
        # Check browser
        browser_path = find_chromium_binary()
        if browser_path:
            info['browser_binary'] = browser_path
            info['browser_available'] = True
            
            # Get browser version
            try:
                result = subprocess.run([browser_path, '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info['browser_version'] = result.stdout.strip()
            except:
                pass
        
        # Check chromedriver
        chromedriver_path = find_system_chromedriver()
        if chromedriver_path:
            info['chromedriver_path'] = chromedriver_path
            info['chromedriver_available'] = True
            
            # Get chromedriver version
            try:
                result = subprocess.run([chromedriver_path, '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info['chromedriver_version'] = result.stdout.strip()
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error getting browser info: {e}")
    
    return info
