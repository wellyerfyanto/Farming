import os
import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class DeviceController:
    def __init__(self, device_id, config, profile_manager):
        self.device_id = device_id
        self.config = config
        self.profile_manager = profile_manager
        self.driver = None
        self.current_profile = None
        self.current_task = None
        self.session_start_time = None
        self.is_active = False
        self.google_login_success = False
        
        # Device capabilities
        self.capabilities = {
            'browser_name': 'chrome',
            'max_session_duration': config.get('max_session_duration', 3600),
            'proxy_enabled': config.get('proxy_enabled', False),
            'headless': True,
            'save_session': config.get('save_session', True)
        }

    def _setup_chrome_driver(self, profile):
        """Setup Chrome driver dengan comprehensive error handling"""
        try:
            logger.info(f"Setting up Chrome driver for {self.device_id}")
            
            from chrome_setup import setup_chrome_driver, check_chrome_availability, get_browser_info
            
            # Cek ketersediaan Chrome/Chromium secara detail
            browser_info = get_browser_info()
            logger.info(f"Browser info for {self.device_id}: {browser_info}")
            
            if not check_chrome_availability():
                error_msg = f"Chrome not available for {self.device_id}. Browser: {browser_info.get('browser_available')}, Driver: {browser_info.get('chromedriver_available')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            # Setup Chrome driver
            driver = setup_chrome_driver()
            
            # Apply profile settings jika ada
            if profile and profile.get('profile_path'):
                logger.info(f"Profile path available for {self.device_id}: {profile['profile_path']}")
            
            logger.info(f"Chrome driver setup successful for {self.device_id}")
            return driver
            
        except Exception as e:
            logger.error(f"Chrome setup failed for {self.device_id}: {e}")
            raise RuntimeError(f"Chrome setup failed: {str(e)}")

    def start_session(self, profile, task_config):
        """Start browser session dengan comprehensive error handling"""
        try:
            self.current_profile = profile
            self.current_task = task_config
            
            logger.info(f"Starting session for device {self.device_id}")
            
            # Setup Chrome driver
            self.driver = self._setup_chrome_driver(profile)
            
            if self.driver is None:
                logger.error(f"No driver available for {self.device_id}")
                return False
            
            # Check if already logged in via profile (cookies)
            if self.profile_manager.is_google_logged_in(self.device_id):
                logger.info(f"Checking existing Google session for {self.device_id}")
                
                # Try to load cookies
                if self._load_session_cookies():
                    time.sleep(2)
                    
                # Check if still logged in
                if self._check_google_logged_in():
                    self.google_login_success = True
                    logger.info(f"Resumed Google session for {self.device_id}")
                else:
                    # Session expired, need to login again
                    logger.info(f"Google session expired for {self.device_id}")
                    self.google_login_success = False
            
            # Login Google jika belum login dan ada akun
            if not self.google_login_success:
                google_account = self.config.get('google_account')
                if google_account and google_account.get('email') and google_account.get('password'):
                    logger.info(f"Attempting Google login for {self.device_id}")
                    login_success = self._login_google(google_account['email'], google_account['password'])
                    if login_success:
                        self.google_login_success = True
                        logger.info(f"Google login successful for {self.device_id}")
                    else:
                        logger.warning(f"Google login failed for {self.device_id}")
            
            # Jika tidak ada Google account atau login gagal, lanjutkan tanpa login
            if not self.google_login_success:
                logger.info(f"No Google login for {self.device_id}, continuing without login")
            
            # Execute task (jika driver masih aktif)
            if self.driver:
                logger.info(f"Executing task for {self.device_id}: {task_config.get('type')}")
                self._execute_task(task_config)
                self.session_start_time = time.time()
                self.is_active = True
                logger.info(f"Device {self.device_id} started successfully")
                return True
            else:
                logger.error(f"Driver not available for {self.device_id} after setup")
                return False
            
        except Exception as e:
            logger.error(f"Device {self.device_id} failed to start: {e}")
            self.is_active = False
            return False

    def _save_session_cookies(self):
        """Save session cookies untuk persistence"""
        if not self.capabilities['save_session'] or not self.driver:
            return
        
        try:
            cookies = self.driver.get_cookies()
            self.profile_manager.save_cookies(self.device_id, cookies)
            logger.info(f"Saved cookies for {self.device_id}")
        except Exception as e:
            logger.warning(f"Could not save cookies for {self.device_id}: {e}")

    def _load_session_cookies(self):
        """Load session cookies untuk persistence"""
        if not self.capabilities['save_session'] or not self.driver:
            return False
        
        try:
            cookies = self.profile_manager.load_cookies(self.device_id)
            if cookies:
                # Clear existing cookies first
                self.driver.delete_all_cookies()
                
                # Add saved cookies
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        logger.warning(f"Could not add cookie: {e}")
                
                # Refresh to apply cookies
                self.driver.refresh()
                logger.info(f"Loaded cookies for {self.device_id}")
                return True
        except Exception as e:
            logger.warning(f"Could not load cookies for {self.device_id}: {e}")
        
        return False

    def _check_google_logged_in(self):
        """Check if already logged in to Google"""
        if not self.driver:
            return False
            
        try:
            # Try multiple methods to check login status
            check_methods = [
                self._check_gmail_login,
                self._check_google_account_login,
                self._check_google_home_login
            ]
            
            for method in check_methods:
                if method():
                    return True
                    
        except Exception as e:
            logger.warning(f"Error checking Google login status for {self.device_id}: {e}")
        
        return False

    def _check_gmail_login(self):
        """Check login via Gmail"""
        try:
            self.driver.get("https://mail.google.com/mail/u/0/")
            time.sleep(3)
            
            # Check if we're on Gmail inbox (not login page)
            if "mail.google.com" in self.driver.current_url:
                if "signin" not in self.driver.current_url and "accountchooser" not in self.driver.current_url:
                    return True
                    
            # Check for inbox elements
            inbox_indicators = [
                "//div[contains(@aria-label, 'Inbox')]",
                "//div[contains(@role, 'main')]",
                "//div[contains(@class, 'UI')]"
            ]
            
            for indicator in inbox_indicators:
                try:
                    if self.driver.find_elements(By.XPATH, indicator):
                        return True
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Gmail login check failed: {e}")
            
        return False

    def _check_google_account_login(self):
        """Check login via Google Account page"""
        try:
            self.driver.get("https://myaccount.google.com/")
            time.sleep(3)
            
            # If redirected to login page, not logged in
            if "signin" in self.driver.current_url or "accounts.google.com" in self.driver.current_url:
                return False
                
            # Check for account overview elements
            account_indicators = [
                "//h1[contains(text(), 'Welcome')]",
                "//div[contains(text(), 'Your Google Account')]",
                "//a[contains(@href, 'myaccount.google.com')]"
            ]
            
            for indicator in account_indicators:
                try:
                    if self.driver.find_elements(By.XPATH, indicator):
                        return True
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Google Account login check failed: {e}")
            
        return False

    def _check_google_home_login(self):
        """Check login via Google homepage"""
        try:
            self.driver.get("https://www.google.com")
            time.sleep(2)
            
            # Check for user avatar or account indicator
            avatar_indicators = [
                "//a[contains(@href, 'myaccount.google.com')]",
                "//img[contains(@alt, 'Google Account')]",
                "//div[contains(@class, 'gb_ua')]",
                "//a[contains(@aria-label, 'Google Account')]"
            ]
            
            for indicator in avatar_indicators:
                try:
                    if self.driver.find_elements(By.XPATH, indicator):
                        return True
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Google homepage login check failed: {e}")
            
        return False

    def _login_google(self, email, password):
        """Login ke Google dengan email dan password - improved version"""
        if not self.driver:
            return False
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Device {self.device_id} attempting Google login (attempt {attempt + 1}): {email}")
                
                # Coba beberapa URL login Google yang berbeda
                login_urls = [
                    "https://accounts.google.com/signin/v2/identifier",
                    "https://accounts.google.com/ServiceLogin",
                    "https://accounts.google.com/v3/signin"
                ]
                
                for login_url in login_urls:
                    try:
                        self.driver.get(login_url)
                        time.sleep(3)
                        
                        # Cek jika sudah login
                        if self._check_google_logged_in():
                            logger.info("Already logged in")
                            return True
                        
                        # Cari email field
                        email_selectors = [
                            (By.ID, "identifierId"),
                            (By.NAME, "identifier"),
                            (By.CSS_SELECTOR, "input[type='email']"),
                            (By.XPATH, "//input[@type='email']"),
                            (By.CSS_SELECTOR, "input[autocomplete='username']")
                        ]
                        
                        email_field = None
                        for selector_type, selector_value in email_selectors:
                            try:
                                email_field = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((selector_type, selector_value))
                                )
                                if email_field.is_displayed() and email_field.is_enabled():
                                    break
                                email_field = None
                            except:
                                continue
                        
                        if email_field:
                            break  # Keluar dari loop URL
                    except:
                        continue
                
                if not email_field:
                    logger.error(f"Could not find email field on attempt {attempt + 1}")
                    # Coba method alternatif: direct ke Gmail
                    try:
                        self.driver.get("https://mail.google.com")
                        time.sleep(3)
                        
                        # Cek jika sudah redirect ke login
                        if "accounts.google.com" in self.driver.current_url:
                            # Cari email field di halaman login Gmail
                            email_field = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
                            )
                    except Exception as e:
                        logger.error(f"Alternative login method failed: {e}")
                        continue
                
                if not email_field:
                    continue
                
                # Clear dan ketik email
                try:
                    email_field.clear()
                    self._type_like_human(email_field, email)
                    time.sleep(1)
                except:
                    # Coba dengan JavaScript
                    self.driver.execute_script("arguments[0].value = arguments[1];", email_field, email)
                
                # Cari tombol next
                next_button = None
                next_selectors = [
                    (By.ID, "identifierNext"),
                    (By.CSS_SELECTOR, "button[type='button']"),
                    (By.CSS_SELECTOR, "div[role='button']"),
                    (By.XPATH, "//span[contains(text(), 'Next')]"),
                    (By.XPATH, "//button[contains(., 'Next')]")
                ]
                
                for selector_type, selector_value in next_selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector_value)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                next_button = element
                                break
                        if next_button:
                            break
                    except:
                        continue
                
                if next_button:
                    try:
                        next_button.click()
                    except:
                        # Coba dengan JavaScript
                        self.driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)
                else:
                    # Coba tekan Enter
                    email_field.send_keys(Keys.RETURN)
                    time.sleep(3)
                
                # Tunggu untuk halaman password muncul
                time.sleep(3)
                
                # Cari password field dengan lebih banyak opsi
                password_field = None
                password_selectors = [
                    (By.NAME, "password"),
                    (By.NAME, "Passwd"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                    (By.XPATH, "//input[@type='password']"),
                    (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                    (By.ID, "password"),
                    (By.ID, "Passwd")
                ]
                
                for selector_type, selector_value in password_selectors:
                    try:
                        password_field = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        if password_field.is_displayed():
                            break
                        password_field = None
                    except:
                        continue
                
                if not password_field:
                    # Coba cari dengan XPath yang lebih umum
                    try:
                        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        for inp in all_inputs:
                            if inp.get_attribute("type") == "password" and inp.is_displayed():
                                password_field = inp
                                break
                    except:
                        pass
                
                if not password_field:
                    logger.error(f"Password field not found, current URL: {self.driver.current_url}")
                    # Simpan screenshot untuk debugging
                    try:
                        self.driver.save_screenshot(f"debug_password_not_found_{attempt}.png")
                    except:
                        pass
                    continue
                
                # Isi password
                try:
                    password_field.clear()
                    self._type_like_human(password_field, password)
                    time.sleep(1)
                except:
                    self.driver.execute_script("arguments[0].value = arguments[1];", password_field, password)
                
                # Cari tombol login/sign in
                login_button = None
                login_selectors = [
                    (By.ID, "passwordNext"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.CSS_SELECTOR, "button[type='button']"),
                    (By.XPATH, "//span[contains(text(), 'Sign in')]"),
                    (By.XPATH, "//button[contains(., 'Sign in')]"),
                    (By.XPATH, "//div[contains(text(), 'Sign in')]")
                ]
                
                for selector_type, selector_value in login_selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector_value)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                login_button = element
                                break
                        if login_button:
                            break
                    except:
                        continue
                
                if login_button:
                    try:
                        login_button.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", login_button)
                else:
                    # Coba tekan Enter
                    password_field.send_keys(Keys.RETURN)
                
                time.sleep(5)
                
                # Cek challenge
                if self._handle_login_challenges():
                    logger.warning("Login challenge detected, skipping...")
                    return False
                
                # Verifikasi login
                if self._check_google_logged_in():
                    logger.info(f"Google login successful for {email}")
                    self._save_session_cookies()
                    self.profile_manager.mark_google_logged_in(self.device_id, email)
                    return True
                else:
                    logger.warning(f"Login verification failed, URL: {self.driver.current_url}")
                    
            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} failed: {str(e)}")
                try:
                    self.driver.save_screenshot(f"login_error_{attempt}.png")
                except:
                    pass
                continue
        
        logger.error(f"All {max_attempts} login attempts failed")
        return False

    def _type_like_human(self, element, text):
        """Type text like a human with random delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))  # Random typing speed

    def _handle_login_challenges(self):
        """Handle login challenges like 2FA, recovery email, etc."""
        try:
            # Check for recovery email challenge
            recovery_selectors = [
                (By.NAME, "knowledgePreregisteredEmailResponse"),
                (By.XPATH, "//input[contains(@name, 'knowledge')]")
            ]
            
            for selector_type, selector_value in recovery_selectors:
                try:
                    if self.driver.find_elements(selector_type, selector_value):
                        logger.warning("⚠️ Recovery email challenge detected")
                        return True
                except:
                    continue
            
            # Check for 2FA challenge
            twofa_selectors = [
                (By.NAME, "smsUserPin"),
                (By.XPATH, "//input[contains(@name, 'Pin')]"),
                (By.XPATH, "//div[contains(text(), '2-Step Verification')]")
            ]
            
            for selector_type, selector_value in twofa_selectors:
                try:
                    if self.driver.find_elements(selector_type, selector_value):
                        logger.warning("⚠️ 2FA challenge detected")
                        return True
                except:
                    continue
            
            # Check for phone verification
            phone_selectors = [
                (By.XPATH, "//div[contains(text(), 'phone')]"),
                (By.XPATH, "//div[contains(text(), 'Phone')]")
            ]
            
            for selector_type, selector_value in phone_selectors:
                try:
                    if self.driver.find_elements(selector_type, selector_value):
                        logger.warning("⚠️ Phone verification challenge detected")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking login challenges: {e}")
            return False

    def _execute_task(self, task_config):
        """Execute assigned task dengan konfigurasi scenario"""
        task_type = task_config.get('type', 'browsing')
        
        try:
            logger.info(f"Executing {task_type} task for {self.device_id}")
            
            if task_type == 'search_engine':
                self._execute_search_task(task_config)
            elif task_type == 'enhanced_search':
                self._execute_enhanced_search_task(task_config)
            elif task_type == 'youtube':
                self._execute_youtube_task(task_config)
            elif task_type == 'website_visit':
                self._execute_visit_task(task_config)
            else:
                self._execute_browsing_task(task_config)
                
            logger.info(f"Task {task_type} completed for {self.device_id}")
                
        except Exception as e:
            logger.error(f"Task execution failed for {self.device_id}: {e}")

    def _execute_enhanced_search_task(self, task_config):
        """Execute enhanced search engine simulation with human-like behavior"""
        try:
            engine = task_config.get('engine', 'google')
            keywords = task_config.get('keywords', [])
            target_urls = task_config.get('target_urls', [])
            searches_per_device = task_config.get('searches_per_device', 5)
            min_clicks = task_config.get('min_result_clicks', 2)
            max_clicks = task_config.get('max_result_clicks', 4)
            behavior = task_config.get('behavior', {})
            session_variation = task_config.get('session_variation', {})
            
            # Validasi input
            if not keywords:
                logger.warning(f"No keywords provided for device {self.device_id}")
                keywords = ["technology", "news", "sports", "entertainment"]
            
            logger.info(f"Starting enhanced search task on {engine} with {len(keywords)} keywords")
            
            # Apply session variation
            read_multiplier = session_variation.get('read_time_multiplier', 1.0)
            behavior['min_read_time'] = int(behavior.get('min_read_time', 30) * read_multiplier)
            behavior['max_read_time'] = int(behavior.get('max_read_time', 90) * read_multiplier)
            
            for search_idx in range(searches_per_device):
                if not self.is_active:
                    break
                    
                # Select random keyword
                keyword = random.choice(keywords) if keywords else "latest technology"
                
                try:
                    # Perform search
                    if engine == 'google':
                        self._google_search(keyword)
                    elif engine == 'bing':
                        self._bing_search(keyword)
                    elif engine == 'both':
                        # Alternate between Google and Bing
                        if search_idx % 2 == 0:
                            self._google_search(keyword)
                        else:
                            self._bing_search(keyword)
                    
                    # Random delay to simulate thinking
                    time.sleep(random.uniform(2, 5))
                    
                    # Click search results with enhanced behavior
                    num_clicks = random.randint(min_clicks, max_clicks)
                    self._click_search_results_with_behavior(num_clicks, target_urls, behavior, keyword)
                    
                    # Random delay between searches
                    time.sleep(random.uniform(15, 30))
                    
                except Exception as e:
                    logger.error(f"Search iteration {search_idx + 1} failed: {e}")
                    # Coba refresh page atau back
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except:
                        try:
                            self.driver.get("https://www.google.com")
                            time.sleep(3)
                        except:
                            # Jika masih error, break dari loop
                            break
                    continue
                    
        except Exception as e:
            logger.error(f"Enhanced search task failed: {e}")
            raise

    def _click_search_results_with_behavior(self, num_clicks, target_urls, behavior, keyword):
        """Click search results with human-like behavior patterns"""
        try:
            # Find search result links
            results = self._get_search_results_enhanced()
            if not results:
                logger.warning("No search results found")
                return
            
            # Filter results that match target URLs (if any)
            matched_results = []
            other_results = []
            
            for result in results:
                try:
                    href = result.get_attribute("href")
                    if href:
                        # Check if this matches any target URL
                        is_target = any(target_url in href for target_url in target_urls if target_url)
                        if is_target and target_urls:
                            matched_results.append((result, href, True))
                        else:
                            other_results.append((result, href, False))
                except:
                    continue
            
            # Prioritize target URLs, then mix with random results
            all_results = matched_results[:2]  # Take max 2 target URLs
            random.shuffle(other_results)
            all_results.extend(other_results[:num_clicks])
            
            if len(all_results) > num_clicks:
                all_results = all_results[:num_clicks]
            
            logger.info(f"Selected {len(all_results)} results to click ({len(matched_results)} target matches)")
            
            for idx, (result, href, is_target) in enumerate(all_results):
                if not self.is_active:
                    break
                    
                try:
                    # Scroll to result (natural behavior)
                    self._scroll_to_element_natural(result)
                    time.sleep(random.uniform(1, 3))
                    
                    # Hover before clicking (human-like)
                    self._hover_element(result)
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    # Click the result
                    result.click()
                    time.sleep(random.uniform(3, 5))
                    
                    # Simulate human reading behavior on the page
                    self._simulate_human_reading_behavior(behavior, is_target, idx)
                    
                    # If enabled, simulate Ctrl+F search on page
                    if behavior.get('use_ctrl_f', True):
                        self._simulate_ctrl_f_search(keyword)
                    
                    # If target page, do enhanced activities
                    if is_target or behavior.get('random_navigation', True):
                        self._perform_enhanced_activities(behavior)
                    
                    # Return to search results (or go back naturally)
                    self.driver.back()
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    logger.warning(f"Failed to click/interact with result {idx}: {e}")
                    try:
                        self.driver.back()
                    except:
                        pass
                    
        except Exception as e:
            logger.error(f"Click search results with behavior failed: {e}")

    def _get_search_results_enhanced(self):
        """Get search results with multiple selector strategies"""
        result_selectors = [
            "h3",  # Google results
            ".b_algo h2",  # Bing results
            "a h3",  # Links with h3
            "[data-header-feature]",
            "[role='heading']",
            ".rc .r a",  # Google classic
            ".g .r a"
        ]
        
        all_results = []
        for selector in result_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        # Find the clickable parent/link
                        link = element.find_element(By.XPATH, "./ancestor::a[1]")
                        if link not in all_results:
                            all_results.append(link)
                    except:
                        # Try to click the element itself
                        if element not in all_results:
                            all_results.append(element)
            except:
                continue
        
        # Remove duplicates based on href/text
        unique_results = []
        seen = set()
        for result in all_results:
            try:
                identifier = result.get_attribute("href") or result.text
                if identifier and identifier not in seen:
                    seen.add(identifier)
                    unique_results.append(result)
            except:
                continue
        
        return unique_results

    def _simulate_human_reading_behavior(self, behavior, is_target=False, result_index=0):
        """Simulate human reading patterns"""
        try:
            # Calculate reading time based on behavior pattern
            min_time = behavior.get('min_read_time', 30)
            max_time = behavior.get('max_read_time', 90)
            
            # Adjust time based on result position and type
            if is_target:
                # Spend more time on target pages
                min_time = int(min_time * 1.5)
                max_time = int(max_time * 1.5)
            elif result_index == 0:
                # Spend more time on first result
                min_time = int(min_time * 1.2)
                max_time = int(max_time * 1.2)
            
            read_time = random.randint(min_time, max_time)
            scroll_speed = behavior.get('scroll_speed', 'medium')
            
            logger.info(f"Simulating {read_time}s reading with {scroll_speed} scroll speed")
            
            # Adjust scroll parameters based on speed
            if scroll_speed == 'slow':
                scrolls = random.randint(8, 15)
                scroll_delay = random.uniform(2, 4)
                scroll_amount = random.randint(300, 600)
            elif scroll_speed == 'fast':
                scrolls = random.randint(3, 6)
                scroll_delay = random.uniform(0.5, 1.5)
                scroll_amount = random.randint(800, 1200)
            else:  # medium
                scrolls = random.randint(5, 10)
                scroll_delay = random.uniform(1, 2.5)
                scroll_amount = random.randint(500, 800)
            
            # Perform reading simulation
            start_time = time.time()
            scrolls_done = 0
            
            while time.time() - start_time < read_time and scrolls_done < scrolls:
                # Random scroll pattern
                scroll_direction = random.choice(['down', 'up', 'down', 'down'])  # Mostly down
                if scroll_direction == 'down':
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                else:
                    self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount//2});")
                
                # Random micro-pauses during scrolling
                micro_pause = random.uniform(0.3, 1.2)
                time.sleep(micro_pause)
                
                # Occasionally stop scrolling to "read"
                if random.random() < 0.3:  # 30% chance
                    read_pause = random.uniform(3, 8)
                    time.sleep(read_pause)
                
                scrolls_done += 1
                time.sleep(scroll_delay)
            
            # Final reading pause
            if random.random() < 0.7:  # 70% chance
                final_pause = random.uniform(5, 15)
                time.sleep(final_pause)
                
        except Exception as e:
            logger.warning(f"Reading behavior simulation failed: {e}")

    def _simulate_ctrl_f_search(self, keyword):
        """Simulate Ctrl+F search behavior on page"""
        try:
            # Extract main words from keyword for search
            words = keyword.lower().split()
            if not words:
                return
                
            # Pick 1-2 words to "search" for
            search_words = random.sample(words, min(2, len(words)))
            
            for word in search_words:
                if len(word) < 3:  # Skip very short words
                    continue
                    
                # Simulate looking for word (random scroll to simulate finding)
                logger.info(f"Simulating search for: {word}")
                
                # Scroll randomly as if searching
                for _ in range(random.randint(2, 4)):
                    scroll_pos = random.randint(100, 1000)
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                    time.sleep(random.uniform(1, 2))
                    
                # Pause as if found something
                if random.random() < 0.4:  # 40% chance of "finding" it
                    time.sleep(random.uniform(3, 7))
                    
        except Exception as e:
            logger.warning(f"Ctrl+F simulation failed: {e}")

    def _perform_enhanced_activities(self, behavior):
        """Perform enhanced activities on page"""
        try:
            click_pattern = behavior.get('click_pattern', 'normal')
            return_home = behavior.get('return_to_home', False)
            
            # Get all internal links on page
            internal_links = self._get_internal_links()
            
            if not internal_links:
                return
                
            # Determine number of clicks based on pattern
            if click_pattern == 'explorer':
                clicks = random.randint(3, 6)
            elif click_pattern == 'researcher':
                clicks = random.randint(2, 4)
            else:  # normal
                clicks = random.randint(1, 3)
            
            # Select random links to click
            selected_links = random.sample(internal_links, min(clicks, len(internal_links)))
            
            logger.info(f"Performing {clicks} enhanced activities with {click_pattern} pattern")
            
            for i, link in enumerate(selected_links):
                if not self.is_active:
                    break
                    
                try:
                    # Scroll to link naturally
                    self._scroll_to_element_natural(link)
                    time.sleep(random.uniform(1, 2))
                    
                    # Hover and click
                    self._hover_element(link)
                    time.sleep(random.uniform(0.5, 1))
                    link.click()
                    time.sleep(random.uniform(3, 5))
                    
                    # Read the new page
                    self._simulate_human_reading_behavior(behavior, False, i)
                    
                    # If this isn't the last click, maybe go back
                    if i < len(selected_links) - 1 and random.random() < 0.7:
                        self.driver.back()
                        time.sleep(random.uniform(2, 4))
                        # Need to re-find links after back
                        internal_links = self._get_internal_links()
                        
                except Exception as e:
                    logger.warning(f"Enhanced activity {i} failed: {e}")
                    try:
                        self.driver.back()
                    except:
                        pass
            
            # Return to home if enabled
            if return_home and random.random() < 0.5:  # 50% chance
                self._click_home_menu()
                
        except Exception as e:
            logger.error(f"Enhanced activities failed: {e}")

    def _get_internal_links(self):
        """Get internal links from current page"""
        try:
            current_url = self.driver.current_url
            domain = current_url.split('/')[2] if '//' in current_url else current_url.split('/')[0]
            
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            internal_links = []
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and domain in href and href != current_url:
                        # Check if link is likely clickable
                        if link.is_displayed() and link.is_enabled():
                            text = link.text.strip()
                            if text and len(text) > 2:  # Filter empty/very short text
                                internal_links.append(link)
                except:
                    continue
            
            return internal_links
            
        except Exception as e:
            logger.warning(f"Failed to get internal links: {e}")
            return []

    def _click_home_menu(self):
        """Try to click home menu/logo"""
        try:
            home_selectors = [
                "a[href='/']",
                ".logo a",
                "[aria-label='Home']",
                "[title='Home']",
                "header a:first-child",
                "nav a:first-child"
            ]
            
            for selector in home_selectors:
                try:
                    home_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in home_elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(random.uniform(2, 4))
                            return True
                except:
                    continue
                    
            return False
        except Exception as e:
            logger.warning(f"Failed to click home menu: {e}")
            return False

    def _scroll_to_element_natural(self, element):
        """Scroll to element with natural human-like movement"""
        try:
            # Get element position
            element_y = element.location['y']
            current_y = self.driver.execute_script("return window.pageYOffset;")
            
            # Calculate distance
            distance = element_y - current_y
            
            # Scroll in increments with varying speed (human-like)
            scroll_increment = random.randint(300, 600)
            steps = max(1, abs(distance) // scroll_increment)
            
            for step in range(steps):
                # Vary scroll amount slightly
                current_increment = scroll_increment + random.randint(-100, 100)
                if distance > 0:
                    self.driver.execute_script(f"window.scrollBy(0, {current_increment});")
                else:
                    self.driver.execute_script(f"window.scrollBy(0, {-current_increment});")
                
                # Random micro-pause
                time.sleep(random.uniform(0.1, 0.3))
                
            # Final small adjustment
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(-50, 50)});")
            
        except Exception as e:
            logger.warning(f"Natural scroll failed: {e}")
            # Fallback to standard scroll
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", element)
            except:
                pass

    def _hover_element(self, element):
        """Hover over element (simulate mouse movement)"""
        try:
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            
            # Small random movement after hover
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            if offset_x != 0 or offset_y != 0:
                actions.move_by_offset(offset_x, offset_y).perform()
                
        except Exception as e:
            logger.warning(f"Hover failed: {e}")

    # Existing methods (keep these from original file)
    def _execute_search_task(self, task_config):
        """Execute search engine simulation task"""
        try:
            engine = task_config.get('engine', 'google')
            keywords = task_config.get('keywords', [])
            searches_per_device = task_config.get('searches_per_device', 10)
            min_clicks = task_config.get('min_result_clicks', 2)
            max_clicks = task_config.get('max_result_clicks', 5)
            
            logger.info(f"Starting search task on {engine} with {len(keywords)} keywords")
            
            for search_idx in range(searches_per_device):
                if not self.is_active:
                    break
                    
                # Select random keyword
                keyword = random.choice(keywords) if keywords else "test search"
                
                # Perform search
                if engine == 'google':
                    self._google_search(keyword)
                elif engine == 'bing':
                    self._bing_search(keyword)
                elif engine == 'both':
                    # Alternate between Google and Bing
                    if search_idx % 2 == 0:
                        self._google_search(keyword)
                    else:
                        self._bing_search(keyword)
                
                # Random clicks on search results
                num_clicks = random.randint(min_clicks, max_clicks)
                self._click_search_results(num_clicks)
                
                # Random delay between searches
                time.sleep(random.uniform(10, 30))
                
        except Exception as e:
            logger.error(f"Search task failed: {e}")
            raise

    def _execute_youtube_task(self, task_config):
        """Execute YouTube view farming task"""
        try:
            video_urls = task_config.get('video_urls', [])
            if isinstance(video_urls, str):
                video_urls = [video_urls]
                
            watch_time_min = task_config.get('watch_time_min', 60)
            watch_time_max = task_config.get('watch_time_max', 180)
            auto_like = task_config.get('auto_like', False)
            auto_subscribe = task_config.get('auto_subscribe', False)
            
            logger.info(f"Starting YouTube task with {len(video_urls)} videos")
            
            for video_url in video_urls:
                if not self.is_active:
                    break
                    
                try:
                    # Navigate to video
                    self.driver.get(video_url)
                    time.sleep(5)
                    
                    # Play video
                    self._click_play_button()
                    
                    # Watch for random duration
                    watch_time = random.randint(watch_time_min, watch_time_max)
                    logger.info(f"Watching video for {watch_time} seconds")
                    
                    # Simulate watching with occasional interactions
                    start_time = time.time()
                    while time.time() - start_time < watch_time and self.is_active:
                        # Random scroll
                        if random.random() < 0.3:  # 30% chance
                            self._random_scroll()
                        
                        # Random pause/play
                        if random.random() < 0.1:  # 10% chance
                            self._toggle_play_pause()
                            
                        time.sleep(10)  # Check every 10 seconds
                    
                    # Auto like if enabled
                    if auto_like:
                        self._like_video()
                    
                    # Auto subscribe if enabled
                    if auto_subscribe:
                        self._subscribe_channel()
                        
                    # Random delay before next video
                    time.sleep(random.uniform(5, 15))
                    
                except Exception as e:
                    logger.warning(f"Failed to process video {video_url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"YouTube task failed: {e}")
            raise

    def _execute_visit_task(self, task_config):
        """Execute website traffic generation task"""
        try:
            urls = task_config.get('urls', [])
            if isinstance(urls, str):
                urls = [urls]
                
            visit_duration = task_config.get('visit_duration', 120)
            pages_per_session = task_config.get('pages_per_session', 5)
            random_click = task_config.get('random_click', True)
            random_scroll = task_config.get('random_scroll', True)
            
            logger.info(f"Starting visit task with {len(urls)} URLs")
            
            for i in range(min(pages_per_session, len(urls))):
                if not self.is_active:
                    break
                    
                url = urls[i % len(urls)]  # Cycle through URLs
                
                try:
                    # Visit page
                    self.driver.get(url)
                    time.sleep(3)
                    
                    # Random scroll during visit
                    if random_scroll:
                        scroll_duration = min(visit_duration // len(urls), 30)
                        self._simulate_browsing(scroll_duration, random_click)
                    else:
                        time.sleep(5)  # Minimum stay
                        
                    # Random click if enabled
                    if random_click and random.random() < 0.7:  # 70% chance
                        self._click_random_link()
                        
                except Exception as e:
                    logger.warning(f"Failed to visit {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Visit task failed: {e}")
            raise

    def _execute_browsing_task(self, task_config):
        """Execute general browsing task"""
        try:
            logger.info("Starting general browsing task")
            
            # Default browsing behavior
            duration = task_config.get('duration', 60)
            self._simulate_browsing(duration, True)
            
        except Exception as e:
            logger.error(f"Browsing task failed: {e}")
            raise

    def _google_search(self, keyword):
        """Perform Google search"""
        try:
            self.driver.get("https://www.google.com")
            time.sleep(2)
            
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "q"))
            )
            
            # Type search query
            search_box.clear()
            for char in keyword:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            search_box.submit()
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"Google search failed: {e}")

    def _bing_search(self, keyword):
        """Perform Bing search"""
        try:
            self.driver.get("https://www.bing.com")
            time.sleep(2)
            
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "q"))
            )
            
            # Type search query
            search_box.clear()
            for char in keyword:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            search_box.submit()
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")

    def _click_search_results(self, num_clicks):
        """Click on search results"""
        try:
            # Find search result links
            results = self.driver.find_elements(By.CSS_SELECTOR, "h3")
            clickable_results = []
            
            for result in results:
                try:
                    link = result.find_element(By.XPATH, "./..")
                    if link.get_attribute("href"):
                        clickable_results.append(link)
                except:
                    continue
            
            # Click random results
            for _ in range(min(num_clicks, len(clickable_results))):
                if not self.is_active:
                    break
                    
                result = random.choice(clickable_results)
                try:
                    result.click()
                    time.sleep(random.uniform(5, 15))  # Stay on page
                    self.driver.back()  # Go back to search results
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Failed to click search result: {e}")
                    
        except Exception as e:
            logger.warning(f"Click search results failed: {e}")

    def _click_play_button(self):
        """Click YouTube play button"""
        try:
            # Try different selectors for play button
            selectors = [
                "button.ytp-play-button",
                ".ytp-large-play-button",
                "button[aria-label*='Play']"
            ]
            
            for selector in selectors:
                try:
                    play_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    play_button.click()
                    time.sleep(2)
                    return True
                except:
                    continue
                    
            return False
        except Exception as e:
            logger.warning(f"Click play button failed: {e}")
            return False

    def _random_scroll(self):
        """Perform random scrolling"""
        try:
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_pos = random.randint(100, scroll_height - 500)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(random.uniform(1, 3))
        except:
            pass

    def _toggle_play_pause(self):
        """Toggle YouTube play/pause"""
        try:
            play_button = self.driver.find_element(By.CSS_SELECTOR, "button.ytp-play-button")
            play_button.click()
            time.sleep(1)
        except:
            pass

    def _like_video(self):
        """Like YouTube video"""
        try:
            like_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='like this video']")
            like_button.click()
            time.sleep(1)
        except:
            pass

    def _subscribe_channel(self):
        """Subscribe to YouTube channel"""
        try:
            subscribe_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Subscribe']")
            if "subscribed" not in subscribe_button.get_attribute("innerHTML"):
                subscribe_button.click()
                time.sleep(1)
        except:
            pass

    def _simulate_browsing(self, duration, random_click=False):
        """Simulate natural browsing behavior"""
        start_time = time.time()
        
        while time.time() - start_time < duration and self.is_active:
            # Random scroll
            self._random_scroll()
            
            # Random click if enabled
            if random_click and random.random() < 0.2:  # 20% chance
                self._click_random_link()
                time.sleep(random.uniform(5, 15))
                self.driver.back()
                time.sleep(2)
            
            time.sleep(random.uniform(3, 8))

    def _click_random_link(self):
        """Click random link on page"""
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            valid_links = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and "http" in href and "youtube.com" not in href:
                        valid_links.append(link)
                except:
                    continue
            
            if valid_links:
                link = random.choice(valid_links)
                link.click()
                return True
                
        except Exception as e:
            logger.warning(f"Click random link failed: {e}")
            
        return False

    def restart_session(self):
        """Restart device session"""
        try:
            self.stop_session()
            time.sleep(2)
            return self.start_session(self.current_profile, self.current_task)
        except Exception as e:
            logger.error(f"Failed to restart session for {self.device_id}: {e}")
            return False

    def is_running(self):
        """Check if device is running"""
        if not self.is_active or not self.driver:
            return False
        
        # Check session duration
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
            if session_duration > self.capabilities['max_session_duration']:
                logger.info(f"Session duration exceeded for {self.device_id}, stopping")
                self.stop_session()
                return False
        
        return self.is_active

    def is_healthy(self):
        """Check if device session is healthy"""
        try:
            # Check if driver is still responsive
            self.driver.current_url
            return True
        except:
            logger.warning(f"Device {self.device_id} is not healthy")
            return False

    def stop_session(self):
        """Stop device session dan save state"""
        try:
            # Save session before quitting
            if self.google_login_success and self.capabilities['save_session']:
                self._save_session_cookies()
            
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.warning(f"Error during session stop for {self.device_id}: {e}")
        
        self.driver = None
        self.is_active = False
        self.session_start_time = None
        logger.info(f"Device {self.device_id} session stopped")

    def get_status(self):
        """Get device status"""
        session_duration = 0
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
        
        return {
            'device_id': self.device_id,
            'is_active': self.is_active,
            'google_login_success': self.google_login_success,
            'current_task': self.current_task,
            'session_duration': session_duration,
            'browser_type': 'chrome'
        }