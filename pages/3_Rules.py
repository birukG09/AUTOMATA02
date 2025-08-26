import streamlit as st
import json
from typing import Dict, Any, List

st.set_page_config(page_title="Rules", page_icon="⚙️", layout="wide")

st.title("⚙️ Organization Rules")

# Initialize session state
if 'config_manager' not in st.session_state:
    st.error("Configuration manager not initialized. Please go back to the main page.")
    st.stop()

config_manager = st.session_state.config_manager

# Rule management section
st.header("Rule Management")

# Get current rules
rules = config_manager.get_rules()

# Tabs for different rule operations
tab1, tab2, tab3 = st.tabs(["📋 View Rules", "➕ Add Rule", "🧪 Test Rules"])

with tab1:
    st.subheader("Current Rules")
    
    if rules:
        for i, rule in enumerate(rules):
            with st.expander(f"Rule {i+1}: {rule['name']}", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write("**Conditions (When):**")
                    when_conditions = rule.get('when', {})
                    for key, value in when_conditions.items():
                        st.write(f"- {key}: `{value}`")
                    
                    st.write("**Actions (Then):**")
                    then_actions = rule.get('then', {})
                    for key, value in then_actions.items():
                        st.write(f"- {key}: `{value}`")
                
                with col2:
                    st.write(f"**Priority:** {rule.get('priority', 100)}")
                    st.write(f"**Active:** {'✅ Yes' if rule.get('active', True) else '❌ No'}")
                    
                    # Edit rule button
                    if st.button(f"✏️ Edit", key=f"edit_rule_{i}"):
                        st.session_state[f'editing_rule_{i}'] = True
                        st.rerun()
                
                with col3:
                    # Delete rule button
                    if st.button(f"🗑️ Delete", key=f"delete_rule_{i}", type="secondary"):
                        if st.session_state.get(f'confirm_delete_{i}', False):
                            if config_manager.delete_rule(i):
                                st.success("Rule deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete rule")
                        else:
                            st.session_state[f'confirm_delete_{i}'] = True
                            st.warning("Click again to confirm deletion")
                
                # Edit form
                if st.session_state.get(f'editing_rule_{i}', False):
                    st.subheader(f"Edit Rule: {rule['name']}")
                    
                    with st.form(f"edit_rule_form_{i}"):
                        # Basic info
                        rule_name = st.text_input("Rule Name", value=rule['name'])
                        rule_priority = st.number_input("Priority", value=rule.get('priority', 100), min_value=1, max_value=1000)
                        rule_active = st.checkbox("Active", value=rule.get('active', True))
                        
                        # Conditions
                        st.subheader("Conditions (When)")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            filename_regex = st.text_input("Filename Regex", value=when_conditions.get('filename_regex', ''))
                            mime_startswith = st.text_input("MIME Type Starts With", value=when_conditions.get('mime_startswith', ''))
                            path_regex = st.text_input("Path Regex", value=when_conditions.get('path_regex', ''))
                        
                        with col2:
                            mime_in = st.text_input("MIME Types (comma-separated)", value=', '.join(when_conditions.get('mime_in', [])))
                            size_lt = st.number_input("Size Less Than (bytes)", value=when_conditions.get('size_lt_bytes', 0), min_value=0)
                            size_gt = st.number_input("Size Greater Than (bytes)", value=when_conditions.get('size_gt_bytes', 0), min_value=0)
                        
                        # Actions
                        st.subheader("Actions (Then)")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            label = st.selectbox(
                                "Label/Category", 
                                options=['finance', 'documents', 'media', 'code', 'archives', 'other'],
                                index=['finance', 'documents', 'media', 'code', 'archives', 'other'].index(then_actions.get('label', 'other'))
                            )
                            tags_add = st.text_input("Tags to Add (comma-separated)", value=', '.join(then_actions.get('tags_add', [])))
                        
                        with col2:
                            move_to = st.text_input("Move To Path", value=then_actions.get('move_to', ''))
                            rename_to = st.text_input("Rename To", value=then_actions.get('rename_to', ''))
                        
                        # Form buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes", type="primary"):
                                # Build updated rule
                                updated_rule = {
                                    'name': rule_name,
                                    'priority': rule_priority,
                                    'active': rule_active,
                                    'when': {},
                                    'then': {}
                                }
                                
                                # Add conditions
                                if filename_regex:
                                    updated_rule['when']['filename_regex'] = filename_regex
                                if mime_startswith:
                                    updated_rule['when']['mime_startswith'] = mime_startswith
                                if path_regex:
                                    updated_rule['when']['path_regex'] = path_regex
                                if mime_in:
                                    updated_rule['when']['mime_in'] = [m.strip() for m in mime_in.split(',') if m.strip()]
                                if size_lt > 0:
                                    updated_rule['when']['size_lt_bytes'] = size_lt
                                if size_gt > 0:
                                    updated_rule['when']['size_gt_bytes'] = size_gt
                                
                                # Add actions
                                updated_rule['then']['label'] = label
                                if tags_add:
                                    updated_rule['then']['tags_add'] = [t.strip() for t in tags_add.split(',') if t.strip()]
                                if move_to:
                                    updated_rule['then']['move_to'] = move_to
                                if rename_to:
                                    updated_rule['then']['rename_to'] = rename_to
                                
                                if config_manager.update_rule(i, updated_rule):
                                    st.success("Rule updated successfully!")
                                    st.session_state[f'editing_rule_{i}'] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to update rule")
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f'editing_rule_{i}'] = False
                                st.rerun()
    else:
        st.info("No rules configured yet. Add a rule using the 'Add Rule' tab.")

