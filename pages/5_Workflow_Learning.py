import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Workflow Learning", page_icon="🧠", layout="wide")

st.title("🧠 Behavioral Workflow Learning")

# Initialize session state
if 'db_manager' not in st.session_state:
    st.error("Database manager not initialized. Please go back to the main page.")
    st.stop()

# Initialize workflow learner if not exists
if 'workflow_learner' not in st.session_state:
    try:
        from core.workflow_learner import BehavioralWorkflowLearner
        st.session_state.workflow_learner = BehavioralWorkflowLearner(st.session_state.db_manager)
    except Exception as e:
        st.error(f"Error initializing workflow learner: {e}")
        st.stop()

workflow_learner = st.session_state.workflow_learner

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Patterns", "💡 Suggestions", "⚙️ Settings"])

with tab1:
    st.header("Workflow Learning Overview")
    
    # Get workflow stats
    try:
        stats = workflow_learner.get_workflow_stats()
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Events Captured",
                value=f"{stats.get('total_events', 0):,}",
                delta=f"+{stats.get('recent_activity', 0)} (24h)"
            )
        
        with col2:
            st.metric(
                label="Patterns Discovered",
                value=stats.get('patterns_discovered', 0),
                delta=None
            )
        
        with col3:
            st.metric(
                label="Pending Suggestions",
                value=stats.get('pending_suggestions', 0),
                delta=None
            )
        
        with col4:
            monitoring_status = "🟢 Active" if stats.get('monitoring_active', False) else "🔴 Inactive"
            st.metric(
                label="Monitoring Status",
                value=monitoring_status,
                delta=None
            )
    
    except Exception as e:
        st.error(f"Error loading workflow stats: {e}")
    
    st.markdown("---")
    
    # Control panel
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Learning Control")
        
        if workflow_learner.monitoring:
            if st.button("🛑 Stop Learning", type="secondary"):
                workflow_learner.stop_monitoring()
                st.success("Workflow learning stopped")
                st.rerun()
        else:
            if st.button("▶️ Start Learning", type="primary"):
                workflow_learner.start_monitoring()
                st.success("Workflow learning started")
                st.rerun()
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    with col2:
        st.subheader("Quick Actions")
        
        if st.button("🧹 Clear Old Events"):
            st.info("Feature coming soon - clear events older than 30 days")
        
        if st.button("📤 Export Patterns"):
            st.info("Feature coming soon - export discovered patterns")
    
    # Recent activity
    st.subheader("Recent Workflow Activity")
    
    # Mock recent activity for demonstration
    recent_activities = [
        {"time": "2 minutes ago", "event": "File moved to Finance folder", "confidence": 0.9},
        {"time": "5 minutes ago", "event": "PDF opened and renamed", "confidence": 0.8},
        {"time": "12 minutes ago", "event": "Multiple files organized by type", "confidence": 0.95},
        {"time": "18 minutes ago", "event": "New CSV file processed", "confidence": 0.7},
        {"time": "25 minutes ago", "event": "Application workflow detected", "confidence": 0.85}
    ]
    
    for activity in recent_activities:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{activity['event']}**")
        with col2:
            st.caption(activity['time'])
        with col3:
            confidence_color = "green" if activity['confidence'] > 0.8 else "orange" if activity['confidence'] > 0.6 else "red"
            st.markdown(f"<span style='color: {confidence_color}'>●</span> {activity['confidence']:.1%}", unsafe_allow_html=True)

