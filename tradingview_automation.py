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
import pandas as pd

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

DATA_EXPORT_DIR = os.path.join("data", "exports")
if not os.path.exists(DATA_EXPORT_DIR):
    os.makedirs(DATA_EXPORT_DIR, exist_ok=True)

# SCREENSHOTS_DIR = "screenshots"
# ANALYSIS_DIR = "analysis"

def init_driver():
    chrome_options = Options()

    # Persistent user data directory:
    # This directory will hold your Chrome profile data (cookies, sessions).
    # Make sure to use an absolute path and a dedicated folder.
    user_data_dir = os.path.abspath("chrome_user_data")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--profile-directory=Default")

    # Configure automatic downloads
    prefs = {
        "download.default_directory": os.path.abspath(DATA_EXPORT_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
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
        # Navigate to TradingView
        driver.get("https://www.tradingview.com/")
        logging.info("Navigated to TradingView sign-in page.")
        
        # Check if already logged in by looking for a user-specific element
        try:
            # Wait a short time for user-specific element (like avatar or username)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='user-avatar']"))
            )
            logging.info("Already logged in, skipping login process")
            return True
            
        except TimeoutException:
            # Not logged in, proceed with Google login
            logging.info("Not logged in, proceeding with Google login flow")
            
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
            
            # Wait for successful login by checking for user avatar
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='user-avatar']"))
            )
            logging.info("Successfully logged in to TradingView")
            
    except Exception as e:
        logging.error(f"Login via Google OAuth failed: {str(e)}")
        raise

def navigate_to_chart(driver):
    try:
        # Navigate directly to charts
        driver.get("https://www.tradingview.com/chart/")
        logging.info("Navigating to chart page")
        
        # Wait for chart container to confirm we're on the right page
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#tv_chart_container"))
        )
        logging.info("Successfully loaded chart page")
        
    except Exception as e:
        logging.error(f"Failed to navigate to chart: {str(e)}")
        raise

def export_chart_data(driver, symbol, timeframe):
    try:
        # Open the layout dropdown menu (the "carot" menu)
        layout_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-role='menuitem' and @aria-haspopup='dialog']"))
        )
        layout_button.click()
        logging.info("Opened layout dropdown menu")

        # Click on "Export chart data…" menu item using your specific selector
        export_item = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'accessible-NQERJsv9') and @data-role='menuitem']//span[contains(text(), 'Export chart data…')]"))
        )
        export_item.click()
        logging.info("Clicked 'Export chart data…'")

        # Click on the 'Export' button using your specific selector
        export_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-name='submit-button' and .//span[text()='Export']]"))
        )
        export_button.click()
        logging.info("Clicked 'Export' button")

        # Wait for the file to download
        time.sleep(5)  # Give time for the file to be saved

        # Handle the downloaded file
        csv_files = [f for f in os.listdir(DATA_EXPORT_DIR) if f.endswith(".csv")]
        if csv_files:
            latest_csv = csv_files[0]
            new_name = f"{symbol}_{timeframe}_{int(time.time())}.csv"
            os.rename(
                os.path.join(DATA_EXPORT_DIR, latest_csv),
                os.path.join(DATA_EXPORT_DIR, new_name)
            )
            logging.info(f"Renamed downloaded CSV to {new_name}")
            return os.path.join(DATA_EXPORT_DIR, new_name)
        else:
            logging.warning("No CSV file found after export")
            return None

    except Exception as e:
        logging.error(f"Failed to export chart data for {symbol} {timeframe}: {e}")
        raise


def validate_configuration():
    """Validate environment variables and configuration"""
    if not GOOGLE_EMAIL or not GOOGLE_PASSWORD:
        raise ValueError("Google credentials not found in environment variables")
    if not ASSETS:
        raise ValueError("No assets configured for processing")

def process_assets(driver):
    """Process all assets and export their data"""
    results = []
    for asset in ASSETS:
        symbol = asset["symbol"]
        for timeframe in asset["timeframes"]:
            try:
                logging.info(f"Processing {symbol} {timeframe}")
                navigate_to_chart(driver)
                
                # Allow chart to load completely
                time.sleep(3)
                
                # Export chart data
                exported_file = export_chart_data(driver, symbol, timeframe)
                results.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data_file": exported_file
                })
                
                logging.info(f"Successfully processed {symbol} {timeframe}")
                
            except Exception as e:
                logging.error(f"Failed to process {symbol} {timeframe}: {e}")
                continue
                
    return results

def parse_chart_data(csv_path):
    df = pd.read_csv(csv_path)
    # Process indicators
    return df

def prepare_data_for_analysis(df):
    analysis_data = {
        "price_data": df['close'].tolist(),
        "volume": df['volume'].tolist(),
        "indicators": {
            "rsi": df['rsi'].tolist() if 'rsi' in df else None,
            "macd": df['macd'].tolist() if 'macd' in df else None,
            # Add more indicators
        }
    }
    return analysis_data

def navigate_to_initial_chart(driver):
    """Navigate to initial chart after login to ensure proper loading"""
    try:
        # Navigate to a default chart (using first asset from ASSETS list)
        default_symbol = ASSETS[0]["symbol"]
        default_timeframe = ASSETS[0]["timeframes"][0]
        
        chart_url = f"https://www.tradingview.com/chart/?symbol=COINBASE:{default_symbol}"
        driver.get(chart_url)
        
        # Wait for chart container to be present
        chart_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-role='chart-container']"))
        )
        
        # Wait for timeframe button and click
        timeframe_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[@data-name='{default_timeframe}']"))
        )
        timeframe_button.click()
        
        # Wait for chart to load
        time.sleep(3)
        
        logging.info(f"Successfully loaded initial chart: {default_symbol} {default_timeframe}")
        
    except Exception as e:
        logging.error(f"Failed to load initial chart: {e}")
        raise

def main():
    driver = setup_driver()  # Your existing driver setup
    try:
        login_tradingview_with_google(driver)
        navigate_to_chart(driver)
        # Continue with your symbol selection and timeframe code
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    try:
        validate_configuration()
        driver = init_driver()
        login_tradingview_with_google(driver)
        navigate_to_initial_chart(driver) 
        process_assets(driver)
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.quit()