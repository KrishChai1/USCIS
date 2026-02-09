"""
USCIS Torch API Testing Console
Interactive Streamlit app for testing USCIS APIs

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

# ============================================
# DEMO ID CONFIGURATION - USCIS REQUIRED
# ============================================
DEMO_ID = "3401"  # USCIS assigned demo ID for production access

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
    .demo-box {
        background-color: #e8f4f8;
        border: 2px solid #0066cc;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .header-box {
        background-color: #1e1e1e;
        color: #00ff00;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
    .success-row {
        background-color: #d4edda;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 3px;
    }
    .error-row {
        background-color: #fff3cd;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'client' not in st.session_state:
    st.session_state.client = None
if 'demo_client' not in st.session_state:
    st.session_state.demo_client = None
if 'api_logs' not in st.session_state:
    st.session_state.api_logs = []
if 'traffic_stats' not in st.session_state:
    st.session_state.traffic_stats = {"200": 0, "4xx": 0, "total": 0}

# Load credentials from Streamlit secrets
def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

DEFAULT_CLIENT_ID = get_secret("USCIS_CLIENT_ID", "")
DEFAULT_CLIENT_SECRET = get_secret("USCIS_CLIENT_SECRET", "")
DEFAULT_ENVIRONMENT = get_secret("USCIS_ENVIRONMENT", "sandbox")


def add_log(action: str, status: str, details: dict = None):
    st.session_state.api_logs.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details or {}
    })
    st.session_state.api_logs = st.session_state.api_logs[:100]


# ==================== SIDEBAR ====================

with st.sidebar:
    st.markdown("### 🔐 Connection Status")
    
    # Auto-connect on startup
    if not st.session_state.client and DEFAULT_CLIENT_ID and DEFAULT_CLIENT_SECRET:
        try:
            env = USCISEnvironment.PRODUCTION if DEFAULT_ENVIRONMENT.lower() == "production" else USCISEnvironment.SANDBOX
            client = USCISApiClient(DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, env, demo_id=DEMO_ID)
            client.authenticate()
            st.session_state.client = client
            add_log("Auto-Authentication", "SUCCESS", {"environment": env.value, "demo_id": DEMO_ID})
        except USCISApiError as e:
            add_log("Auto-Authentication", "FAILED", {"error": str(e)})
    
    if st.session_state.client:
        token_info = st.session_state.client.get_token_info()
        if token_info.get("authenticated"):
            seconds_remaining = token_info.get("seconds_remaining", 0)
            if seconds_remaining > 0:
                st.success("🟢 Connected")
                st.metric("Token Expires", f"{seconds_remaining}s")
                st.caption(f"Environment: **{token_info.get('environment', 'unknown').upper()}**")
                st.caption(f"Demo ID: **{DEMO_ID}**")
            else:
                st.error("🔴 Token Expired")
                if st.button("🔄 Reconnect"):
                    st.session_state.client.authenticate()
                    st.rerun()
    else:
        st.warning("🟡 Not connected")
    
    st.markdown("---")
    st.markdown("### 📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ 200", st.session_state.traffic_stats["200"])
    with col2:
        st.metric("❌ 4xx", st.session_state.traffic_stats["4xx"])
    
    st.markdown("---")
    st.markdown("### ⏰ Sandbox Hours")
    st.info("Mon-Fri: 7AM-8PM EST")


# ==================== MAIN CONTENT ====================

st.markdown('<p class="main-header">🏛️ USCIS Torch API Console</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Demo ID: {DEMO_ID} | Production Access Testing</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Case Status", 
    "🎯 USCIS Demo",
    "🚀 Traffic Test",
    "🧪 Connection",
    "📜 Logs"
])


# ==================== TAB 1: CASE STATUS ====================

with tab1:
    st.markdown("## Case Status API")
    
    receipt_input = st.text_input("Receipt Number", placeholder="e.g., EAC9999103402")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("EAC9999103402"):
            receipt_input = "EAC9999103402"
    with col2:
        if st.button("WAC9999103402"):
            receipt_input = "WAC9999103402"
    with col3:
        if st.button("LIN9999103402"):
            receipt_input = "LIN9999103402"
    
    if st.button("🔍 Check Status", type="primary", disabled=not st.session_state.client):
        if receipt_input:
            with st.spinner("Querying USCIS..."):
                try:
                    status = st.session_state.client.get_case_status(receipt_input)
                    st.session_state.traffic_stats["200"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    add_log(f"Case: {receipt_input}", "SUCCESS", {"http": 200})
                    
                    st.success(f"✅ HTTP 200 OK")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Receipt", status.receipt_number)
                        st.metric("Form", status.form_type)
                    with col2:
                        st.metric("Submitted", status.submitted_date or "N/A")
                        st.metric("Modified", status.modified_date or "N/A")
                    
                    st.info(f"**{status.status_text_en}**")
                    
                except USCISApiError as e:
                    st.session_state.traffic_stats["4xx"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    add_log(f"Case: {receipt_input}", "ERROR", {"http": e.status})
                    st.error(f"❌ HTTP {e.status}: {e}")


# ==================== TAB 2: USCIS DEMO (SCREENSHOT THIS) ====================

with tab2:
    st.markdown("## 🎯 USCIS Production Access Demo")
    st.markdown("**Screenshot this page for USCIS submission**")
    
    st.markdown("---")
    
    # Demo ID Box
    st.markdown(f"""
    <div class="demo-box">
        <h3>📋 Demo Configuration</h3>
        <p><strong>Demo ID:</strong> {DEMO_ID}</p>
        <p><strong>Environment:</strong> Sandbox (api-int.uscis.gov)</p>
        <p><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Request Headers
    st.markdown("### 📤 Request Headers")
    st.markdown(f"""
    <div class="header-box">
Content-Type: application/json<br>
Accept: application/json<br>
<span style="color: #ffff00; font-weight: bold;">demo_id: {DEMO_ID}</span>  ← USCIS REQUIRED HEADER<br>
Authorization: Bearer &lt;token&gt;
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Run Demo Button
    if st.button("🚀 RUN COMPLETE DEMO TEST", type="primary", use_container_width=True):
        
        if not DEFAULT_CLIENT_ID or not DEFAULT_CLIENT_SECRET:
            st.error("❌ Missing credentials in secrets")
        else:
            # Create client with demo_id
            st.markdown("### Step 1: Initialize Client with demo_id")
            
            demo_client = USCISApiClient(
                client_id=DEFAULT_CLIENT_ID,
                client_secret=DEFAULT_CLIENT_SECRET,
                environment=USCISEnvironment.SANDBOX,
                demo_id=DEMO_ID  # ← USCIS Demo ID Header
            )
            
            st.code(f"""
client = USCISApiClient(
    client_id="***",
    client_secret="***",
    environment=USCISEnvironment.SANDBOX,
    demo_id="{DEMO_ID}"  # ← USCIS Demo ID
)
            """, language="python")
            
            st.success(f"✅ Client initialized with demo_id: {DEMO_ID}")
            
            # Authenticate
            st.markdown("### Step 2: Authenticate")
            try:
                demo_client.authenticate()
                st.success("✅ Authentication successful")
                
                # Show headers
                st.markdown("### Step 3: Verify Headers")
                headers = demo_client.get_request_headers()
                
                header_display = ""
                for k, v in headers.items():
                    if k == "demo_id":
                        header_display += f"**{k}: {v}** ← USCIS DEMO ID\n\n"
                    else:
                        header_display += f"{k}: {v}\n\n"
                
                st.markdown(header_display)
                
                # Test 200 responses
                st.markdown("### Step 4: Test 200 OK Responses")
                
                valid_receipts = ["EAC9999103402", "WAC9999103402", "LIN9999103402"]
                results_200 = []
                
                progress = st.progress(0)
                for i, receipt in enumerate(valid_receipts):
                    try:
                        status = demo_client.get_case_status(receipt)
                        results_200.append({
                            "Receipt": receipt,
                            "HTTP": "200 ✅",
                            "Form": status.form_type,
                            "Status": "Success"
                        })
                        st.session_state.traffic_stats["200"] += 1
                        st.session_state.traffic_stats["total"] += 1
                    except USCISApiError as e:
                        results_200.append({
                            "Receipt": receipt,
                            "HTTP": f"{e.status} ❌",
                            "Form": "N/A",
                            "Status": str(e)[:30]
                        })
                    progress.progress((i + 1) / len(valid_receipts))
                    time.sleep(0.5)
                
                st.table(results_200)
                
                # Test 4xx responses
                st.markdown("### Step 5: Test 4xx Error Responses")
                
                invalid_receipts = [
                    ("INVALID", "Invalid format"),
                    ("XXX0000000000", "Invalid prefix"),
                    ("ABC", "Too short"),
                ]
                results_4xx = []
                
                progress2 = st.progress(0)
                for i, (receipt, desc) in enumerate(invalid_receipts):
                    try:
                        demo_client.get_case_status(receipt)
                        results_4xx.append({
                            "Input": receipt,
                            "HTTP": "200 ⚠️",
                            "Expected": "4xx",
                            "Description": desc
                        })
                    except USCISApiError as e:
                        results_4xx.append({
                            "Input": receipt,
                            "HTTP": f"{e.status} ✅",
                            "Expected": "4xx",
                            "Description": desc
                        })
                        st.session_state.traffic_stats["4xx"] += 1
                        st.session_state.traffic_stats["total"] += 1
                    progress2.progress((i + 1) / len(invalid_receipts))
                    time.sleep(0.5)
                
                st.table(results_4xx)
                
                # Summary
                st.markdown("### 📊 Demo Summary")
                st.markdown(f"""
                <div class="demo-box">
                    <h4>✅ DEMO COMPLETE</h4>
                    <p><strong>Demo ID:</strong> {DEMO_ID}</p>
                    <p><strong>200 OK Responses:</strong> {len(valid_receipts)}</p>
                    <p><strong>4xx Error Responses:</strong> {len(invalid_receipts)}</p>
                    <p><strong>Total API Requests:</strong> {len(valid_receipts) + len(invalid_receipts)}</p>
                    <p><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.balloons()
                
            except USCISApiError as e:
                st.error(f"❌ Authentication failed: {e}")


# ==================== TAB 3: TRAFFIC TEST ====================

with tab3:
    st.markdown("## 🚀 Traffic Generator")
    st.markdown(f"**Demo ID: {DEMO_ID}** - All requests include demo_id header")
    
    st.markdown("---")
    
    # Quick Tests
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ 200 OK Tests")
        if st.button("Run 3 Success Tests", disabled=not st.session_state.client):
            for receipt in ["EAC9999103402", "WAC9999103402", "LIN9999103402"]:
                try:
                    st.session_state.client.get_case_status(receipt)
                    st.session_state.traffic_stats["200"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    st.success(f"✅ {receipt} - 200 OK")
                except USCISApiError as e:
                    st.error(f"❌ {receipt} - {e.status}")
                time.sleep(0.5)
    
    with col2:
        st.markdown("### ❌ 4xx Error Tests")
        if st.button("Run 3 Error Tests", disabled=not st.session_state.client):
            for receipt in ["INVALID", "XXX000", "ABC"]:
                try:
                    st.session_state.client.get_case_status(receipt)
                except USCISApiError as e:
                    st.session_state.traffic_stats["4xx"] += 1
                    st.session_state.traffic_stats["total"] += 1
                    st.success(f"✅ {receipt} - {e.status} (expected)")
                time.sleep(0.5)
    
    st.markdown("---")
    
    # Bulk Traffic Generator
    st.markdown("### 📈 Bulk Traffic Generator")
    st.caption("Generate multiple API requests to meet USCIS traffic requirements")
    
    gen_col1, gen_col2, gen_col3 = st.columns(3)
    
    with gen_col1:
        num_success = st.number_input("Number of 200 requests", min_value=1, max_value=50, value=10)
    with gen_col2:
        num_errors = st.number_input("Number of 4xx requests", min_value=1, max_value=20, value=5)
    with gen_col3:
        delay = st.slider("Delay between requests (sec)", min_value=0.5, max_value=3.0, value=1.0)
    
    if st.button("🚀 Generate Bulk Traffic", type="primary", disabled=not st.session_state.client, use_container_width=True):
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
            except USCISApiError as e:
                status.warning(f"Request failed: {e}")
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
            progress.progress((num_success + i + 1) / total)
            time.sleep(delay)
        
        status.empty()
        st.success(f"""
        ✅ **Bulk Traffic Complete!**
        - Demo ID: {DEMO_ID}
        - 200 OK responses: {results_200}
        - 4xx error responses: {results_4xx}
        - Total requests: {results_200 + results_4xx}
        """)


# ==================== TAB 4: CONNECTION ====================

with tab4:
    st.markdown("## 🧪 Connection Test")
    
    if st.session_state.client:
        st.info(f"**Environment:** {st.session_state.client.environment.value.upper()}")
        st.info(f"**Demo ID:** {DEMO_ID}")
        st.info(f"**Base URL:** {st.session_state.client.base_url}")
        
        st.markdown("### Request Headers")
        if st.session_state.client.is_authenticated:
            headers = st.session_state.client.get_request_headers()
            st.json(headers)
    
    if st.button("🧪 Test Connection"):
        if st.session_state.client:
            results = st.session_state.client.test_connection()
            st.json(results)


# ==================== TAB 5: LOGS ====================

with tab5:
    st.markdown("## 📜 API Logs")
    
    if st.button("Clear Logs"):
        st.session_state.api_logs = []
        st.session_state.traffic_stats = {"200": 0, "4xx": 0, "total": 0}
        st.rerun()
    
    if st.session_state.api_logs:
        for log in st.session_state.api_logs[:20]:
            icon = "✅" if log["status"] == "SUCCESS" else "❌"
            st.text(f"{icon} {log['timestamp'][:19]} | {log['action']}")
    else:
        st.info("No logs yet")


# ==================== FOOTER ====================

st.markdown("---")
st.caption(f"USCIS Torch API Console | Demo ID: {DEMO_ID} | [Developer Portal](https://developer.uscis.gov)")
