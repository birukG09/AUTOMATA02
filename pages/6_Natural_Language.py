import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="Natural Language Automation", page_icon="💬", layout="wide")

st.title("💬 Natural Language Automation")

# Initialize session state
if 'db_manager' not in st.session_state or 'config_manager' not in st.session_state:
    st.error("Managers not initialized. Please go back to the main page.")
    st.stop()

# Initialize NLP processor if not exists
if 'nlp_processor' not in st.session_state:
    try:
        from core.nlp_automation import NaturalLanguageProcessor
        st.session_state.nlp_processor = NaturalLanguageProcessor(
            st.session_state.db_manager,
            st.session_state.config_manager
        )
    except Exception as e:
        st.error(f"Error initializing NLP processor: {e}")
        st.stop()

nlp_processor = st.session_state.nlp_processor

# Initialize command history
if 'command_history' not in st.session_state:
    st.session_state.command_history = []

# Main interface
st.markdown("""
Transform your file management with plain English commands! Just tell AUTOMATA02 what you want to do, and it will understand and execute your requests.
""")

# Quick examples
with st.expander("💡 Command Examples", expanded=True):
    examples_col1, examples_col2 = st.columns(2)
    
    with examples_col1:
        st.markdown("""
        **File Organization:**
        - "Sort my downloads by type"
        - "Move all PDFs to Documents folder"
        - "Organize everything in Downloads"
        - "Put invoice files in Finance folder"
        """)
        
        st.markdown("""
        **Search & Discovery:**
        - "Find all files related to project Alpha"
        - "Show me documents from last week"
        - "Where are my Excel files?"
        - "List all invoice PDFs"
        """)
    
    with examples_col2:
        st.markdown("""
        **Automation & Rules:**
        - "Always move bank statements to Finance"
        - "Create a rule for organizing images"
        - "Automatically tag PDF documents"
        - "Set up invoice processing"
        """)
        
        st.markdown("""
        **Reports & Analysis:**
        - "Generate a weekly financial report"
        - "Show me activity insights"
        - "Create expense summary for this month"
        - "Give me productivity metrics"
        """)

# Main command interface
st.markdown("---")

# Command input with suggestions
command_input = st.text_input(
    "🎤 What would you like me to do?",
    placeholder="e.g., Sort my downloads by file type and move PDFs to Documents",
    help="Describe what you want to do in plain English"
)

# Get suggestions as user types
if len(command_input) > 3:
    suggestions = nlp_processor.get_command_suggestions(command_input)
    if suggestions:
        st.write("**Suggestions:**")
        for suggestion in suggestions[:3]:
            if st.button(f"💡 {suggestion}", key=f"suggestion_{suggestion}"):
                command_input = suggestion
                st.rerun()

# Execute command
col1, col2 = st.columns([1, 4])

with col1:
    execute_button = st.button("🚀 Execute", type="primary", disabled=not command_input)

with col2:
    if command_input:
        # Show real-time intent detection
        try:
            nlp_command = nlp_processor.process_command(command_input)
            confidence_color = "🟢" if nlp_command.confidence > 0.7 else "🟡" if nlp_command.confidence > 0.4 else "🔴"
            st.write(f"{confidence_color} **Intent:** {nlp_command.intent.replace('_', ' ').title()} ({nlp_command.confidence:.1%} confidence)")
        except:
            st.write("🔴 **Intent:** Unknown")

# Process command when button is clicked
if execute_button and command_input:
    with st.spinner("Processing your command..."):
        try:
            # Process the command
            nlp_command = nlp_processor.process_command(command_input)
            
            # Add to history
            st.session_state.command_history.insert(0, {
                'timestamp': datetime.now(),
                'command': command_input,
                'intent': nlp_command.intent,
                'confidence': nlp_command.confidence,
                'actions': nlp_command.actions
            })
            
            # Keep only last 10 commands
            st.session_state.command_history = st.session_state.command_history[:10]
            
            # Display processing results
            st.subheader("🔍 Command Analysis")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Intent Detected", nlp_command.intent.replace('_', ' ').title())
            
            with col2:
                confidence_emoji = "🟢" if nlp_command.confidence > 0.7 else "🟡" if nlp_command.confidence > 0.4 else "🔴"
                st.metric("Confidence", f"{confidence_emoji} {nlp_command.confidence:.1%}")
            
            with col3:
                st.metric("Actions Generated", len(nlp_command.actions))
            
            # Show extracted entities
            if nlp_command.entities:
                st.subheader("📋 Extracted Information")
                
                for entity_type, values in nlp_command.entities.items():
                    if values:
                        st.write(f"**{entity_type.replace('_', ' ').title()}:** {', '.join(map(str, values))}")
            
            # Execute actions
            st.subheader("⚡ Executing Actions")
            
            if nlp_command.actions:
                results = nlp_processor.execute_actions(nlp_command.actions)
                
                for i, result in enumerate(results):
                    action = result['action']
                    
                    if result['success']:
                        st.success(f"✅ {action['type'].replace('_', ' ').title()}: {result['result']}")
                        
                        # Show additional data if available
                        if 'data' in result and result['data']:
                            with st.expander(f"View Results ({len(result['data'])} items)"):
                                if action['type'] == 'search_files':
                                    # Display found files
                                    for file_info in result['data'][:10]:  # Show first 10
                                        st.write(f"📄 {file_info.get('path', 'Unknown')}")
                                else:
                                    st.json(result['data'])
                    else:
                        st.error(f"❌ {action['type'].replace('_', ' ').title()}: {result.get('error', 'Unknown error')}")
            else:
                st.warning("No actions generated. Try rephrasing your command.")
        
        except Exception as e:
            st.error(f"Error processing command: {e}")

