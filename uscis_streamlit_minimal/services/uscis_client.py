"""
USCIS Torch API Client Service
Based on official USCIS Developer Portal documentation
https://developer.uscis.gov

Available APIs:
1. Case Status API (v1.0.0) - Check case status by receipt number
2. FOIA Request and Status API (v1.2.0) - Create and check FOIA requests

Authentication: OAuth 2.0 Client Credentials
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class USCISEnvironment(Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class TokenInfo:
    """OAuth 2.0 Access Token Information"""
    access_token: str
    token_type: str
    expires_in: int
    issued_at: datetime
    api_products: List[str] = field(default_factory=list)
    
    @property
    def expires_at(self) -> datetime:
        return self.issued_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        # Add 60 second buffer before expiration
        return datetime.now() >= (self.expires_at - timedelta(seconds=60))


@dataclass
class CaseStatus:
    """Case Status API Response"""
    receipt_number: str
    form_type: str
    submitted_date: Optional[str]
    modified_date: Optional[str]
    status_text_en: str
    status_desc_en: str
    status_text_es: Optional[str] = None
    status_desc_es: Optional[str] = None
    history: Optional[List[Dict]] = None
    raw_response: Dict = field(default_factory=dict)


@dataclass
class FOIARequest:
    """FOIA Request Data"""
    request_number: Optional[str] = None
    status: Optional[str] = None
    created_date: Optional[str] = None
    raw_response: Dict = field(default_factory=dict)


class USCISApiError(Exception):
    """Custom exception for USCIS API errors"""
    def __init__(self, message: str, code: str = None, status: int = None, trace_id: str = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.trace_id = trace_id


class USCISApiClient:
    """
    USCIS Torch API Client
    
    Official documentation: https://developer.uscis.gov
    
    Usage:
        client = USCISApiClient(client_id="xxx", client_secret="xxx")
        client.authenticate()
        status = client.get_case_status("EAC9999103402")
    """
    
    # API Endpoints from official documentation
    ENDPOINTS = {
        USCISEnvironment.SANDBOX: {
            "base_url": "https://api-int.uscis.gov",
            "oauth_url": "https://api-int.uscis.gov/oauth/accesstoken",
        },
        USCISEnvironment.PRODUCTION: {
            "base_url": "https://api.uscis.gov",
            "oauth_url": "https://api.uscis.gov/oauth/accesstoken",
        }
    }
    
    # Sandbox test receipt numbers from USCIS documentation
    SANDBOX_TEST_RECEIPTS = [
        "EAC9999103402",  # I-130 - Case Approval Was Affirmed
        "WAC9999103402",  # Test receipt
        "LIN9999103402",  # Test receipt
    ]
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        environment: USCISEnvironment = USCISEnvironment.SANDBOX
    ):
        """
        Initialize USCIS API Client
        
        Args:
            client_id: OAuth Client ID from Developer Portal
            client_secret: OAuth Client Secret from Developer Portal
            environment: SANDBOX or PRODUCTION
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self.token_info: Optional[TokenInfo] = None
        
        self._endpoints = self.ENDPOINTS[environment]
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    @property
    def base_url(self) -> str:
        return self._endpoints["base_url"]
    
    @property
    def oauth_url(self) -> str:
        return self._endpoints["oauth_url"]
    
    @property
    def is_authenticated(self) -> bool:
        return self.token_info is not None and not self.token_info.is_expired
    
    def authenticate(self) -> TokenInfo:
        """
        Authenticate using OAuth 2.0 Client Credentials Grant
        
        From USCIS documentation:
        curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
             -d "grant_type=client_credentials&client_id=xxx&client_secret=xxx" \
             https://api-int.uscis.gov/oauth/accesstoken
        
        Returns:
            TokenInfo object with access token details
        """
        logger.info(f"Authenticating with USCIS {self.environment.value} environment")
        
        try:
            response = requests.post(
                self.oauth_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                timeout=30
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise USCISApiError(
                    message=f"Authentication failed: {response.status_code}",
                    code=error_data.get("error", "AUTH_ERROR"),
                    status=response.status_code
                )
            
            data = response.json()
            
            # Parse API products list
            api_products = data.get("api_product_list_json", [])
            if isinstance(api_products, str):
                api_products = [api_products]
            
            self.token_info = TokenInfo(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=int(data.get("expires_in", 1799)),
                issued_at=datetime.now(),
                api_products=api_products
            )
            
            # Update session with bearer token
            self._session.headers.update({
                "Authorization": f"Bearer {self.token_info.access_token}"
            })
            
            logger.info(f"Authentication successful. Token expires in {self.token_info.expires_in}s")
            logger.info(f"API Products: {api_products}")
            
            return self.token_info
            
        except requests.RequestException as e:
            raise USCISApiError(f"Network error during authentication: {str(e)}")
    
    def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.is_authenticated:
            self.authenticate()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None
    ) -> Dict:
        """Make authenticated API request"""
        self._ensure_authenticated()
        
        url = f"{self.base_url}{endpoint}"
        
        logger.info(f"Making {method} request to: {url}")
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            # Handle errors
            if response.status_code >= 400:
                # Try to parse error response
                error_body = response.text
                error_data = {}
                try:
                    error_data = response.json() if response.text else {}
                except:
                    pass
                
                errors = error_data.get("errors", [{}])
                first_error = errors[0] if errors else {}
                
                # Build detailed error message
                error_msg = first_error.get("message", "")
                if not error_msg:
                    if response.status_code == 503:
                        error_msg = f"USCIS API unavailable (503). URL: {url}. Response: {error_body[:200] if error_body else 'empty'}"
                    elif response.status_code == 401:
                        error_msg = "Authentication failed - check your credentials"
                    elif response.status_code == 404:
                        error_msg = f"Endpoint not found: {url}"
                    else:
                        error_msg = f"API error {response.status_code}: {error_body[:200] if error_body else 'no response body'}"
                
                raise USCISApiError(
                    message=error_msg,
                    code=first_error.get("code", f"HTTP_{response.status_code}"),
                    status=response.status_code,
                    trace_id=first_error.get("traceId")
                )
            
            return response.json()
            
        except requests.RequestException as e:
            raise USCISApiError(f"Network error: {str(e)}")
    
    # ==================== CASE STATUS API ====================
    
    def get_case_status(self, receipt_number: str) -> CaseStatus:
        """
        Get case status by receipt number
        
        Endpoint: GET /case-status/{receipt_number}
        
        From USCIS documentation:
        curl -X GET -H "Authorization: Bearer xxx" \
             https://api-int.uscis.gov/case-status/EAC9999103402
        
        Args:
            receipt_number: USCIS receipt number (e.g., EAC9999103402)
        
        Returns:
            CaseStatus object with case details
        """
        logger.info(f"Getting case status for: {receipt_number}")
        
        data = self._make_request("GET", f"/case-status/{receipt_number}")
        
        case_data = data.get("case_status", {})
        
        return CaseStatus(
            receipt_number=case_data.get("receiptNumber", receipt_number),
            form_type=case_data.get("formType", ""),
            submitted_date=case_data.get("submittedDate"),
            modified_date=case_data.get("modifiedDate"),
            status_text_en=case_data.get("current_case_status_text_en", ""),
            status_desc_en=case_data.get("current_case_status_desc_en", ""),
            status_text_es=case_data.get("current_case_status_text_es"),
            status_desc_es=case_data.get("current_case_status_desc_es"),
            history=case_data.get("hist_case_status"),
            raw_response=data
        )
    
    def get_case_status_batch(self, receipt_numbers: List[str]) -> Dict[str, CaseStatus]:
        """
        Get status for multiple cases
        
        Args:
            receipt_numbers: List of receipt numbers
        
        Returns:
            Dictionary mapping receipt numbers to CaseStatus objects
        """
        results = {}
        errors = {}
        
        for receipt in receipt_numbers:
            try:
                results[receipt] = self.get_case_status(receipt)
            except USCISApiError as e:
                errors[receipt] = str(e)
                logger.error(f"Error getting status for {receipt}: {e}")
        
        if errors:
            logger.warning(f"Batch had {len(errors)} errors out of {len(receipt_numbers)} requests")
        
        return results
    
    # ==================== FOIA API ====================
    
    def create_foia_request(
        self,
        subject_first_name: str,
        subject_last_name: str,
        subject_dob: str,
        subject_country_of_birth: str,
        a_number: Optional[str] = None,
        requester_email: Optional[str] = None,
        request_type: str = "ALIEN_FILE",
        **additional_fields
    ) -> FOIARequest:
        """
        Create a new FOIA/Privacy Act request
        
        Endpoint: POST /foia/request
        
        Args:
            subject_first_name: Subject's first name
            subject_last_name: Subject's last name
            subject_dob: Date of birth (MM-DD-YYYY)
            subject_country_of_birth: Country of birth
            a_number: Alien number (optional)
            requester_email: Email for notifications
            request_type: Type of request (default: ALIEN_FILE)
        
        Returns:
            FOIARequest object with request number
        """
        logger.info(f"Creating FOIA request for: {subject_first_name} {subject_last_name}")
        
        payload = {
            "subjectFirstName": subject_first_name,
            "subjectLastName": subject_last_name,
            "subjectDateOfBirth": subject_dob,
            "subjectCountryOfBirth": subject_country_of_birth,
            "requestType": request_type,
        }
        
        if a_number:
            payload["alienNumber"] = a_number
        if requester_email:
            payload["requesterEmail"] = requester_email
        
        payload.update(additional_fields)
        
        data = self._make_request("POST", "/foia/request", json_data=payload)
        
        return FOIARequest(
            request_number=data.get("requestNumber"),
            status=data.get("status"),
            created_date=data.get("createdDate"),
            raw_response=data
        )
    
    def get_foia_status(self, request_number: str) -> FOIARequest:
        """
        Get status of a FOIA request
        
        Endpoint: GET /foia/status/{request_number}
        
        Args:
            request_number: FOIA request number
        
        Returns:
            FOIARequest object with status details
        """
        logger.info(f"Getting FOIA status for: {request_number}")
        
        data = self._make_request("GET", f"/foia/status/{request_number}")
        
        return FOIARequest(
            request_number=request_number,
            status=data.get("status"),
            raw_response=data
        )
    
    # ==================== UTILITY METHODS ====================
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get current token information"""
        if not self.token_info:
            return {"authenticated": False}
        
        return {
            "authenticated": True,
            "token_type": self.token_info.token_type,
            "expires_in": self.token_info.expires_in,
            "issued_at": self.token_info.issued_at.isoformat(),
            "expires_at": self.token_info.expires_at.isoformat(),
            "is_expired": self.token_info.is_expired,
            "seconds_remaining": max(0, int((self.token_info.expires_at - datetime.now()).total_seconds())),
            "api_products": self.token_info.api_products,
            "environment": self.environment.value
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection with sandbox test receipt
        
        Returns:
            Connection test results
        """
        results = {
            "environment": self.environment.value,
            "timestamp": datetime.now().isoformat(),
            "authentication": {"success": False},
            "case_status_api": {"success": False},
        }
        
        # Test authentication
        try:
            self.authenticate()
            results["authentication"] = {
                "success": True,
                "token_info": self.get_token_info()
            }
        except USCISApiError as e:
            results["authentication"] = {
                "success": False,
                "error": str(e),
                "code": e.code
            }
            return results
        
        # Test Case Status API
        if self.environment == USCISEnvironment.SANDBOX:
            test_receipt = self.SANDBOX_TEST_RECEIPTS[0]
            try:
                status = self.get_case_status(test_receipt)
                results["case_status_api"] = {
                    "success": True,
                    "test_receipt": test_receipt,
                    "form_type": status.form_type,
                    "status": status.status_text_en
                }
            except USCISApiError as e:
                results["case_status_api"] = {
                    "success": False,
                    "test_receipt": test_receipt,
                    "error": str(e),
                    "code": e.code
                }
        
        return results
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about API configuration"""
        return {
            "environment": self.environment.value,
            "base_url": self.base_url,
            "oauth_url": self.oauth_url,
            "case_status_endpoint": f"{self.base_url}/case-status/{{receipt_number}}",
            "foia_request_endpoint": f"{self.base_url}/foia/request",
            "foia_status_endpoint": f"{self.base_url}/foia/status/{{request_number}}",
            "is_authenticated": self.is_authenticated,
            "token_info": self.get_token_info() if self.token_info else None,
            "sandbox_test_receipts": self.SANDBOX_TEST_RECEIPTS
        }


# Convenience function
def create_client(
    client_id: str,
    client_secret: str,
    sandbox: bool = True
) -> USCISApiClient:
    """
    Create a USCIS API client
    
    Args:
        client_id: OAuth Client ID
        client_secret: OAuth Client Secret
        sandbox: Use sandbox environment (default: True)
    
    Returns:
        Authenticated USCISApiClient
    """
    env = USCISEnvironment.SANDBOX if sandbox else USCISEnvironment.PRODUCTION
    client = USCISApiClient(client_id, client_secret, env)
    client.authenticate()
    return client