with tab2:
    st.subheader("Add New Rule")
    
    with st.form("add_rule_form"):
        # Basic info
        rule_name = st.text_input("Rule Name*", placeholder="e.g., 'PDF Invoices to Finance'")
        rule_priority = st.number_input("Priority", value=100, min_value=1, max_value=1000, 
                                       help="Lower numbers run first")
        rule_active = st.checkbox("Active", value=True)
        
        # Conditions
        st.subheader("Conditions (When)")
        st.markdown("*Specify when this rule should apply. Leave empty for conditions you don't need.*")
        
        col1, col2 = st.columns(2)
        
        with col1:
            filename_regex = st.text_input("Filename Regex", placeholder="e.g., invoice|bill|statement")
            mime_startswith = st.text_input("MIME Type Starts With", placeholder="e.g., image/")
            path_regex = st.text_input("Path Regex", placeholder="e.g., /Downloads/.*")
        
        with col2:
            mime_in = st.text_input("MIME Types (comma-separated)", placeholder="e.g., application/pdf, text/plain")
            size_lt = st.number_input("Size Less Than (bytes)", value=0, min_value=0)
            size_gt = st.number_input("Size Greater Than (bytes)", value=0, min_value=0)
        
        # Actions
        st.subheader("Actions (Then)")
        st.markdown("*Specify what should happen when conditions match.*")
        
        col1, col2 = st.columns(2)
        
        with col1:
            label = st.selectbox("Label/Category*", 
                                options=['finance', 'documents', 'media', 'code', 'archives', 'other'])
            tags_add = st.text_input("Tags to Add (comma-separated)", 
                                    placeholder="e.g., invoice, pdf, important")
        
        with col2:
            move_to = st.text_input("Move To Path", 
                                   placeholder="e.g., {{HOME}}/AutomataOrganized/Finance/{{YYYY}}")
            rename_to = st.text_input("Rename To", placeholder="Optional rename pattern")
        
        # Help section
        with st.expander("💡 Template Variables Help"):
            st.markdown("""
            **Date Variables:**
            - `{{YYYY}}` - 4-digit year (e.g., 2024)
            - `{{MM}}` - 2-digit month (e.g., 03)
            - `{{DD}}` - 2-digit day (e.g., 15)
            - `{{HH}}` - 2-digit hour (e.g., 14)
            - `{{mm}}` - 2-digit minute (e.g., 30)
            - `{{ss}}` - 2-digit second (e.g., 45)
            
            **File Variables:**
            - `{{BASENAME}}` - Full filename with extension
            - `{{STEM}}` - Filename without extension
            - `{{EXT}}` - File extension including dot
            
            **Path Variables:**
            - `{{HOME}}` - User's home directory
            
            **Examples:**
            - `{{HOME}}/Documents/{{YYYY}}/{{MM}}/`
            - `{{HOME}}/AutomataOrganized/{{LABEL}}/{{YYYY}}/`
            """)
        
        # Form submit
        if st.form_submit_button("➕ Add Rule", type="primary"):
            if not rule_name:
                st.error("Rule name is required")
            else:
                # Build new rule
                new_rule = {
                    'name': rule_name,
                    'priority': rule_priority,
                    'active': rule_active,
                    'when': {},
                    'then': {'label': label}
                }
                
                # Add conditions
                if filename_regex:
                    new_rule['when']['filename_regex'] = filename_regex
                if mime_startswith:
                    new_rule['when']['mime_startswith'] = mime_startswith
                if path_regex:
                    new_rule['when']['path_regex'] = path_regex
                if mime_in:
                    new_rule['when']['mime_in'] = [m.strip() for m in mime_in.split(',') if m.strip()]
                if size_lt > 0:
                    new_rule['when']['size_lt_bytes'] = size_lt
                if size_gt > 0:
                    new_rule['when']['size_gt_bytes'] = size_gt
                
                # Add actions
                if tags_add:
                    new_rule['then']['tags_add'] = [t.strip() for t in tags_add.split(',') if t.strip()]
                if move_to:
                    new_rule['then']['move_to'] = move_to
                if rename_to:
                    new_rule['then']['rename_to'] = rename_to
                
                if config_manager.add_rule(new_rule):
                    st.success("Rule added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add rule")