# Command history
if st.session_state.command_history:
    st.markdown("---")
    st.subheader("📜 Recent Commands")
    
    for i, cmd_history in enumerate(st.session_state.command_history):
        with st.expander(f"{cmd_history['timestamp'].strftime('%H:%M')} - {cmd_history['command'][:50]}...", expanded=i==0):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Command:** {cmd_history['command']}")
                st.write(f"**Intent:** {cmd_history['intent'].replace('_', ' ').title()}")
                st.write(f"**Confidence:** {cmd_history['confidence']:.1%}")
                
                if cmd_history['actions']:
                    st.write("**Actions:**")
                    for action in cmd_history['actions']:
                        st.write(f"• {action['type'].replace('_', ' ').title()}")
            
            with col2:
                if st.button("🔄 Repeat", key=f"repeat_{i}"):
                    st.session_state['repeat_command'] = cmd_history['command']
                    st.rerun()

# Advanced features
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Quick Actions")
    
    if st.button("📁 Organize My Downloads"):
        st.session_state['quick_command'] = "organize everything in Downloads folder"
        st.rerun()
    
    if st.button("🔍 Find Recent Documents"):
        st.session_state['quick_command'] = "show me documents from this week"
        st.rerun()
    
    if st.button("📊 Generate Activity Report"):
        st.session_state['quick_command'] = "generate weekly activity report"
        st.rerun()
    
    if st.button("🏷️ Tag All PDFs"):
        st.session_state['quick_command'] = "automatically tag all PDF documents"
        st.rerun()

with col2:
    st.subheader("🤖 Smart Suggestions")
    
    # Show contextual suggestions based on file inventory
    try:
        recent_files = st.session_state.db_manager.get_recent_files(limit=5)
        if recent_files:
            file_types = set()
            for file in recent_files:
                if file.get('path'):
                    from pathlib import Path
                    ext = Path(file['path']).suffix.lower()
                    if ext:
                        file_types.add(ext)
            
            if file_types:
                st.write("**Based on your recent files:**")
                for ext in list(file_types)[:3]:
                    suggestion = f"Organize all {ext} files by date"
                    if st.button(f"💡 {suggestion}", key=f"smart_{ext}"):
                        st.session_state['smart_command'] = suggestion
                        st.rerun()
        else:
            st.info("No recent files found for suggestions")
    
    except Exception as e:
        st.warning("Unable to load smart suggestions")

# Handle quick/smart commands
if 'quick_command' in st.session_state:
    st.session_state['command_to_execute'] = st.session_state['quick_command']
    del st.session_state['quick_command']
    st.rerun()

if 'smart_command' in st.session_state:
    st.session_state['command_to_execute'] = st.session_state['smart_command']
    del st.session_state['smart_command']
    st.rerun()

if 'repeat_command' in st.session_state:
    st.session_state['command_to_execute'] = st.session_state['repeat_command']
    del st.session_state['repeat_command']
    st.rerun()

# Voice input simulation (placeholder)
st.markdown("---")
st.subheader("🎤 Voice Commands (Coming Soon)")

col1, col2 = st.columns([1, 3])

with col1:
    st.button("🎙️ Start Voice Input", disabled=True)

with col2:
    st.info("Voice command support will be added in a future update. For now, use text commands above.")

# Settings and configuration
with st.expander("⚙️ NLP Settings"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Language Processing")
        
        confidence_threshold = st.slider(
            "Confidence Threshold",
            min_value=0.1,
            max_value=1.0,
            value=0.6,
            step=0.1,
            help="Minimum confidence required to execute commands"
        )
        
        enable_suggestions = st.checkbox(
            "Enable Command Suggestions",
            value=True,
            help="Show command suggestions as you type"
        )
        
        case_sensitive = st.checkbox(
            "Case Sensitive Matching",
            value=False,
            help="Whether to consider case in text matching"
        )
    
    with col2:
        st.subheader("Safety & Confirmation")
        
        confirm_destructive = st.checkbox(
            "Confirm Destructive Actions",
            value=True,
            help="Ask for confirmation before deleting or moving files"
        )
        
        dry_run_mode = st.checkbox(
            "Dry Run Mode",
            value=False,
            help="Show what would be done without actually doing it"
        )
        
        max_files_per_action = st.number_input(
            "Max Files Per Action",
            min_value=1,
            max_value=1000,
            value=100,
            help="Maximum number of files to process in a single command"
        )

# Help and tips
with st.expander("💡 Tips for Better Commands"):
    st.markdown("""
    **Command Structure Tips:**
    
    1. **Be Specific:** Instead of "organize files", try "organize PDF files in Downloads by date"
    
    2. **Use Keywords:** Include words like "move", "copy", "delete", "find", "organize", "create"
    
    3. **Specify Locations:** Mention specific folders like "Downloads", "Documents", "Desktop"
    
    4. **Include File Types:** Be specific about file types like "PDF", "images", "Excel files"
    
    5. **Time References:** Use "today", "this week", "last month" for time-based operations
    
    **Supported Intents:**
    - File organization and movement
    - File search and discovery
    - Rule creation and automation
    - Report generation
    - System notifications
    - Scheduled tasks
    
    **Example Patterns:**
    - "Move [files] to [location]"
    - "Find [criteria] files"
    - "Create rule for [condition]"
    - "Generate [report type] report"
    - "Schedule [task] every [frequency]"
    """)

# Footer
st.markdown("---")
st.markdown(
    "💬 **Natural Language Automation** - Powered by advanced NLP processing and pattern recognition. "
    "Your commands are processed locally for privacy and security."
)