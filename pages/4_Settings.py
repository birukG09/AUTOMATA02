import streamlit as st
import os
import sys
from pathlib import Path

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")

# Initialize session state
if 'config_manager' not in st.session_state:
    st.error("Configuration manager not initialized. Please go back to the main page.")
    st.stop()

config_manager = st.session_state.config_manager

# Get current configuration
config = config_manager.get_config()

# Settings tabs
tab1, tab2, tab3, tab4 = st.tabs(["📁 File Watching", "📂 Organization", "🔧 System", "📊 Advanced"])

with tab1:
    st.subheader("File Watching Configuration")
    
    # Watch paths
    st.write("**Folders to Monitor**")
    current_paths = config_manager.get_watch_paths()
    
    # Display current watch paths
    for i, path in enumerate(current_paths):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            path_exists = os.path.exists(path)
            status_icon = "✅" if path_exists else "❌"
            st.write(f"{status_icon} `{path}`")
        
        with col2:
            if st.button("📂", key=f"browse_{i}", help="Browse folder"):
                st.info("Use the text input below to modify paths")
        
        with col3:
            if st.button("🗑️", key=f"remove_path_{i}", help="Remove path"):
                new_paths = current_paths.copy()
                del new_paths[i]
                config_manager.set_watch_paths(new_paths)
                st.success("Path removed!")
                st.rerun()
    
    # Add new watch path
    st.write("**Add New Watch Path**")
    with st.form("add_watch_path"):
        new_path = st.text_input("Folder Path", placeholder=str(Path.home() / "Desktop"))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("➕ Add Path", type="primary"):
                if new_path and os.path.exists(new_path):
                    current_paths.append(new_path)
                    config_manager.set_watch_paths(current_paths)
                    st.success("Watch path added!")
                    st.rerun()
                elif new_path:
                    st.error("Path does not exist")
                else:
                    st.error("Please enter a path")
        
        with col2:
            # Common path shortcuts
            common_paths = [
                ("Downloads", str(Path.home() / "Downloads")),
                ("Desktop", str(Path.home() / "Desktop")),
                ("Documents", str(Path.home() / "Documents"))
            ]
            
            selected_common = st.selectbox("Quick Add", 
                                         options=["Select..."] + [p[0] for p in common_paths])
            
            if selected_common != "Select...":
                path_to_add = next(p[1] for p in common_paths if p[0] == selected_common)
                if st.form_submit_button("Add Selected"):
                    if path_to_add not in current_paths:
                        current_paths.append(path_to_add)
                        config_manager.set_watch_paths(current_paths)
                        st.success(f"Added {selected_common} folder!")
                        st.rerun()
                    else:
                        st.warning("Path already being watched")

with tab2:
    st.subheader("File Organization Settings")
    
    # Base organization path
    current_base_path = config_manager.get_organize_base_path()
    
    with st.form("organization_settings"):
        st.write("**Base Organization Folder**")
        st.caption("This is where organized files will be moved to")
        
        new_base_path = st.text_input("Base Path", value=current_base_path)
        
        if st.form_submit_button("💾 Save Organization Path"):
            try:
                # Create directory if it doesn't exist
                if new_base_path:
                    Path(new_base_path).mkdir(parents=True, exist_ok=True)
                config_manager.set_organize_base_path(new_base_path)
                st.success("Organization path updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error setting organization path: {e}")
    
    # Organization structure preview
    st.write("**Organization Structure Preview**")
    try:
        from core.organizer import FileOrganizer
        
        organizer = FileOrganizer(st.session_state.db_manager, config_manager)
        
        if st.button("🏗️ Create Organization Folders"):
            try:
                created_folders = organizer.create_organized_structure(current_base_path)
                st.success("Organization folders created!")
                for category, path in created_folders.items():
                    st.write(f"✅ {category}: `{path}`")
            except Exception as e:
                st.error(f"Error creating folders: {e}")
        
        # Show what the structure would look like
        st.write("**Folder Structure:**")
        base_path = Path(current_base_path)
        structure = [
            "📁 Finance/",
            "📁 Documents/",
            "📁 Media/",
            "📁 Code/",
            "📁 Archives/",
            "📁 Other/"
        ]
        
        for folder in structure:
            st.write(f"`{base_path}/` {folder}")
    
    except Exception as e:
        st.error(f"Error loading organization settings: {e}")

