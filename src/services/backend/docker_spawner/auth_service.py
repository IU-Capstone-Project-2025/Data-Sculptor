import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


class AuthService:
    """Service for validating OAuth tokens."""
    
    def __init__(self, auth_service_url: str):
        self.auth_service_url = auth_service_url.rstrip('/')
    
    async def validate_token(self, oauth_token: str) -> bool:
        """
        Validate an OAuth token.
        
        Args:
            oauth_token: The OAuth token to validate
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Make request to auth service to validate token
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {oauth_token}",
                    "Content-Type": "application/json"
                }
                
                # You can customize this endpoint based on your auth service
                url = f"{self.auth_service_url}/validate-token"
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                ***REMOVED*** data.get("valid", False)
                    else:
                        logger.warning(f"Auth service returned status {response.status}")
                ***REMOVED*** False
                        
        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to auth service: {str(e)}")
    ***REMOVED*** False
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
    ***REMOVED*** False
    
    async def get_user_info(self, oauth_token: str) -> Optional[dict]:
        """
        Get user information from OAuth token.
        
        Args:
            oauth_token: The OAuth token
        
        Returns:
            User information dict or None if token is invalid
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {oauth_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.auth_service_url}/user-info"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                ***REMOVED*** await response.json()
                    else:
                        logger.warning(f"Auth service returned status {response.status}")
                ***REMOVED*** None
                        
        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to auth service: {str(e)}")
    ***REMOVED*** None
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
    ***REMOVED*** None
    
    async def check_case_access(self, oauth_token: str, case_id: str) -> bool:
        """
        Check if user has access to a specific case.
        
        Args:
            oauth_token: The OAuth token
            case_id: The case ID to check access for
        
        Returns:
            True if user has access to the case, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {oauth_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.auth_service_url}/check-case-access"
                payload = {"case_id": case_id}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                ***REMOVED*** data.get("has_access", False)
                    else:
                        logger.warning(f"Auth service returned status {response.status}")
                ***REMOVED*** False
                        
        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to auth service: {str(e)}")
    ***REMOVED*** False
        except Exception as e:
            logger.error(f"Error checking case access: {str(e)}")
    ***REMOVED*** False 