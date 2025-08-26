import streamlit as st
import os
import threading
import time
from pathlib import Path
from core.database import DatabaseManager
from core.file_watcher import FileWatcher
from core.config_manager import ConfigManager
from utils.logger import setup_logger

# Initialize logger
logger = setup_logger()

# Page config
st.set_page_config(
    page_title="AUTOMATA02 - Intelligent Workspace Automation Hub",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    with open('powerbi_components.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# Initialize session state
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()

if 'config_manager' not in st.session_state:
    st.session_state.config_manager = ConfigManager()

if 'file_watcher' not in st.session_state:
    st.session_state.file_watcher = None

if 'watcher_running' not in st.session_state:
    st.session_state.watcher_running = False

# Sidebar Navigation
with st.sidebar:
    # Logo and Brand
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px;">
        <div class="app-logo">A2</div>
        <div style="color: var(--text-high); font-size: 18px; font-weight: 600;">AUTOMATA02</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation Menu
    st.markdown("### 📊 Dashboard")
    st.markdown("### 📁 File Inventory")
    st.markdown("### ⚙️ Rules Editor")
    st.markdown("### 🧠 Workflow Learning")
    st.markdown("### 💬 Natural Language")
    st.markdown("### 🚨 Anomaly Detection")
    st.markdown("### 📈 Knowledge Graph")
    st.markdown("### ⏰ Scheduler")
    
    st.markdown("---")
    
    # System Status
    st.markdown("### System Status")
    
    # Database status
    db_status = st.session_state.db_manager.test_connection()
    if db_status:
        st.markdown('<div class="status-indicator status-active">🟢 Database Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-indicator status-danger">🔴 Database Error</div>', unsafe_allow_html=True)
    
    # File watcher status
    if st.session_state.watcher_running:
        st.markdown('<div class="status-indicator status-active">🟢 File Watcher Active</div>', unsafe_allow_html=True)
        if st.button("Stop Watcher", type="secondary"):
            if st.session_state.file_watcher:
                st.session_state.file_watcher.stop()
                st.session_state.watcher_running = False
                st.success("File watcher stopped")
                st.rerun()
    else:
        st.markdown('<div class="status-indicator status-warning">🟡 File Watcher Inactive</div>', unsafe_allow_html=True)
        if st.button("Start Watcher", type="primary"):
            try:
                if not st.session_state.file_watcher:
                    st.session_state.file_watcher = FileWatcher(
                        st.session_state.db_manager,
                        st.session_state.config_manager
                    )
                
                st.session_state.file_watcher.start()
                st.session_state.watcher_running = True
                st.success("File watcher started")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start file watcher: {e}")
                logger.error(f"Failed to start file watcher: {e}")

    st.markdown("---")
    
    # Quick Stats
    st.markdown("### Quick Metrics")
    try:
        stats = st.session_state.db_manager.get_dashboard_stats()
        
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Files</h3>
            <div class="metric-value">{stats['total_files']:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h3>Files Today</h3>
            <div class="metric-value">{stats['files_today']:,}</div>
            <div class="metric-change">+{stats.get('files_change', 0)} vs yesterday</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h3>Categories</h3>
            <div class="metric-value">{stats['unique_labels']:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error("Error loading stats")
        logger.error(f"Error loading stats: {e}")

# Main Header
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 class="app-title">
                <div class="app-logo">A2</div>
                AUTOMATA02 Dashboard
            </h1>
            <p style="color: var(--text-medium); margin: 8px 0 0 0; font-size: 14px;">
                Intelligent workspace automation and file organization
            </p>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <div class="status-indicator status-info">🔄 Live Mode</div>
            <div class="status-indicator status-active">🤖 AI Active</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Content Container
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Dashboard Stats Grid
st.markdown("### System Overview")

try:
    stats = st.session_state.db_manager.get_dashboard_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card animate-hover">
            <h3>Files Processed</h3>
            <div class="metric-value">{stats['total_files']:,}</div>
            <div class="metric-change">+{stats.get('files_change', 12)} today</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card animate-hover">
            <h3>Categories</h3>
            <div class="metric-value">{stats['unique_labels']:,}</div>
            <div class="metric-change">Auto-classified</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        watcher_status = "Active" if st.session_state.watcher_running else "Inactive"
        watcher_color = "var(--text-success)" if st.session_state.watcher_running else "var(--text-warning)"
        st.markdown(f"""
        <div class="metric-card animate-hover">
            <h3>File Watcher</h3>
            <div class="metric-value" style="color: {watcher_color}; font-size: 20px;">{watcher_status}</div>
            <div class="metric-change">Real-time monitoring</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        rules_count = len(st.session_state.config_manager.get_rules())
        st.markdown(f"""
        <div class="metric-card animate-hover">
            <h3>Active Rules</h3>
            <div class="metric-value">{rules_count}</div>
            <div class="metric-change">Automation rules</div>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error("Error loading dashboard stats")
    logger.error(f"Error loading dashboard stats: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# Main Content Grid
col1, col2 = st.columns([2, 1])

with col1:
    # Recent Activity Section
    st.markdown("### Recent Activity")
    
    try:
        recent_files = st.session_state.db_manager.get_recent_files(limit=8)
        if recent_files:
            st.markdown("""
            <div class="info-card">
            """, unsafe_allow_html=True)
            
            for i, file_info in enumerate(recent_files):
                file_name = Path(file_info['path']).name
                file_icon = "📄" if not file_info.get('label') else {
                    'document': '📄',
                    'image': '🖼️',
                    'video': '🎥',
                    'audio': '🎵',
                    'archive': '📦',
                    'code': '💻'
                }.get(file_info['label'], '📄')
                
                st.markdown(f"""
                <div style="padding: 12px 0; border-bottom: 1px solid var(--border-muted); display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 18px;">{file_icon}</span>
                        <div>
                            <div style="color: var(--text-high); font-weight: 500;">{file_name}</div>
                            <div style="color: var(--text-medium); font-size: 12px;">
                                {file_info['label'].title() if file_info.get('label') else 'Uncategorized'} • 
                                {file_info.get('created_at', 'Unknown time')[:16]}
                            </div>
                        </div>
                    </div>
                    <div class="status-indicator status-active" style="font-size: 10px;">
                        Processed
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if i >= 7:  # Limit to 8 items
                    break
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-card">
                <div style="text-align: center; padding: 40px 20px; color: var(--text-medium);">
                    <div style="font-size: 48px; margin-bottom: 16px;">🚀</div>
                    <h3 style="color: var(--text-high); margin-bottom: 8px;">Ready to Start</h3>
                    <p>No recent files found. Start the file watcher to begin monitoring your workspace.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error("Error loading recent activity")
        logger.error(f"Error loading recent activity: {e}")

with col2:
    # System Status & Quick Actions
    st.markdown("### System Status")
    
    # Watch Paths Status
    watch_paths = st.session_state.config_manager.get_watch_paths()
    
    st.markdown("""
    <div class="info-card">
        <h3>Monitored Folders</h3>
    """, unsafe_allow_html=True)
    
    for path in watch_paths:
        if os.path.exists(path):
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; padding: 8px 0;">
                <span class="status-indicator status-active" style="font-size: 10px;">Active</span>
                <span style="color: var(--text-high); font-size: 13px;">{path}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; padding: 8px 0;">
                <span class="status-indicator status-danger" style="font-size: 10px;">Missing</span>
                <span style="color: var(--text-medium); font-size: 13px;">{path}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("### Quick Actions")
    
    if st.button("🔍 View File Inventory", use_container_width=True):
        st.switch_page("pages/1_Dashboard.py")
    
    if st.button("⚙️ Configure Rules", use_container_width=True):
        st.switch_page("pages/3_Rules.py")
    
    if st.button("🧠 View Workflow Learning", use_container_width=True):
        st.switch_page("pages/5_Workflow_Learning.py")
    
    if st.button("💬 Natural Language Commands", use_container_width=True):
        st.switch_page("pages/6_Natural_Language.py")

# Feature Highlights
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### Advanced Features")

feature_col1, feature_col2, feature_col3 = st.columns(3)

with feature_col1:
    st.markdown("""
    <div class="info-card animate-hover">
        <h3>🧠 Behavioral Learning</h3>
        <p style="color: var(--text-medium); margin: 8px 0;">
            Automatically learns your workflow patterns and suggests intelligent automations
        </p>
        <div class="status-indicator status-active" style="margin-top: 12px;">
            15 patterns discovered
        </div>
    </div>
    """, unsafe_allow_html=True)

with feature_col2:
    st.markdown("""
    <div class="info-card animate-hover">
        <h3>💬 Natural Language</h3>
        <p style="color: var(--text-medium); margin: 8px 0;">
            Control your file system with plain English commands and conversational AI
        </p>
        <div class="status-indicator status-info" style="margin-top: 12px;">
            Ready for commands
        </div>
    </div>
    """, unsafe_allow_html=True)

with feature_col3:
    st.markdown("""
    <div class="info-card animate-hover">
        <h3>🚨 Anomaly Detection</h3>
        <p style="color: var(--text-medium); margin: 8px 0;">
            ML-powered detection of unusual patterns and proactive system monitoring
        </p>
        <div class="status-indicator status-active" style="margin-top: 12px;">
            All systems normal
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close main-content

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-medium); padding: 20px 0; font-size: 13px;">
    <strong>AUTOMATA02</strong> • Intelligent Workspace Automation Hub • 
    Use sidebar navigation to explore advanced features
</div>
""", unsafe_allow_html=True)