with tab3:
    st.subheader("System Settings")
    
    # Database information
    st.write("**Database Information**")
    db_manager = st.session_state.get('db_manager')
    if db_manager:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Database Path:** `{db_manager.db_path}`")
            if db_manager.test_connection():
                st.success("✅ Database Connected")
            else:
                st.error("❌ Database Connection Failed")
        
        with col2:
            try:
                stats = db_manager.get_dashboard_stats()
                st.metric("Total Files in DB", stats['total_files'])
            except:
                st.warning("Could not load database stats")
    
    # Logging settings
    st.write("**Logging Configuration**")
    current_log_level = config.get('logging', {}).get('level', 'INFO')
    log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    
    with st.form("logging_settings"):
        selected_level = st.selectbox("Log Level", 
                                     options=log_levels,
                                     index=log_levels.index(current_log_level))
        
        if st.form_submit_button("💾 Save Logging Settings"):
            config['logging'] = config.get('logging', {})
            config['logging']['level'] = selected_level
            config_manager.save_config(config)
            st.success("Logging settings saved!")
    
    # System information
    st.write("**System Information**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Home Directory:** `{Path.home()}`")
        st.write(f"**Config Directory:** `{config_manager.config_dir}`")
    
    with col2:
        st.write(f"**Python Version:** {sys.version}")
        st.write(f"**Platform:** {os.name}")

with tab4:
    st.subheader("Advanced Settings")
    
    # Configuration file editor
    st.write("**Raw Configuration Editor**")
    st.warning("⚠️ Advanced users only. Incorrect configuration may cause issues.")
    
    with st.expander("📝 Edit Raw Configuration"):
        import yaml
        
        config_text = st.text_area(
            "Configuration (YAML)",
            value=yaml.safe_dump(config, default_flow_style=False),
            height=300
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Raw Config", type="primary"):
                try:
                    new_config = yaml.safe_load(config_text)
                    config_manager.save_config(new_config)
                    st.success("Configuration saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid YAML: {e}")
        
        with col2:
            if st.button("🔄 Reset to Default"):
                if st.session_state.get('confirm_reset', False):
                    # Reset to defaults (would need implementation)
                    st.warning("Reset functionality not implemented yet")
                else:
                    st.session_state['confirm_reset'] = True
                    st.warning("Click again to confirm reset")
    
    # Export/Import configuration
    st.write("**Configuration Backup**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Export Configuration**")
        if st.button("📤 Export Config"):
            import yaml
            config_yaml = yaml.safe_dump(config, default_flow_style=False)
            st.download_button(
                label="Download config.yaml",
                data=config_yaml,
                file_name="automata02_config.yaml",
                mime="text/yaml"
            )
    
    with col2:
        st.write("**Import Configuration**")
        uploaded_config = st.file_uploader("Choose config file", type=['yaml', 'yml'])
        if uploaded_config is not None:
            try:
                import yaml
                imported_config = yaml.safe_load(uploaded_config)
                if st.button("📥 Import Config (Replace)", type="secondary"):
                    config_manager.save_config(imported_config)
                    st.success("Configuration imported!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error importing config: {e}")
    
    # System maintenance
    st.write("**System Maintenance**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh All Data"):
            # Clear session state to refresh all managers
            for key in list(st.session_state.keys()):
                if isinstance(key, str) and key.startswith(('db_manager', 'config_manager', 'file_watcher')):
                    del st.session_state[key]
            st.success("System refreshed! Please reload the page.")
    
    with col2:
        if st.button("🧹 Clear Activity Log"):
            try:
                # Would need implementation to clear activity log
                st.info("Activity log clearing not implemented yet")
            except Exception as e:
                st.error(f"Error clearing log: {e}")

# Footer with version info
st.markdown("---")
st.markdown("**AUTOMATA02 v1.0.0** - Intelligent Workspace Automation Hub")
st.caption("Configuration changes take effect immediately. Restart the file watcher if needed.")
