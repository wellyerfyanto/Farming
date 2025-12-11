import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class GoogleLoginManager:
    def __init__(self):
        self.accounts = []
        self.login_attempts = {}
    
    def add_account(self, email, password, device_id):
        """Add Google account for specific device"""
        self.accounts.append({
            'email': email,
            'password': password,
            'device_id': device_id
        })
    
    def get_account_for_device(self, device_id):
        """Get Google account for specific device"""
        for account in self.accounts:
            if account['device_id'] == device_id:
                return account
        return None
    
    def verify_login_success(self, driver):
        """Verify if Google login was successful"""
        try:
            # Check multiple indicators of successful login
            indicators = [
                "myaccount.google.com" in driver.current_url,
                "mail.google.com" in driver.current_url,
                driver.find_elements(By.CSS_SELECTOR, "[aria-label*='Google Account']"),
                driver.find_elements(By.CSS_SELECTOR, "[data-identifier*='@gmail.com']")
            ]
            
            return any(indicators)
        except:
            return False
    
    def handle_login_challenges(self, driver):
        """Handle potential login challenges like 2FA, recovery email, etc."""
        try:
            # Check for recovery email challenge
            recovery_elements = driver.find_elements(By.NAME, "knowledgePreregisteredEmailResponse")
            if recovery_elements:
                logger.warning("⚠️ Recovery email challenge detected - manual intervention needed")
                return False
            
            # Check for 2FA challenge
            twofa_elements = driver.find_elements(By.NAME, "smsUserPin")
            if twofa_elements:
                logger.warning("⚠️ 2FA challenge detected - manual intervention needed")
                return False
            
            return True
        except:
            return True