with tab3:
    st.subheader("Test Rules")
    st.markdown("Test your rules against sample files to see how they would be classified.")
    
    # Test file input
    test_file_path = st.text_input("Test File Path", 
                                  placeholder="/home/user/Downloads/invoice_2024_01.pdf")
    
    if test_file_path and st.button("🧪 Test Classification"):
        try:
            # Import classifier and test
            from core.classifier import FileClassifier
            
            classifier = FileClassifier(config_manager)
            result = classifier.classify_file(test_file_path)
            
            st.subheader("Classification Result")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Label:** {result['label']}")
                st.write(f"**Confidence:** {result['confidence']:.2f}")
                st.write(f"**MIME Type:** {result['mime_type']}")
                if result['tags']:
                    st.write("**Tags:**")
                    for tag in result['tags']:
                        st.badge(tag)
            
            with col2:
                if result.get('rule_matched'):
                    st.success(f"✅ Matched Rule: {result['rule_matched']}")
                else:
                    st.info("ℹ️ Used fallback classification")
                
                if result.get('move_to'):
                    st.write(f"**Would Move To:** {result['move_to']}")
                
                if result.get('metadata'):
                    with st.expander("Metadata"):
                        st.json(result['metadata'])
        
        except Exception as e:
            st.error(f"Error testing classification: {e}")
    
    # Dry run organizer test
    st.markdown("---")
    st.subheader("Test File Organization (Dry Run)")
    
    org_test_file = st.text_input("File Path to Test Organization", 
                                 placeholder="/home/user/Downloads/document.pdf")
    
    if org_test_file and st.button("🔍 Test Organization"):
        try:
            from core.classifier import FileClassifier
            from core.organizer import FileOrganizer
            
            classifier = FileClassifier(config_manager)
            organizer = FileOrganizer(st.session_state.db_manager, config_manager)
            
            # Classify file
            classification = classifier.classify_file(org_test_file)
            
            # Test organization (dry run)
            dry_run_result = organizer.dry_run_organize(org_test_file, classification)
            
            st.subheader("Organization Test Result")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Source:** `{dry_run_result['source']}`")
                st.write(f"**Label:** {dry_run_result['label']}")
                if dry_run_result['tags']:
                    st.write("**Tags:** " + ", ".join(dry_run_result['tags']))
            
            with col2:
                if dry_run_result['would_move']:
                    st.success("✅ File would be moved")
                    st.write(f"**Destination:** `{dry_run_result['destination']}`")
                    if dry_run_result.get('destination_exists'):
                        st.warning("⚠️ Destination already exists (would add suffix)")
                else:
                    st.info("ℹ️ File would stay in place")
                
                if dry_run_result.get('rule_matched'):
                    st.write(f"**Rule:** {dry_run_result['rule_matched']}")
            
            if dry_run_result.get('error'):
                st.error(f"Error: {dry_run_result['error']}")
        
        except Exception as e:
            st.error(f"Error testing organization: {e}")

# Import/Export rules
st.markdown("---")
st.subheader("Import/Export Rules")

col1, col2 = st.columns(2)

with col1:
    st.write("**Export Rules**")
    if st.button("📤 Export Rules to JSON"):
        rules_json = json.dumps(rules, indent=2)
        st.download_button(
            label="Download rules.json",
            data=rules_json,
            file_name="automata02_rules.json",
            mime="application/json"
        )

with col2:
    st.write("**Import Rules**")
    uploaded_file = st.file_uploader("Choose rules JSON file", type=['json'])
    if uploaded_file is not None:
        try:
            imported_rules = json.load(uploaded_file)
            if isinstance(imported_rules, list):
                if st.button("📥 Import Rules (Replace All)", type="secondary"):
                    config_manager.save_rules(imported_rules)
                    st.success(f"Imported {len(imported_rules)} rules successfully!")
                    st.rerun()
            else:
                st.error("Invalid rules file format")
        except Exception as e:
            st.error(f"Error importing rules: {e}")

# Help section
with st.expander("ℹ️ Rules Help"):
    st.markdown("""
    **Rule Priority:**
    - Rules are evaluated in order of priority (lower numbers first)
    - If multiple rules match, only the first matching rule is applied
    - Set important rules with lower priority numbers
    
    **Condition Matching:**
    - All specified conditions must match for a rule to apply
    - Leave conditions empty if you don't need them
    - Regular expressions are case-insensitive
    
    **File Organization:**
    - Files are moved according to the "Move To Path" setting
    - Use template variables for dynamic paths
    - Files are renamed if conflicts exist (adds _1, _2, etc.)
    
    **Best Practices:**
    - Test rules before enabling them
    - Use specific conditions to avoid unwanted matches
    - Organize rules by priority for predictable behavior
    - Keep rule names descriptive for easy management
    """)
