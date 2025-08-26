import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import sys

st.set_page_config(page_title="Inventory", page_icon="📁", layout="wide")

st.title("📁 File Inventory")

# Initialize session state
if 'db_manager' not in st.session_state:
    st.error("Database manager not initialized. Please go back to the main page.")
    st.stop()

db_manager = st.session_state.db_manager

# Search and Filter Section
st.header("Search & Filter")

col1, col2, col3 = st.columns(3)

with col1:
    search_query = st.text_input("🔍 Search files", placeholder="Enter filename or content...")

with col2:
    # Get available labels for filter
    try:
        category_stats = db_manager.get_category_distribution()
        available_labels = ['All'] + list(category_stats.keys())
        selected_label = st.selectbox("📂 Filter by Category", available_labels)
        if selected_label == 'All':
            selected_label = None
    except:
        selected_label = st.selectbox("📂 Filter by Category", ['All'])
        if selected_label == 'All':
            selected_label = None

with col3:
    # Tags filter (simple text input for now)
    tag_filter = st.text_input("🏷️ Filter by Tags", placeholder="Enter tag name...")
    if tag_filter.strip():
        tags_list = [tag_filter.strip()]
    else:
        tags_list = None

# Results limit
col1, col2 = st.columns([3, 1])
with col2:
    results_limit = st.selectbox("Results per page", [25, 50, 100, 200], index=1)

# Search button
if st.button("🔍 Search", type="primary") or search_query or selected_label or tag_filter:
    # Perform search
    try:
        with st.spinner("Searching files..."):
            files = db_manager.search_files(
                query=search_query if search_query else None,
                label=selected_label,
                tags=tags_list,
                limit=results_limit
            )
        
        st.success(f"Found {len(files)} files")
        
        if files:
            # Convert to DataFrame for better display
            df_data = []
            for file_info in files:
                df_data.append({
                    'Filename': Path(file_info['path']).name,
                    'Category': file_info['label'],
                    'Size (KB)': round(file_info['size_bytes'] / 1024, 2) if file_info['size_bytes'] else 0,
                    'Created': file_info['created_at'][:16] if file_info['created_at'] else 'N/A',
                    'MIME Type': file_info['mime_type'] or 'Unknown',
                    'Tags': ', '.join(file_info['tags']) if file_info['tags'] else '',
                    'Path': file_info['path']
                })
            
            df = pd.DataFrame(df_data)
            
            # Display results in a table with selection
            st.header(f"Search Results ({len(files)} files)")
            
            # File details section
            selected_files = st.dataframe(
                df[['Filename', 'Category', 'Size (KB)', 'Created', 'MIME Type', 'Tags']],
                use_container_width=True,
                hide_index=True
            )
            
            # File actions section
            st.subheader("File Actions")
            
            # Select file for detailed view
            if not df.empty:
                selected_file = st.selectbox(
                    "Select file for details",
                    options=range(len(df)),
                    format_func=lambda x: df.iloc[x]['Filename']
                )
                
                if selected_file is not None:
                    file_info = files[selected_file]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("File Details")
                        st.write(f"**Full Path:** `{file_info['path']}`")
                        st.write(f"**Category:** {file_info['label']}")
                        st.write(f"**Size:** {file_info['size_bytes']:,} bytes")
                        st.write(f"**Created:** {file_info['created_at']}")
                        st.write(f"**Modified:** {file_info['modified_at']}")
                        st.write(f"**MIME Type:** {file_info['mime_type']}")
                        st.write(f"**Hash:** {file_info['hash'][:16]}..." if file_info['hash'] else "No hash")
                        
                        if file_info['tags']:
                            st.write("**Tags:**")
                            for tag in file_info['tags']:
                                st.badge(tag)
                    
                    with col2:
                        st.subheader("File Actions")
                        
                        # Check if file exists
                        file_exists = os.path.exists(file_info['path'])
                        if file_exists:
                            st.success("✅ File exists on disk")
                        else:
                            st.error("❌ File not found on disk")
                        
                        # Open containing folder button
                        if file_exists and st.button("📂 Open Containing Folder"):
                            folder_path = Path(file_info['path']).parent
                            try:
                                if os.name == 'nt':  # Windows
                                    os.startfile(str(folder_path))
                                elif os.name == 'posix':  # macOS and Linux
                                    os.system(f'open "{folder_path}"' if sys.platform == 'darwin' else f'xdg-open "{folder_path}"')
                                st.success("Opened folder in file manager")
                            except Exception as e:
                                st.error(f"Could not open folder: {e}")
                        
                        # Show metadata if available
                        if file_info['metadata']:
                            st.subheader("Metadata")
                            st.json(file_info['metadata'])
            
        else:
            st.info("No files found matching your search criteria.")
    
    except Exception as e:
        st.error(f"Error searching files: {e}")

else:
    # Show summary when no search is performed
    st.header("Inventory Summary")
    
    try:
        stats = db_manager.get_dashboard_stats()
        category_stats = db_manager.get_category_distribution()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Quick Stats")
            st.metric("Total Files", stats['total_files'])
            st.metric("Files Today", stats['files_today'])
            st.metric("Categories", stats['unique_labels'])
        
        with col2:
            st.subheader("Categories")
            if category_stats:
                for label, count in category_stats.items():
                    st.write(f"📁 **{label.title()}:** {count} files")
            else:
                st.info("No files categorized yet.")
    
    except Exception as e:
        st.error(f"Error loading inventory summary: {e}")

# Export functionality
st.markdown("---")
st.subheader("Export Inventory")

col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Export to CSV"):
        try:
            all_files = db_manager.search_files(limit=10000)  # Get all files
            if all_files:
                df_export = pd.DataFrame(all_files)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"automata02_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                st.success(f"Ready to download {len(all_files)} files")
            else:
                st.warning("No files to export")
        except Exception as e:
            st.error(f"Error exporting inventory: {e}")

with col2:
    if st.button("🔄 Refresh Inventory"):
        st.rerun()

# Help section
with st.expander("ℹ️ Help & Tips"):
    st.markdown("""
    **Search Tips:**
    - Use partial filenames to find files
    - Combine category and tag filters for precise results
    - Use the file details section to view complete information
    
    **File Management:**
    - Files are automatically organized based on your rules
    - Check the file path to see where files are stored
    - Use the "Open Containing Folder" button to locate files
    
    **Inventory Maintenance:**
    - The inventory is updated automatically when files are processed
    - Export your inventory regularly for backup purposes
    - Files marked as "not found" may have been moved or deleted outside of AUTOMATA02
    """)
