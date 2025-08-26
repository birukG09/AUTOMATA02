import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Dashboard")

# Initialize session state
if 'db_manager' not in st.session_state:
    st.error("Database manager not initialized. Please go back to the main page.")
    st.stop()

db_manager = st.session_state.db_manager

# Dashboard metrics
st.header("System Overview")

col1, col2, col3, col4 = st.columns(4)

try:
    stats = db_manager.get_dashboard_stats()
    
    with col1:
        st.metric(
            label="Total Files",
            value=stats['total_files'],
            delta=None
        )
    
    with col2:
        st.metric(
            label="Files Today",
            value=stats['files_today'],
            delta=None
        )
    
    with col3:
        st.metric(
            label="Categories",
            value=stats['unique_labels'],
            delta=None
        )
    
    with col4:
        # Calculate processing rate (files per day over last 7 days)
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            files_week = db_manager.search_files(limit=10000)  # Get many files
            files_this_week = [f for f in files_week if f['created_at'] >= week_ago]
            rate = len(files_this_week) / 7 if files_this_week else 0
            st.metric(
                label="Files/Day (7d avg)",
                value=f"{rate:.1f}",
                delta=None
            )
        except:
            st.metric(
                label="Files/Day (7d avg)",
                value="N/A",
                delta=None
            )

except Exception as e:
    st.error(f"Error loading dashboard stats: {e}")

st.markdown("---")

# Recent Activity and Category Distribution
col1, col2 = st.columns(2)

with col1:
    st.subheader("Recent Activity")
    try:
        recent_files = db_manager.get_recent_files(limit=10)
        if recent_files:
            for file_info in recent_files:
                file_name = Path(file_info['path']).name
                st.write(f"📄 **{file_name}**")
                st.caption(f"Category: {file_info['label']} | {file_info['created_at'][:16]}")
                if file_info['tags']:
                    tags_str = ", ".join(file_info['tags'])
                    st.caption(f"Tags: {tags_str}")
                st.markdown("")
        else:
            st.info("No recent files found. Start the file watcher to begin monitoring.")
    except Exception as e:
        st.error(f"Error loading recent activity: {e}")

with col2:
    st.subheader("File Categories")
    try:
        category_stats = db_manager.get_category_distribution()
        if category_stats:
            # Create pie chart
            fig = px.pie(
                values=list(category_stats.values()),
                names=list(category_stats.keys()),
                title="Distribution by Category"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No files categorized yet.")
    except Exception as e:
        st.error(f"Error loading category distribution: {e}")

st.markdown("---")

# Activity Timeline
st.subheader("Activity Timeline")
try:
    # Get files from last 30 days
    files = db_manager.search_files(limit=1000)
    if files:
        # Convert to DataFrame
        df = pd.DataFrame(files)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['date'] = df['created_at'].dt.date
        
        # Group by date and category
        daily_activity = df.groupby(['date', 'label']).size().reset_index(name='count')
        
        # Create stacked bar chart
        fig = px.bar(
            daily_activity,
            x='date',
            y='count',
            color='label',
            title="Daily File Processing by Category",
            labels={'count': 'Number of Files', 'date': 'Date'}
        )
        fig.update_layout(xaxis_title="Date", yaxis_title="Number of Files")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No activity data available yet.")
except Exception as e:
    st.error(f"Error creating activity timeline: {e}")

st.markdown("---")

# System Status
st.subheader("System Status")

col1, col2 = st.columns(2)

with col1:
    st.write("**File Watcher Status:**")
    if st.session_state.get('watcher_running', False):
        st.success("✅ Active and monitoring")
    else:
        st.warning("⏸️ Inactive")
    
    st.write("**Database Status:**")
    if db_manager.test_connection():
        st.success("✅ Connected")
    else:
        st.error("❌ Connection error")

with col2:
    st.write("**Monitored Paths:**")
    config_manager = st.session_state.get('config_manager')
    if config_manager:
        watch_paths = config_manager.get_watch_paths()
        for path in watch_paths:
            if Path(path).exists():
                st.success(f"✅ {path}")
            else:
                st.error(f"❌ {path} (not found)")
    
    st.write("**Active Rules:**")
    if config_manager:
        rules = config_manager.get_rules()
        active_rules = [r for r in rules if r.get('active', True)]
        st.write(f"{len(active_rules)} rules active")

# Activity Log
st.markdown("---")
st.subheader("Recent Activity Log")

try:
    activities = db_manager.get_activity_log(limit=20)
    if activities:
        # Display activity log
        for activity in activities:
            status_icon = "✅" if activity['status'] == 'success' else "❌"
            st.write(f"{status_icon} **{activity['action']}** - {Path(activity['file_path']).name}")
            st.caption(f"{activity['timestamp'][:16]}")
            
            if activity['details']:
                with st.expander(f"Details", expanded=False):
                    st.json(activity['details'])
            st.markdown("")
    else:
        st.info("No activity logged yet.")
except Exception as e:
    st.error(f"Error loading activity log: {e}")

# Refresh button
if st.button("🔄 Refresh Dashboard", type="primary"):
    st.rerun()
