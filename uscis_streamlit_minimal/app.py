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
    .test-passed {
        color: #28a745;
        font-weight: bold;
    }
    .test-failed {
        color: #dc3545;
        font-weight: bold;
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
if 'traffic_stats' not in st.session_state:
    st.session_state.traffic_stats = {"200": 0, "4xx": 0, "total": 0}

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


def add_log(action: str, status: str, details: dict = None):
    """Add entry to API log"""
    st.session_state.api_logs.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details or {}
    })
    # Keep last 100 logs
    st.session_state.api_logs = st.session_state.api_logs[:100]


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
    
    # Traffic Stats
    st.markdown("---")
    st.markdown("### 📊 Session Traffic")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ 200 OK", st.session_state.traffic_stats["200"])
    with col2:
        st.metric("❌ 4xx", st.session_state.traffic_stats["4xx"])
    st.caption(f"Total: {st.session_state.traffic_stats['total']} requests")
    
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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Case Status API", 
    "📝 FOIA API", 
    "🚀 Production Readiness",
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
        
        # Sandbox test receipts
        if DEFAULT_ENVIRONMENT.lower() == "sandbox":
            st.caption("**Sandbox Test Receipt Numbers:**")
            test_cols = st.columns(3)
            for i, receipt in enumerate(USCISApiClient.SANDBOX_TEST_RECEIPTS):
                with test_cols[i % 3]:
                    if st.button(receipt, key=f"test_{receipt}"):
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
                        
                        # Update traffic stats
                        st.session_state.traffic_stats["200"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        
                        add_log(
                            f"Case Status: {receipt_input}",
                            "SUCCESS",
                            {"form_type": status.form_type, "status": status.status_text_en, "http_code": 200}
                        )
                        
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
                        
                        with st.expander("📦 Raw API Response"):
                            st.json(status.raw_response)
                        
                    except USCISApiError as e:
                        st.session_state.traffic_stats["4xx"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        add_log(f"Case Status: {receipt_input}", "FAILED", {"error": str(e), "http_code": e.status})
                        st.error(f"❌ API Error: {e}")
    
    with col2:
        st.markdown("### cURL Example")
        base_url = "https://api-int.uscis.gov" if DEFAULT_ENVIRONMENT.lower() == "sandbox" else "https://api.uscis.gov"
        curl_cmd = f'''curl -X GET \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  "{base_url}/case-status/{receipt_input or 'RECEIPT_NUMBER'}"'''
        st.code(curl_cmd, language="bash")


# ==================== TAB 2: FOIA API ====================

with tab2:
    st.markdown("## FOIA Request and Status API")
    st.markdown("""
    Create and track Freedom of Information Act (FOIA) requests for Alien File material.
    
    **Endpoints:**
    - `POST /foia/request` - Create new FOIA request
    - `GET /foia/status/{request_number}` - Check request status
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
                        st.session_state.traffic_stats["200"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        add_log("FOIA Request Created", "SUCCESS", {"request_number": result.request_number})
                        st.success("✅ FOIA Request Submitted!")
                        st.metric("Request Number", result.request_number)
                    except USCISApiError as e:
                        st.session_state.traffic_stats["4xx"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        add_log("FOIA Request", "FAILED", {"error": str(e), "http_code": e.status})
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
                        st.session_state.traffic_stats["200"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        add_log(f"FOIA Status: {request_number}", "SUCCESS", {"status": result.status})
                        st.success("✅ Status Retrieved")
                        st.metric("Status", result.status)
                    except USCISApiError as e:
                        st.session_state.traffic_stats["4xx"] += 1
                        st.session_state.traffic_stats["total"] += 1
                        add_log(f"FOIA Status: {request_number}", "FAILED", {"error": str(e)})
                        st.error(f"❌ API Error: {e}")


# ==================== TAB 3: PRODUCTION READINESS ====================

with tab3:
    st.markdown("## 🚀 Production Readiness Testing")
    st.markdown("""
    **USCIS requires both 200 (success) and 4xx (error) responses to be tested before granting production access.**
    
    Use this tab to generate the required API traffic for your production access request.
    """)
    
    # Requirements checklist
    st.markdown("### 📋 USCIS Requirements Checklist")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Must Have:**
        - ✅ 5+ consecutive days of API traffic
        - ✅ 200 OK responses tested
        - ✅ 4xx error responses tested
        """)
    with col2:
        st.markdown("""
        **Current Session:**
        - 200 responses: **{}**
        - 4xx responses: **{}**
        - Total requests: **{}**
        """.format(
            st.session_state.traffic_stats["200"],
            st.session_state.traffic_stats["4xx"],
            st.session_state.traffic_stats["total"]
        ))
    
    st.markdown("---")
    
    # Test sections
    test_col1, test_col2 = st.columns(2)
    
    with test_col1:
        st.markdown("### ✅ Test 200 OK Responses")
        st.caption("Valid requests that return successful responses")
        
        valid_receipts = ["EAC9999103402", "WAC9999103402", "LIN9999103402"]
        
        if st.button("🟢 Run Success Tests (200)", type="primary", disabled=not st.session_state.client):
            results = []
            progress = st.progress(0)
            status_container = st.empty()
            
            for i, receipt in enumerate(valid_receipts):
                status_container.info(f"Testing: {receipt}...")
                try:
                    start = time.time()
                    status = st.session_state.client.get_case_status(receipt)
                    elapsed = time.time() - start
                    
                    st.session_state.traffic_stats["200"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    
                    results.append({
                        "receipt": receipt,
                        "status": "✅ 200 OK",
                        "time": f"{elapsed:.2f}s",
                        "form_type": status.form_type
                    })
                    add_log(f"200 Test: {receipt}", "SUCCESS", {"http_code": 200})
                    
                except USCISApiError as e:
                    results.append({
                        "receipt": receipt,
                        "status": f"❌ {e.status}",
                        "time": "N/A",
                        "error": str(e)[:50]
                    })
                
                progress.progress((i + 1) / len(valid_receipts))
                time.sleep(0.5)  # Rate limiting
            
            status_container.empty()
            st.success(f"✅ Completed {len(valid_receipts)} success tests!")
            st.dataframe(results, use_container_width=True)
    
    with test_col2:
        st.markdown("### ❌ Test 4xx Error Responses")
        st.caption("Invalid requests to test error handling")
        
        error_test_cases = [
            {"receipt": "INVALID", "expected": "400", "description": "Invalid format"},
            {"receipt": "XXX0000000000", "expected": "400/404", "description": "Non-existent receipt"},
            {"receipt": "ABC", "expected": "400", "description": "Too short"},
            {"receipt": "12345", "expected": "400", "description": "Numbers only"},
            {"receipt": "!@#$%", "expected": "400", "description": "Special characters"},
        ]
        
        if st.button("🔴 Run Error Tests (4xx)", type="primary", disabled=not st.session_state.client):
            results = []
            progress = st.progress(0)
            status_container = st.empty()
            
            for i, test in enumerate(error_test_cases):
                status_container.info(f"Testing: {test['receipt']} ({test['description']})...")
                try:
                    st.session_state.client.get_case_status(test["receipt"])
                    # If we get here, it didn't error (unexpected)
                    results.append({
                        "input": test["receipt"],
                        "description": test["description"],
                        "expected": test["expected"],
                        "actual": "200 OK (unexpected)",
                        "status": "⚠️"
                    })
                except USCISApiError as e:
                    st.session_state.traffic_stats["4xx"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    
                    results.append({
                        "input": test["receipt"],
                        "description": test["description"],
                        "expected": test["expected"],
                        "actual": f"{e.status}",
                        "status": "✅" if str(e.status).startswith("4") else "❌"
                    })
                    add_log(f"4xx Test: {test['receipt']}", "SUCCESS", {"http_code": e.status, "error": str(e)[:100]})
                
                progress.progress((i + 1) / len(error_test_cases))
                time.sleep(0.5)  # Rate limiting
            
            status_container.empty()
            st.success(f"✅ Completed {len(error_test_cases)} error tests!")
            st.dataframe(results, use_container_width=True)
    
    st.markdown("---")
    
    # Bulk traffic generator
    st.markdown("### 📈 Bulk Traffic Generator")
    st.caption("Generate multiple API requests to meet the 5-day traffic requirement")
    
    gen_col1, gen_col2, gen_col3 = st.columns(3)
    
    with gen_col1:
        num_success = st.number_input("Number of 200 requests", min_value=1, max_value=50, value=10)
    with gen_col2:
        num_errors = st.number_input("Number of 4xx requests", min_value=1, max_value=20, value=5)
    with gen_col3:
        delay = st.slider("Delay between requests (sec)", min_value=0.5, max_value=3.0, value=1.0)
    
    if st.button("🚀 Generate Traffic", type="primary", disabled=not st.session_state.client):
        total = num_success + num_errors
        progress = st.progress(0)
        status = st.empty()
        results_200 = 0
        results_4xx = 0
        
        # Success requests
        valid_receipts = ["EAC9999103402", "WAC9999103402", "LIN9999103402"]
        for i in range(num_success):
            receipt = valid_receipts[i % len(valid_receipts)]
            status.info(f"[{i+1}/{total}] Testing 200: {receipt}")
            try:
                st.session_state.client.get_case_status(receipt)
                st.session_state.traffic_stats["200"] += 1
                st.session_state.traffic_stats["total"] += 1
                results_200 += 1
                add_log(f"Bulk 200: {receipt}", "SUCCESS", {"http_code": 200})
            except:
                pass
            progress.progress((i + 1) / total)
            time.sleep(delay)
        
        # Error requests
        error_receipts = ["INVALID", "XXX000", "ABC", "123", "!@#"]
        for i in range(num_errors):
            receipt = error_receipts[i % len(error_receipts)]
            status.info(f"[{num_success + i + 1}/{total}] Testing 4xx: {receipt}")
            try:
                st.session_state.client.get_case_status(receipt)
            except USCISApiError as e:
                if str(e.status).startswith("4"):
                    st.session_state.traffic_stats["4xx"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    results_4xx += 1
                    add_log(f"Bulk 4xx: {receipt}", "SUCCESS", {"http_code": e.status})
            progress.progress((num_success + i + 1) / total)
            time.sleep(delay)
        
        status.empty()
        st.success(f"""
        ✅ **Traffic Generation Complete!**
        - 200 OK responses: {results_200}
        - 4xx error responses: {results_4xx}
        - Total requests: {results_200 + results_4xx}
        """)
    
    st.markdown("---")
    
    # Production access info
    st.markdown("### 📧 Ready for Production Access?")
    st.info("""
    Once you have **5+ consecutive days** of traffic with **both 200 and 4xx responses**, email USCIS:
    
    **To:** uscis-torch-api@uscis.dhs.gov
    
    **Subject:** Production Access Request - [Your Company Name]
    
    **Include:**
    - Company name
    - App name  
    - Client ID
    - Confirmation of 5+ days of testing
    - Website URL
    - Privacy Policy URL
    - Terms of Service URL
    """)


# ==================== TAB 4: CONNECTION TEST ====================

with tab4:
    st.markdown("## Connection Test")
    st.markdown("Test your API connection and verify the service is working correctly.")
    
    if st.session_state.client:
        st.markdown("### 🌐 API Configuration")
        col1, col2 = st.columns(2)
        with col1:
            env = st.session_state.client.environment.value.upper()
            st.info(f"**Environment:** {env}")
        with col2:
            base_url = st.session_state.client.base_url
            st.info(f"**Base URL:** {base_url}")
        
        # Show enabled APIs
        token_info = st.session_state.client.get_token_info()
        api_products = token_info.get("api_products", [])
        
        st.markdown("### 📋 Enabled API Products")
        if api_products:
            for api in api_products:
                if "case" in api.lower():
                    st.success(f"✅ {api}")
                elif "foia" in api.lower():
                    st.success(f"✅ {api}")
                else:
                    st.info(f"ℹ️ {api}")
            
            has_foia = any("foia" in api.lower() for api in api_products)
            if not has_foia:
                st.warning("⚠️ **FOIA API not enabled** - Contact uscis-torch-api@uscis.dhs.gov to request access")
    
    if st.button("🧪 Run Full Connection Test", type="primary"):
        if not st.session_state.client:
            st.error("Not connected to USCIS API. Check your secrets configuration.")
        else:
            with st.spinner("Running tests..."):
                results = st.session_state.client.test_connection()
                
                # Also test a 4xx error
                error_test = {"success": False, "error": "Not tested"}
                try:
                    st.session_state.client.get_case_status("INVALID_TEST")
                except USCISApiError as e:
                    if str(e.status).startswith("4"):
                        error_test = {"success": True, "status": e.status}
                        st.session_state.traffic_stats["4xx"] += 1
                        st.session_state.traffic_stats["total"] += 1
                    else:
                        error_test = {"success": False, "error": str(e)}
                
                add_log("Connection Test", "COMPLETE", {
                    "auth": results.get("authentication", {}).get("success"),
                    "api_200": results.get("case_status_api", {}).get("success"),
                    "api_4xx": error_test.get("success")
                })
                
                st.markdown("### Test Results")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("#### Environment")
                    st.info(results.get("environment", "unknown").upper())
                
                with col2:
                    st.markdown("#### Auth")
                    if results.get("authentication", {}).get("success"):
                        st.success("✅ PASSED")
                    else:
                        st.error("❌ FAILED")
                
                with col3:
                    st.markdown("#### 200 OK")
                    if results.get("case_status_api", {}).get("success"):
                        st.success("✅ PASSED")
                        st.session_state.traffic_stats["200"] += 1
                        st.session_state.traffic_stats["total"] += 1
                    else:
                        st.error("❌ FAILED")
                
                with col4:
                    st.markdown("#### 4xx Error")
                    if error_test.get("success"):
                        st.success(f"✅ {error_test.get('status')}")
                    else:
                        st.error("❌ FAILED")
    
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
        ]
    }
    st.dataframe(endpoints_df, use_container_width=True)


# ==================== TAB 5: API LOGS ====================

with tab5:
    st.markdown("## API Request Logs")
    st.markdown("View history of API calls made during this session.")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🗑️ Clear Logs"):
            st.session_state.api_logs = []
            st.session_state.traffic_stats = {"200": 0, "4xx": 0, "total": 0}
            st.rerun()
    
    # Summary stats
    if st.session_state.api_logs:
        success_count = len([l for l in st.session_state.api_logs if l["status"] == "SUCCESS"])
        failed_count = len([l for l in st.session_state.api_logs if l["status"] == "FAILED"])
        st.markdown(f"**Total:** {len(st.session_state.api_logs)} logs | ✅ Success: {success_count} | ❌ Failed: {failed_count}")
    
    if not st.session_state.api_logs:
        st.info("No API calls logged yet. Make some requests to see them here.")
    else:
        for i, log in enumerate(st.session_state.api_logs[:50]):  # Show last 50
            status_icon = "✅" if log["status"] == "SUCCESS" else "❌" if log["status"] == "FAILED" else "ℹ️"
            http_code = log.get("details", {}).get("http_code", "")
            http_badge = f" [{http_code}]" if http_code else ""
            
            with st.expander(f"{status_icon} {log['action']}{http_badge} - {log['timestamp'][:19]}"):
                st.markdown(f"**Status:** {log['status']}")
                if log.get("details"):
                    st.json(log["details"])


# ==================== FOOTER ====================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    <p>USCIS Torch API Testing Console | <a href="https://developer.uscis.gov">USCIS Developer Portal</a></p>
    <p>Support: <a href="mailto:uscis-torch-api@uscis.dhs.gov">uscis-torch-api@uscis.dhs.gov</a></p>
</div>
""", unsafe_allow_html=True)
