from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import os
import json
import random

# ----------------------------
# CONFIG
# ----------------------------
URL = "https://click.ledeinchristus.com/checkin?cong=Centurion"
VISITOR_NAME = "Toets Import"
UNKNOWN_NAME = "Unknown"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FOLDER = os.path.join(SCRIPT_DIR, "Download")
os.makedirs(LOCAL_FOLDER, exist_ok=True)
FAILED_LOG_PATH = LOCAL_FOLDER
CSV_PATH = os.path.join(LOCAL_FOLDER, "export_attendance.csv")

# ----------------------------
# SELENIUM SETUP - ANTI DETECTION
# ----------------------------
chrome_options = Options()

# Basic headless options
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-software-rasterizer")

# Anti-detection options
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--allow-running-insecure-content")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-default-apps")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-browser-side-navigation")
chrome_options.add_argument("--disable-features=VizDisplayCompositor")
chrome_options.add_argument("--disable-background-timer-throttling")
chrome_options.add_argument("--disable-backgrounding-occluded-windows")
chrome_options.add_argument("--disable-renderer-backgrounding")
chrome_options.add_argument("--disable-ipc-flooding-protection")
chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")

# Random user agent
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]
chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

# Try to find Chrome binary
chrome_binary_locations = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium"
]

for location in chrome_binary_locations:
    if os.path.exists(location):
        chrome_options.binary_location = location
        print(f"Using Chrome binary at: {location}")
        break
else:
    print("Warning: Chrome binary not found in common locations")

# Try to find chromedriver
chromedriver_locations = [
    "/usr/local/bin/chromedriver",
    "/usr/bin/chromedriver",
    "/usr/lib/chromium-browser/chromedriver"
]

service = None
for location in chromedriver_locations:
    if os.path.exists(location):
        service = Service(location)
        print(f"Using ChromeDriver at: {location}")
        break
else:
    print("Warning: ChromeDriver not found, trying default location")
    service = Service()

try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Additional anti-detection measures
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": driver.execute_script("return navigator.userAgent;").replace("Headless", "")
    })
    
    print("Chrome driver initialized successfully")
except Exception as e:
    print(f"Failed to initialize Chrome driver: {e}")
    exit(1)

# ----------------------------
# READ CSV
# ----------------------------

if not os.path.exists(CSV_PATH):
    print(f"⚠️ CSV file not found at {CSV_PATH}, nothing to process.")
    driver.quit()
    exit(0)

df = pd.read_csv(CSV_PATH)
df['Number'] = df['Number'].astype(str).str.strip("'")  # remove quotes from numbers
df['Family'] = df['Family'].fillna('')      # ensure no NaN family names

processed_families = set()
failed_entries = []

# ----------------------------
# HELPER FUNCTION
# ----------------------------
def human_like_delay():
    """Add random human-like delays"""
    time.sleep(random.uniform(0.5, 2.0))

