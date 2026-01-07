"""
USCIS Torch API Testing Console
Interactive Streamlit app for testing USCIS APIs with your actual credentials

Run with: streamlit run app.py
"""

import streamlit as st
import json
import time
from datetime import datetime
from typing import Optional
import sys
import os

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.uscis_client import (
    USCISApiClient, 
    USCISEnvironment, 
    USCISApiError,
    CaseStatus,
    FOIARequest
)

# Page config
st.set_page_config(
    page_title="USCIS API Testing Console",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a365d;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .api-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #cce5ff;
        border: 1px solid #99caff;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .code-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .token-timer {
        font-size: 1.5rem;
        font-weight: bold;
        color: #28a745;
    }
    .token-expired {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'client' not in st.session_state:
    st.session_state.client = None
if 'api_logs' not in st.session_state:
    st.session_state.api_logs = []
if 'credentials_saved' not in st.session_state:
    st.session_state.credentials_saved = False

# Load credentials from Streamlit secrets if available
def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit secrets or return default"""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

# Pre-load credentials from secrets
DEFAULT_CLIENT_ID = get_secret("USCIS_CLIENT_ID", "")
DEFAULT_CLIENT_SECRET = get_secret("USCIS_CLIENT_SECRET", "")
DEFAULT_ENVIRONMENT = get_secret("USCIS_ENVIRONMENT", "sandbox")
CLAUDE_API_KEY = get_secret("CLAUDE_API_KEY", "")


def add_log(action: str, status: str, details: dict = None):
    """Add entry to API log"""
    st.session_state.api_logs.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details or {}
    })
    # Keep last 50 logs
    st.session_state.api_logs = st.session_state.api_logs[:50]


def format_curl(method: str, url: str, headers: dict = None, data: dict = None) -> str:
    """Format a curl command for documentation"""
    cmd = f"curl -X {method}"
    if headers:
        for k, v in headers.items():
            if k.lower() == "authorization":
                v = "Bearer YOUR_ACCESS_TOKEN"
            cmd += f' \\\n  -H "{k}: {v}"'
    if data:
        cmd += f' \\\n  -d \'{json.dumps(data)}\''
    cmd += f' \\\n  {url}'
    return cmd


# ==================== SIDEBAR ====================

with st.sidebar:
    st.markdown("### 🔐 Connection Status")
    
    # Auto-connect from secrets on startup
    if not st.session_state.client and DEFAULT_CLIENT_ID and DEFAULT_CLIENT_SECRET:
        try:
            env = USCISEnvironment.PRODUCTION if DEFAULT_ENVIRONMENT.lower() == "production" else USCISEnvironment.SANDBOX
            client = USCISApiClient(DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, env)
            client.authenticate()
            st.session_state.client = client
            st.session_state.credentials_saved = True
            add_log("Auto-Authentication", "SUCCESS", {"environment": env.value})
        except USCISApiError as e:
            add_log("Auto-Authentication", "FAILED", {"error": str(e)})
    
    # Show connection status
    if st.session_state.client:
        token_info = st.session_state.client.get_token_info()
        if token_info.get("authenticated"):
            seconds_remaining = token_info.get("seconds_remaining", 0)
            
            if seconds_remaining > 0:
                st.success("🟢 Connected to USCIS API")
                st.metric("Token Expires In", f"{seconds_remaining}s")
                st.caption(f"Environment: **{token_info.get('environment', 'unknown').upper()}**")
                
                # Show enabled APIs
                api_products = token_info.get("api_products", [])
                if api_products:
                    st.markdown("**Enabled APIs:**")
                    for api in api_products:
                        st.caption(f"✅ {api}")
                    
                    # Check for missing FOIA API
                    has_foia = any("foia" in api.lower() for api in api_products)
                    if not has_foia:
                        st.warning("⚠️ FOIA API not enabled")
                
                # Auto-refresh warning
                if seconds_remaining < 300:
                    st.warning("⚠️ Token expiring soon!")
                    if st.button("🔄 Refresh Token"):
                        try:
                            st.session_state.client.authenticate()
                            st.rerun()
                        except USCISApiError as e:
                            st.error(f"Refresh failed: {e}")
            else:
                st.error("🔴 Token Expired")
                if st.button("🔄 Reconnect"):
                    try:
                        st.session_state.client.authenticate()
                        st.rerun()
                    except USCISApiError as e:
                        st.error(f"Reconnect failed: {e}")
        else:
            st.warning("🟡 Not authenticated")
    else:
        if DEFAULT_CLIENT_ID and DEFAULT_CLIENT_SECRET:
            st.error("🔴 Connection failed - check secrets")
        else:
            st.warning("🟡 Credentials not configured")
            st.info("Add USCIS_CLIENT_ID and USCIS_CLIENT_SECRET to Streamlit secrets")
    
    # Quick links
    st.markdown("---")
    st.markdown("### 📚 Resources")
    st.markdown("""
    - [USCIS Developer Portal](https://developer.uscis.gov)
    - [API Documentation](https://developer.uscis.gov/apis)
    """)
    
    # Sandbox hours notice
    st.markdown("---")
    st.markdown("### ⏰ Sandbox Hours")
    st.info("**Mon-Fri:** 7AM - 8PM EST\n\nSandbox unavailable on weekends")


# ==================== MAIN CONTENT ====================

st.markdown('<p class="main-header">🏛️ USCIS Torch API Testing Console</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Test the official USCIS APIs with your developer credentials</p>', unsafe_allow_html=True)

# Tabs for different APIs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Case Status API", 
    "📝 FOIA API", 
    "🧪 Connection Test",
    "📜 API Logs"
])


# ==================== TAB 1: CASE STATUS API ====================

with tab1:
    st.markdown("## Case Status API")
    st.markdown("""
    Check the status of immigration cases using receipt numbers.
    
    **Endpoint:** `GET /case-status/{receipt_number}`
    
    **Rate Limit:** 10 TPS (Sandbox)
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Query Case Status")
        
        # Receipt number input
        receipt_input = st.text_input(
            "Receipt Number",
            placeholder="e.g., EAC9999103402",
            help="Enter a valid USCIS receipt number"
        )
        
        # Sandbox test receipts - show if using sandbox environment
        if DEFAULT_ENVIRONMENT.lower() == "sandbox":
            st.caption("**Sandbox Test Receipt Numbers:**")
            test_cols = st.columns(3)
            for i, receipt in enumerate(USCISApiClient.SANDBOX_TEST_RECEIPTS):
                with test_cols[i % 3]:
                    if st.button(receipt, key=f"test_{receipt}"):
                        receipt_input = receipt
                        st.session_state.test_receipt = receipt
        
        # Use session state for receipt if clicked
        if 'test_receipt' in st.session_state:
            receipt_input = st.session_state.test_receipt
            del st.session_state.test_receipt
        
        # Query button
        if st.button("🔍 Check Status", type="primary", disabled=not st.session_state.client):
            if not receipt_input:
                st.error("Please enter a receipt number")
            else:
                with st.spinner("Querying USCIS..."):
                    try:
                        start_time = time.time()
                        status = st.session_state.client.get_case_status(receipt_input)
                        elapsed = time.time() - start_time
                        
                        add_log(
                            f"Case Status: {receipt_input}",
                            "SUCCESS",
                            {"form_type": status.form_type, "status": status.status_text_en}
                        )
                        
                        # Display results
                        st.success(f"✅ Query successful ({elapsed:.2f}s)")
                        
                        st.markdown("#### Case Information")
                        
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            st.metric("Receipt Number", status.receipt_number)
                            st.metric("Form Type", status.form_type)
                        with info_col2:
                            st.metric("Submitted", status.submitted_date or "N/A")
                            st.metric("Last Modified", status.modified_date or "N/A")
                        
                        st.markdown("#### Status")
                        st.info(f"**{status.status_text_en}**")
                        st.markdown(status.status_desc_en)
                        
                        # Spanish translation
                        with st.expander("🇪🇸 Spanish Translation"):
                            st.markdown(f"**{status.status_text_es}**")
                            st.markdown(status.status_desc_es)
                        
                        # Raw response
                        with st.expander("📦 Raw API Response"):
                            st.json(status.raw_response)
                        
                    except USCISApiError as e:
                        add_log(f"Case Status: {receipt_input}", "FAILED", {"error": str(e)})
                        st.error(f"❌ API Error: {e}")
                        if e.trace_id:
                            st.caption(f"Trace ID: {e.trace_id}")
    
    with col2:
        st.markdown("### cURL Example")
        
        base_url = "https://api-int.uscis.gov" if DEFAULT_ENVIRONMENT.lower() == "sandbox" else "https://api.uscis.gov"
        curl_cmd = f'''curl -X GET \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/case-status/{receipt_input or 'RECEIPT_NUMBER'}"'''
        
        st.code(curl_cmd, language="bash")
        
        st.markdown("### Response Format")
        st.code('''{
  "case_status": {
    "receiptNumber": "EAC9999103402",
    "formType": "I-130",
    "submittedDate": "09-05-2023",
    "modifiedDate": "09-05-2023",
    "current_case_status_text_en": "...",
    "current_case_status_desc_en": "...",
    "hist_case_status": null
  },
  "message": "Query was successful"
}''', language="json")


# ==================== TAB 2: FOIA API ====================

with tab2:
    st.markdown("## FOIA Request and Status API")
    st.markdown("""
    Create and track Freedom of Information Act (FOIA) requests for Alien File material.
    
    **Endpoints:**
    - `POST /foia/request` - Create new FOIA request
    - `GET /foia/status/{request_number}` - Check request status
    
    **Rate Limit:** 5 TPS (Sandbox)
    """)
    
    # Show API products for debugging
    if st.session_state.client:
        token_info = st.session_state.client.get_token_info()
        api_products = token_info.get("api_products", [])
        with st.expander("🔧 Debug: Your API Products"):
            st.json(api_products)
            st.caption("If FOIA API is not listed here, you need to enable it in developer.uscis.gov")
    
    foia_tab1, foia_tab2 = st.tabs(["Create Request", "Check Status"])
    
    with foia_tab1:
        st.markdown("### Create FOIA Request")
        
        col1, col2 = st.columns(2)
        
        with col1:
            subject_first = st.text_input("Subject First Name *")
            subject_last = st.text_input("Subject Last Name *")
            subject_dob = st.text_input("Date of Birth *", placeholder="MM-DD-YYYY")
            subject_country = st.text_input("Country of Birth *")
        
        with col2:
            a_number = st.text_input("A-Number (optional)", placeholder="A123456789")
            requester_email = st.text_input("Requester Email (optional)")
            request_type = st.selectbox("Request Type", ["ALIEN_FILE", "OTHER"])
        
        if st.button("📤 Submit FOIA Request", type="primary", disabled=not st.session_state.client):
            if not all([subject_first, subject_last, subject_dob, subject_country]):
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Submitting FOIA request..."):
                    try:
                        result = st.session_state.client.create_foia_request(
                            subject_first_name=subject_first,
                            subject_last_name=subject_last,
                            subject_dob=subject_dob,
                            subject_country_of_birth=subject_country,
                            a_number=a_number if a_number else None,
                            requester_email=requester_email if requester_email else None,
                            request_type=request_type
                        )
                        
                        add_log("FOIA Request Created", "SUCCESS", {"request_number": result.request_number})
                        
                        st.success("✅ FOIA Request Submitted!")
                        st.metric("Request Number", result.request_number)
                        
                        with st.expander("📦 Raw Response"):
                            st.json(result.raw_response)
                            
                    except USCISApiError as e:
                        add_log("FOIA Request", "FAILED", {"error": str(e)})
                        st.error(f"❌ API Error: {e}")
    
    with foia_tab2:
        st.markdown("### Check FOIA Status")
        
        request_number = st.text_input("FOIA Request Number", placeholder="Enter request number")
        
        if st.button("🔍 Check FOIA Status", disabled=not st.session_state.client):
            if not request_number:
                st.error("Please enter a request number")
            else:
                with st.spinner("Checking status..."):
                    try:
                        result = st.session_state.client.get_foia_status(request_number)
                        
                        add_log(f"FOIA Status: {request_number}", "SUCCESS", {"status": result.status})
                        
                        st.success("✅ Status Retrieved")
                        st.metric("Status", result.status)
                        
                        with st.expander("📦 Raw Response"):
                            st.json(result.raw_response)
                            
                    except USCISApiError as e:
                        add_log(f"FOIA Status: {request_number}", "FAILED", {"error": str(e)})
                        st.error(f"❌ API Error: {e}")


# ==================== TAB 3: CONNECTION TEST ====================

with tab3:
    st.markdown("## Connection Test")
    st.markdown("Test your API connection and verify the service is working correctly.")
    
    # Show API info (no credentials)
    if st.session_state.client:
        st.markdown("### 🌐 API Configuration")
        col1, col2 = st.columns(2)
        with col1:
            env = st.session_state.client.environment.value.upper()
            st.info(f"**Environment:** {env}")
        with col2:
            base_url = st.session_state.client.base_url
            st.info(f"**Base URL:** {base_url}")
    
    if st.button("🧪 Run Connection Test", type="primary"):
        if not st.session_state.client:
            st.error("Not connected to USCIS API. Check your secrets configuration.")
        else:
            with st.spinner("Running tests..."):
                results = st.session_state.client.test_connection()
                
                add_log("Connection Test", "COMPLETE", {
                    "auth_success": results.get("authentication", {}).get("success"),
                    "api_success": results.get("case_status_api", {}).get("success")
                })
                
                # Display results
                st.markdown("### Test Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### Environment")
                    st.info(results.get("environment", "unknown").upper())
                
                with col2:
                    st.markdown("#### Authentication")
                    auth = results.get("authentication", {})
                    if auth.get("success"):
                        st.success("✅ PASSED")
                    else:
                        st.error("❌ FAILED")
                        st.caption(auth.get("error", "Unknown error"))
                
                with col3:
                    st.markdown("#### Case Status API")
                    case_api = results.get("case_status_api", {})
                    if case_api.get("success"):
                        st.success("✅ PASSED")
                        st.caption(f"Test: {case_api.get('test_receipt')}")
                    else:
                        st.error("❌ FAILED")
                        error_msg = case_api.get("error", "Unknown error")
                        # Check for sandbox hours issue
                        if "unavailable" in error_msg.lower() or "503" in error_msg:
                            st.caption("⏰ Sandbox may be outside operating hours (Mon-Fri 7AM-8PM EST)")
                        else:
                            st.caption(error_msg[:100])
    
    # API endpoints reference
    st.markdown("---")
    st.markdown("### API Endpoints Reference")
    
    endpoints_df = {
        "API": ["OAuth Token", "Case Status", "FOIA Create", "FOIA Status"],
        "Method": ["POST", "GET", "POST", "GET"],
        "Sandbox URL": [
            "https://api-int.uscis.gov/oauth/accesstoken",
            "https://api-int.uscis.gov/case-status/{receipt}",
            "https://api-int.uscis.gov/foia/request",
            "https://api-int.uscis.gov/foia/status/{request_number}"
        ],
        "Production URL": [
            "https://api.uscis.gov/oauth/accesstoken",
            "https://api.uscis.gov/case-status/{receipt}",
            "https://api.uscis.gov/foia/request",
            "https://api.uscis.gov/foia/status/{request_number}"
        ]
    }
    st.dataframe(endpoints_df, use_container_width=True)


# ==================== TAB 4: API LOGS ====================

with tab4:
    st.markdown("## API Request Logs")
    st.markdown("View history of API calls made during this session.")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🗑️ Clear Logs"):
            st.session_state.api_logs = []
            st.rerun()
    
    if not st.session_state.api_logs:
        st.info("No API calls logged yet. Make some requests to see them here.")
    else:
        for i, log in enumerate(st.session_state.api_logs):
            status_icon = "✅" if log["status"] == "SUCCESS" else "❌" if log["status"] == "FAILED" else "ℹ️"
            
            with st.expander(f"{status_icon} {log['action']} - {log['timestamp'][:19]}"):
                st.markdown(f"**Status:** {log['status']}")
                if log.get("details"):
                    st.json(log["details"])


# ==================== FOOTER ====================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    <p>USCIS Torch API Testing Console | Based on <a href="https://developer.uscis.gov">official USCIS documentation</a></p>
    <p>For support, contact: <a href="mailto:uscis-torch-api@uscis.dhs.gov">uscis-torch-api@uscis.dhs.gov</a></p>
</div>
""", unsafe_allow_html=True)
