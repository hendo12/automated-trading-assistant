import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv
from PIL import Image
from selenium.webdriver.common.keys import Keys

# Configure logging
logging.basicConfig(
    filename='tradingview_automation.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Load environment variables
load_dotenv()

GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")

ASSETS = [
    {"symbol": "BTCUSD", "timeframes": ["1H", "4H", "1D"]},
    {"symbol": "ETHUSD", "timeframes": ["1H", "4H", "1D"]},
    # Add more assets as needed
]

SCREENSHOTS_DIR = "screenshots"
ANALYSIS_DIR = "analysis"

def init_driver():
    chrome_options = Options()
    
    # Remove automation flags and add more "normal" browser behavior
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add user agent to appear more like a regular browser
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    
    # Remove headless mode for now (Google often blocks headless browsers)
    # chrome_options.add_argument("--headless")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # Additional settings to avoid detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        })
        
        # This JavaScript removes the webdriver flag
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize Chrome driver: {e}")
        raise


def login_tradingview_with_google(driver):
    try:
        # Navigate to TradingView login page
        driver.get("https://www.tradingview.com/accounts/signin/")
        logging.info("Navigated to TradingView sign-in page.")
        
        # Wait for the Google sign-in iframe
        google_iframe = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='Sign in with Google Button']"))
        )
        logging.info("Found Google sign-in iframe")
        
        # Switch to the iframe
        driver.switch_to.frame(google_iframe)
        logging.info("Switched to Google iframe")
        
        # Click the Google sign-in button within the iframe
        google_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".nsm7Bb-HzV7m-LgbsSe"))
        )
        google_button.click()
        logging.info("Clicked Google sign-in button")
        
        # Switch back to main content
        driver.switch_to.default_content()
        
        # Handle the Google OAuth popup window
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        google_window = [window for window in driver.window_handles if window != driver.current_window_handle][0]
        driver.switch_to.window(google_window)
        logging.info("Switched to Google OAuth window")
        
        # Enter Google Email
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_field.send_keys(GOOGLE_EMAIL)
        email_field.send_keys(Keys.RETURN)
        logging.info("Entered Google email")
        
        # Wait and enter password
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='Passwd']"))
        )
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='Passwd']"))
        )
        password_field.send_keys(GOOGLE_PASSWORD)
        password_field.send_keys(Keys.RETURN)
        logging.info("Entered Google password")
        
        # Switch back to main window
        WebDriverWait(driver, 30).until(lambda d: len(d.window_handles) == 1)
        driver.switch_to.window(driver.window_handles[0])
        
        # Wait for successful login
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='user-avatar']"))
        )
        logging.info("Successfully logged in to TradingView")
        
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        raise

def navigate_to_chart(driver, symbol, timeframe):
    try:
        chart_url = f"https://www.tradingview.com/chart/?symbol=COINBASE:{symbol}"
        driver.get(chart_url)
        
        # Wait for chart container to be present
        chart_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-role='chart-container']"))
        )
        
        # Wait for timeframe button and click
        timeframe_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[@data-name='{timeframe}']"))
        )
        timeframe_button.click()
        
        # Wait for chart to update after timeframe change
        time.sleep(2)  # Keep minimal sleep for chart rendering
        
        logging.info(f"Successfully navigated to {symbol} {timeframe} chart")
    except TimeoutException as e:
        logging.error(f"Timeout while navigating to chart {symbol} {timeframe}: {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to navigate to chart {symbol} {timeframe}: {e}")
        raise

def capture_screenshot(driver, symbol, timeframe):
    if not os.path.exists(SCREENSHOTS_DIR):
        os.makedirs(SCREENSHOTS_DIR)
    
    try:
        # Wait for chart to be fully loaded
        chart_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-role='chart-container']"))
        )

         # Ensure chart is in viewport
        driver.execute_script("arguments[0].scrollIntoView(true);", chart_element)
        time.sleep(1)  # Brief pause for scroll completion
        
        # Take screenshot with error handling
        temp_screenshot = "temp_screenshot.png"
        try:
            driver.save_screenshot(temp_screenshot)
            
            # Process screenshot
            image = Image.open(temp_screenshot)
            location = chart_element.location_once_scrolled_into_view
            size = chart_element.size
            
            # Crop image
            left = location['x']
            top = location['y']
            right = location['x'] + size['width']
            bottom = location['y'] + size['height']
            chart_image = image.crop((left, top, right, bottom))
            
            # Save with timestamp to prevent overwrites
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_{timeframe}_{timestamp}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)
            chart_image.save(filepath)
            logging.info(f"Screenshot saved: {filepath}")
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_screenshot):
                os.remove(temp_screenshot)
                
    except Exception as e:
        logging.error(f"Failed to capture screenshot for {symbol} {timeframe}: {e}")
        raise

def validate_configuration():
    """Validate environment variables and configuration"""
    if not GOOGLE_EMAIL or not GOOGLE_PASSWORD:
        raise ValueError("Google credentials not found in environment variables")
    if not ASSETS:
        raise ValueError("No assets configured for processing")

def process_assets(driver):
    for asset in ASSETS:
        symbol = asset["symbol"]
        for timeframe in asset["timeframes"]:
            navigate_to_chart(driver, symbol, timeframe)
            capture_screenshot(driver, symbol, timeframe)
            time.sleep(2)  # Optional delay between captures

if __name__ == "__main__":
    try:
        validate_configuration()
        driver = init_driver()
        login_tradingview_with_google(driver)
        process_assets(driver)
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.quit()