def human_like_type(element, text):
    """Type like a human with random delays"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def check_in_member(number, family_rows, is_single):
    """Attempts check-in for one member.
       Returns True if successful, False if needs next try."""
    try:
        print(f"Attempting check-in for number: {number}")
        driver.get(URL)
        human_like_delay()
         # Wait for page to load completely
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for Cloudflare challenge
        if "challenge" in driver.page_source.lower() or "cloudflare" in driver.page_source.lower():
            print("⚠️ Cloudflare challenge detected, waiting...")
            time.sleep(10)  # Wait for potential challenge to resolve
            driver.save_screenshot("cloudflare_challenge.png")

        
        input_box = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Personal Number']"))
        )

        # Human-like interaction with input
        ActionChains(driver).move_to_element(input_box).click().perform()
        human_like_delay()
        input_box.clear()
        human_like_delay()
        
        if number:
            human_like_type(input_box, number)
        human_like_delay()
        # Find and click submit button
        submit_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit')]"))
        )
        ActionChains(driver).move_to_element(submit_btn).click().perform()
        human_like_delay()

        # Single member success
        thank_you = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Thank you for checking in')]"))
        )
        if is_single:
            try:
                submit_btn2 = driver.find_element(By.XPATH, "(//button[contains(text(),'Submit')])[last()]")
                submit_btn2.click()
            except:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                driver.save_screenshot(f"screenshot_{timestamp}.png")
                pass
        print(f"✅ Checked in successfully with number {number}")
        time.sleep(2)
        return True

    except:
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(f"screenshot_{timestamp}.png")
        try:
            # Check for family selection page
            family_members = WebDriverWait(driver, 4).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH,
                     "//div[contains(@class,'group-item')]//div[contains(@class,'Text') and not(contains(text(),'Already a Member')) "
                     "and not(contains(text(),'Visiting')) and not(contains(text(),'I have a Church'))]"))
            )
            if family_members:
                family_names_csv = [str(name).lower() for name in family_rows['Name']]
                for member in family_members:
                    member_name_page = member.text.strip().lower()
                    if any(member_name_page in csv_name for csv_name in family_names_csv):
                        try:
                            button = member.find_element(By.XPATH, "./preceding-sibling::button")
                            button.click()
                            print(f"   ✅ Selected {member.text.strip()}")
                        except:
                            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                            driver.save_screenshot(f"screenshot_{timestamp}.png")
                            print(f"   ⚠️ Could not select {member.text.strip()}")
                    else:
                        print(f"   ⏩ Skipping {member.text.strip()} (not in CSV family)")
                family_submit_btn = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, "(//button[contains(text(),'Submit')])[last()]"))
                )
                family_submit_btn.click()
                print(f"✅ Family checked in successfully with number {number}")
                time.sleep(1)
                return True
            try:
                thank_you = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Thank you for checking in')]"))
                )
                print(f"✅ Family checked in successfully with number {number}")
            except:
                timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                driver.save_screenshot(f"screenshot_{timestamp}.png")
                print(f"⚠️ Family submission clicked but no confirmation detected for number {number}")
                return False

        except:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(f"screenshot_{timestamp}.png")
            if is_single:
                # Visitor / unknown for single member
                try:
                    visiting_option = WebDriverWait(driver, 4).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Visiting')]"))
                    )
                    visiting_option.click()
                    name_input = WebDriverWait(driver, 4).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Full names']"))
                    )
                    name_input.send_keys(family_rows.iloc[0]['Name'])
                    visitor_submit_btn = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, "(//button[contains(text(),'Submit')])[last()]"))
                    )
                    visitor_submit_btn.click()
                    print(f"✅ Visitor checked in successfully with number {number}")
                    time.sleep(1)
                    return True

                except:
                    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
                    driver.save_screenshot(f"screenshot_{timestamp}.png")
                    print(f"⚠️ Single-member {number} failed to check in.")
                    return False
            else:
                print(f"⚠️ Multi-member {number} failed, trying next in family...")
                return False


def normalize_number(number):
    if pd.isna(number) or number.strip() == '':
        return ''  # leave empty numbers empty
    # Remove non-numerical characters
    num = ''.join(filter(str.isdigit, str(number)))
    # Prepend 0 if 9 digits
    if len(num) == 9 and not num.startswith('0'):
        num = '0' + num
    return num


# ----------------------------
# PROCESS ROWS
# ----------------------------
for family_name in df['Family'].unique():
    if family_name in processed_families:
        continue

    family_rows = df[df['Family'] == family_name]
    is_single = len(family_rows) == 1
    family_success = False

    # --- NEW: handle empty family as single row ---
    if family_name.strip() == '':
        # take the first row with empty family
        for _, row in family_rows.iterrows():
            normalized_number = normalize_number(row['Number'])
            success = check_in_member(normalized_number, family_rows.iloc[[0]], True)  # pass a single-row DataFrame
            if not success:
                failed_entries.append({'Family': '', 'Name': row['Name'], 'Number': row['Number']})
        processed_families.add(family_name)
        continue
    # ------------------------------

    # Try each number in family until success
    for _, row in family_rows.iterrows():
        normalized_number = normalize_number(row['Number'])
        success = check_in_member(normalized_number, family_rows, is_single)
        if success:
            family_success = True
            break
        else:
            time.sleep(2)  # wait before next try

    if not family_success:
        for _, row in family_rows.iterrows():
            failed_entries.append(row.to_dict())

    processed_families.add(family_name)

# ----------------------------
# Failed entries upload
# ----------------------------
if failed_entries:
    failed_df = pd.DataFrame(failed_entries)
    local_file = os.path.join(SCRIPT_DIR, f"failed_entries_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv")
    failed_df.to_csv(local_file, index=False)

    print(f"⚠️ Failed entries saved to {local_file}")

# ----------------------------
# CLOSE DRIVER
# ----------------------------
driver.quit()





