import os
import json
import time
import logging
import pickle
import base64

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, profiles_dir="profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)
    
    def create_profile(self, device_id):
        """Create browser profile for device"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        os.makedirs(profile_path, exist_ok=True)
        
        profile = {
            'profile_path': profile_path,
            'device_id': device_id,
            'created_at': time.time(),
            'google_logged_in': False,
            'google_email': None,
            'last_login': None
        }
        
        # Save profile info
        self.save_profile_info(device_id, profile)
        
        logger.info(f"👤 Created profile for {device_id}")
        return profile
    
    def save_profile_info(self, device_id, profile_info):
        """Save profile information"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        info_file = os.path.join(profile_path, 'profile_info.json')
        
        with open(info_file, 'w') as f:
            json.dump(profile_info, f, indent=2)
    
    def get_profile_info(self, device_id):
        """Get profile information"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        info_file = os.path.join(profile_path, 'profile_info.json')
        
        try:
            with open(info_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def save_cookies(self, device_id, cookies):
        """Save browser cookies for session persistence"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        cookies_file = os.path.join(profile_path, 'cookies.pkl')
        
        try:
            with open(cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"💾 Saved cookies for {device_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save cookies for {device_id}: {e}")
    
    def load_cookies(self, device_id):
        """Load browser cookies for session persistence"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        cookies_file = os.path.join(profile_path, 'cookies.pkl')
        
        try:
            with open(cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            logger.info(f"📂 Loaded cookies for {device_id}")
            return cookies
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load cookies for {device_id}: {e}")
            return None
    
    def mark_google_logged_in(self, device_id, email):
        """Mark profile as Google logged in"""
        profile_info = self.get_profile_info(device_id) or {}
        profile_info.update({
            'google_logged_in': True,
            'google_email': email,
            'last_login': time.time()
        })
        
        self.save_profile_info(device_id, profile_info)
        logger.info(f"✅ Marked {device_id} as Google logged in: {email}")
    
    def is_google_logged_in(self, device_id):
        """Check if profile has Google login"""
        profile_info = self.get_profile_info(device_id)
        if profile_info and profile_info.get('google_logged_in'):
            # Check if login is not too old (e.g., within 7 days)
            last_login = profile_info.get('last_login', 0)
            if time.time() - last_login < 7 * 24 * 3600:  # 7 days
                return True
        return False
    
    def export_profile(self, device_id):
        """Export profile for backup"""
        profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
        
        if not os.path.exists(profile_path):
            return None
        
        import zipfile
        import tempfile
        
        try:
            # Create temporary zip file
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, f"profile_{device_id}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(profile_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, profile_path)
                        zipf.write(file_path, arcname)
            
            # Read zip file as base64
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            profile_info = self.get_profile_info(device_id)
            return {
                'device_id': device_id,
                'data': base64.b64encode(zip_data).decode('utf-8'),
                'google_email': profile_info.get('google_email') if profile_info else None,
                'last_login': profile_info.get('last_login') if profile_info else None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to export profile {device_id}: {e}")
            return None
    
    def import_profile(self, device_id, profile_data):
        """Import profile from backup"""
        try:
            profile_path = os.path.join(self.profiles_dir, f"profile_{device_id}")
            
            # Decode base64 data
            zip_data = base64.b64decode(profile_data)
            
            # Save to temporary file
            import tempfile
            import zipfile
            
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, f"profile_{device_id}.zip")
            
            with open(zip_path, 'wb') as f:
                f.write(zip_data)
            
            # Extract to profile path
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(profile_path)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"📥 Imported profile for {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to import profile {device_id}: {e}")
            return False
    
    def get_all_profiles(self):
        """Get all profiles information"""
        profiles = {}
        for item in os.listdir(self.profiles_dir):
            if item.startswith('profile_'):
                device_id = item.replace('profile_', '')
                profile_info = self.get_profile_info(device_id)
                if profile_info:
                    profiles[device_id] = profile_info
        return profiles