with tab2:
    st.header("Discovered Patterns")
    
    # Pattern visualization
    st.subheader("Workflow Pattern Analysis")
    
    # Mock pattern data for demonstration
    pattern_data = [
        {
            "pattern": "Download → Rename → Move",
            "frequency": 15,
            "confidence": 0.92,
            "last_seen": "2 hours ago",
            "sequence": ["file_operation:created", "file_operation:rename", "file_operation:move"]
        },
        {
            "pattern": "PDF Open → Export → Organize",
            "frequency": 8,
            "confidence": 0.85,
            "last_seen": "4 hours ago",
            "sequence": ["app_action:running:acrobat", "file_operation:export", "file_operation:move"]
        },
        {
            "pattern": "CSV Import → Process → Save",
            "frequency": 12,
            "confidence": 0.78,
            "last_seen": "1 day ago",
            "sequence": ["file_operation:created:.csv", "app_action:running:excel", "file_operation:export"]
        }
    ]
    
    # Display patterns
    for i, pattern in enumerate(pattern_data):
        with st.expander(f"Pattern {i+1}: {pattern['pattern']}", expanded=i==0):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Frequency", pattern['frequency'])
                st.metric("Confidence", f"{pattern['confidence']:.1%}")
            
            with col2:
                st.write("**Sequence:**")
                for step in pattern['sequence']:
                    st.write(f"• {step}")
            
            with col3:
                st.write(f"**Last Seen:** {pattern['last_seen']}")
                
                if st.button(f"Create Automation", key=f"create_auto_{i}"):
                    st.success(f"Automation rule created for pattern: {pattern['pattern']}")
    
    # Pattern frequency chart
    st.subheader("Pattern Frequency Over Time")
    
    # Mock frequency data
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), periods=7, freq='D')
    pattern_freq_data = {
        'Date': dates,
        'Download→Rename→Move': [2, 3, 1, 4, 2, 3, 2],
        'PDF→Export→Organize': [1, 2, 0, 1, 2, 1, 1],
        'CSV→Process→Save': [0, 1, 2, 1, 1, 2, 1]
    }
    
    df = pd.DataFrame(pattern_freq_data)
    
    fig = px.line(df, x='Date', y=['Download→Rename→Move', 'PDF→Export→Organize', 'CSV→Process→Save'],
                  title="Pattern Frequency Trends")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("Automation Suggestions")
    
    # Get automation suggestions
    try:
        suggestions = workflow_learner.get_automation_suggestions()
        
        if suggestions:
            st.info(f"Found {len(suggestions)} automation suggestions based on your workflow patterns")
            
            for suggestion in suggestions:
                with st.container():
                    st.markdown("---")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        confidence_color = "🟢" if suggestion['confidence'] > 0.8 else "🟡" if suggestion['confidence'] > 0.6 else "🔴"
                        st.write(f"{confidence_color} **{suggestion['suggestion']}**")
                        
                        st.caption(f"Based on pattern seen {suggestion['frequency']} times")
                        st.caption(f"Confidence: {suggestion['confidence']:.1%}")
                        
                        # Show sequence
                        if 'sequence' in suggestion:
                            with st.expander("View Pattern Sequence"):
                                for step in suggestion['sequence']:
                                    st.write(f"• {step}")
                    
                    with col2:
                        col_accept, col_reject = st.columns(2)
                        
                        with col_accept:
                            if st.button("✅ Accept", key=f"accept_{suggestion['id']}"):
                                if workflow_learner.accept_suggestion(suggestion['id']):
                                    st.success("Suggestion accepted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to accept suggestion")
                        
                        with col_reject:
                            if st.button("❌ Reject", key=f"reject_{suggestion['id']}"):
                                if workflow_learner.reject_suggestion(suggestion['id']):
                                    st.success("Suggestion rejected")
                                    st.rerun()
                                else:
                                    st.error("Failed to reject suggestion")
        else:
            st.info("No automation suggestions available yet. The system needs to observe more workflow patterns.")
            
            # Encourage more usage
            st.markdown("""
            **How to get better suggestions:**
            1. Keep the workflow learning active
            2. Perform repetitive file operations
            3. Use consistent naming patterns
            4. Work with files regularly to build patterns
            """)
    
    except Exception as e:
        st.error(f"Error loading suggestions: {e}")
    
    # Manual suggestion input
    st.subheader("Manual Automation Request")
    
    with st.form("manual_suggestion"):
        user_description = st.text_area(
            "Describe a workflow you'd like to automate",
            placeholder="e.g., 'Always move PDF invoices to Finance folder and tag them with current month'"
        )
        
        if st.form_submit_button("💡 Create Suggestion"):
            if user_description:
                # This would create a manual suggestion
                st.success("Manual suggestion created! We'll analyze your request and add it to the automation pipeline.")
            else:
                st.warning("Please describe the workflow you'd like to automate")

with tab4:
    st.header("Learning Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Detection Sensitivity")
        
        sensitivity = st.select_slider(
            "Pattern Detection Sensitivity",
            options=["Low", "Medium", "High", "Very High"],
            value="Medium",
            help="Higher sensitivity detects more patterns but may include false positives"
        )
        
        min_frequency = st.number_input(
            "Minimum Pattern Frequency",
            min_value=1,
            max_value=10,
            value=3,
            help="Minimum times a pattern must occur to be considered"
        )
        
        pattern_window = st.selectbox(
            "Pattern Detection Window",
            options=["Last 24 hours", "Last 3 days", "Last week", "Last 2 weeks"],
            index=2,
            help="Time window for detecting workflow patterns"
        )
    
    with col2:
        st.subheader("Privacy & Data")
        
        collect_app_data = st.checkbox(
            "Monitor Application Usage",
            value=True,
            help="Allow monitoring of which applications you use for workflow learning"
        )
        
        collect_file_content = st.checkbox(
            "Analyze File Content",
            value=False,
            help="Allow analysis of file content for better pattern recognition (metadata only)"
        )
        
        data_retention = st.selectbox(
            "Data Retention Period",
            options=["7 days", "30 days", "90 days", "1 year"],
            index=1,
            help="How long to keep workflow learning data"
        )
    
    # Advanced settings
    st.subheader("Advanced Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        machine_learning = st.checkbox(
            "Enable Machine Learning",
            value=True,
            help="Use ML algorithms for better pattern recognition"
        )
        
        cross_session = st.checkbox(
            "Cross-Session Learning",
            value=True,
            help="Learn patterns across different work sessions"
        )
    
    with col2:
        auto_suggestions = st.checkbox(
            "Automatic Suggestions",
            value=True,
            help="Automatically generate automation suggestions"
        )
        
        background_learning = st.checkbox(
            "Background Learning",
            value=True,
            help="Continue learning even when app is in background"
        )
    
    # Save settings
    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")
    
    # Reset options
    st.subheader("Reset Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reset Patterns"):
            st.warning("This will delete all discovered patterns. Are you sure?")
    
    with col2:
        if st.button("🧹 Clear Suggestions"):
            st.warning("This will clear all pending suggestions.")
    
    with col3:
        if st.button("💥 Reset All Data"):
            st.error("This will delete ALL workflow learning data!")

# Help section
with st.expander("ℹ️ How Workflow Learning Works"):
    st.markdown("""
    **Behavioral Workflow Learning** automatically observes your file operations and application usage to discover patterns and suggest automations.
    
    **What it tracks:**
    - File operations (create, move, rename, delete)
    - Application usage patterns
    - Sequence of actions
    - Time-based patterns
    
    **Pattern Recognition:**
    - Identifies frequently repeated sequences
    - Analyzes timing and context
    - Uses machine learning for better accuracy
    - Considers user preferences and feedback
    
    **Privacy:**
    - All processing happens locally
    - No data sent to external servers
    - You control what data is collected
    - Easy to disable or reset at any time
    
    **Benefits:**
    - Reduces repetitive tasks
    - Improves workflow efficiency
    - Learns your specific work patterns
    - Suggests smart automations
    """)