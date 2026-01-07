"""
Main Streamlit application for Pidgin translation annotation tool.

This application provides:
- Authentication system
- Annotation workflow for testers
- Admin dashboard for progress tracking
- Concurrent user support with basic locking
"""

import streamlit as st
import os
from typing import Optional

# Import our modules
import auth
import data_loader
import persistence
import annotation_ui
import config


# Page configuration
st.set_page_config(
    page_title="Pidgin Translation Annotation Tool",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize default users on startup
if "users_initialized" not in st.session_state:
    auth.initialize_default_users()
    st.session_state["users_initialized"] = True


# Default data file path
DEFAULT_DATA_FILE = "data.jsonl"


def login_page():
    """Render the login page."""
    st.title("📝 Pidgin Translation Annotation Tool")
    st.markdown("### Please log in to continue")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login", type="primary")
        
        if submit_button:
            if auth.login(username, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    st.markdown("---")
    st.caption("")
    st.caption("please sign in")


def tester_view():
    """Render the tester/annotator view."""
    user_id = auth.get_current_user_id()
    username = auth.get_current_user()
    
    if not user_id or not username:
        st.error("Authentication error. Please log in again.")
        if st.button("Logout"):
            auth.logout()
            st.rerun()
        return
    
    st.title("📝 Annotation Workspace")
    
    # Sidebar with user info and logout
    with st.sidebar:
        st.markdown(f"**Logged in as:** {username}")
        st.markdown(f"**User ID:** {user_id}")
        
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()
        
        st.divider()
        
        # File selection
        st.markdown("### Data File")
        data_file = st.text_input(
            "JSONL file path:",
            value=DEFAULT_DATA_FILE,
            key="data_file_path"
        )
        
        if st.button("📂 Load Data", use_container_width=True):
            if os.path.exists(data_file):
                st.session_state["data_file"] = data_file
                st.session_state["records"] = None  # Force reload
                st.success("Data file selected!")
            else:
                st.error(f"File not found: {data_file}")
    
    # Get or load data file
    data_file = st.session_state.get("data_file", DEFAULT_DATA_FILE)
    
    if not os.path.exists(data_file):
        st.warning(f"⚠️ Data file not found: {data_file}")
        st.info("Please specify a valid JSONL file path in the sidebar.")
        st.markdown("""
        The JSONL file should have one JSON object per line. Supported formats:
        
        **Conversations format (recommended):**
        ```json
        {"conversations": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        ```
        
        **Legacy format:**
        ```json
        {"id": "unique_id", "source_text": "English text", "pidgin_translation": "Pidgin translation"}
        ```
        """)
        return
    
    # Load and validate data
    if "records" not in st.session_state or st.session_state.get("data_file") != data_file:
        with st.spinner("Loading data..."):
            is_valid, error_msg, records = data_loader.validate_jsonl_file(data_file)
            
            if not is_valid:
                st.error(f"Error loading data: {error_msg}")
                return
            
            st.session_state["records"] = records
            st.session_state["data_file"] = data_file
            st.success(f"✅ Loaded {len(records)} records")
    
    records = st.session_state.get("records", [])
    
    if not records:
        st.warning("No records to annotate.")
        return
    
    # Progress tracking
    progress = persistence.get_user_progress(user_id, len(records))
    
    st.markdown("### Your Overall Progress")
    annotation_ui.render_progress_bar(progress["completed"], progress["total"])
    
    # Batch assignment logic
    batch_size = config.get_batch_size()
    user_batch = persistence.get_user_batch(user_id)
    
    # Check if user needs a new batch
    if persistence.user_has_completed_batch(user_id):
        # Assign new batch
        all_record_ids = [r.get("id") for r in records]
        new_batch = persistence.assign_batch_to_user(user_id, batch_size, all_record_ids)
        if new_batch:
            user_batch = new_batch
            st.info(f"📦 You've been assigned {len(new_batch)} records to annotate!")
        else:
            # No more records available
            st.success("🎉 Congratulations! You've completed all available records.")
            if st.button("🔄 Refresh to check for new records"):
                st.session_state["current_record_id"] = None
                st.rerun()
            return
    
    # Show batch progress
    if user_batch:
        annotations = persistence.load_annotations()
        batch_completed = sum(1 for rid in user_batch 
                             if rid in annotations and annotations[rid].get("user_id") == user_id)
        batch_total = len(user_batch)
        
        st.markdown(f"### Current Batch Progress ({batch_completed}/{batch_total})")
        annotation_ui.render_progress_bar(batch_completed, batch_total)
    
    st.divider()
    
    # Get current record to annotate from user's batch
    current_record_id = st.session_state.get("current_record_id")
    current_record = None
    
    # Find next unannotated record in user's batch
    if not current_record_id or current_record_id not in user_batch:
        annotations = persistence.load_annotations()
        for record_id in user_batch:
            # Check if this record is already annotated by this user
            if record_id in annotations and annotations[record_id].get("user_id") == user_id:
                continue
            # Found an unannotated record in batch
            current_record_id = record_id
            st.session_state["current_record_id"] = current_record_id
            break
    else:
        # Current record is in batch, verify it exists
        current_record = next(
            (r for r in records if r.get("id") == current_record_id),
            None
        )
    
    # Find the record object
    if current_record_id:
        current_record = next(
            (r for r in records if r.get("id") == current_record_id),
            None
        )
    
    if not current_record:
        # All records in batch are completed, but batch check should have caught this
        st.success("🎉 You've completed your current batch!")
        if st.button("🔄 Get Next Batch"):
            persistence.clear_user_batch(user_id)
            st.session_state["current_record_id"] = None
            st.rerun()
        return
    
    # Display record number in batch and overall
    record_index_in_batch = user_batch.index(current_record_id) + 1 if current_record_id in user_batch else 0
    record_index_overall = next(
        (idx for idx, r in enumerate(records) if r.get("id") == current_record_id),
        0
    ) + 1
    st.markdown(f"### Record {record_index_in_batch} of {len(user_batch)} in batch (Overall: {record_index_overall}/{len(records)})")
    
    # Render annotation form
    annotation_data = annotation_ui.render_annotation_form(
        current_record, user_id, username
    )
    
    # Handle annotation submission
    if annotation_data is not None:
        record_id = current_record.get("id")
        
        # Save annotation (supports both old and new formats)
        persistence.save_annotation(
            record_id=record_id,
            user_id=user_id,
            username=username,
            is_correct=annotation_data["is_correct"],
            edited_translation=annotation_data.get("edited_translation"),
            edited_conversations=annotation_data.get("edited_conversations")
        )
        
        # Note: We don't release assignment immediately - it stays in the batch
        
        # Clear current record to move to next
        st.session_state["current_record_id"] = None
        
        st.success("✅ Annotation saved successfully!")
        st.balloons()
        
        # Auto-refresh to next record in batch
        st.rerun()
    
    # Navigation buttons
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("⏭️ Skip to Next Record in Batch", use_container_width=True):
            st.session_state["current_record_id"] = None
            st.rerun()


def admin_view():
    """Render the admin dashboard view."""
    username = auth.get_current_user()
    
    st.title("👑 Admin Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"**Logged in as:** {username} (Admin)")
        
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()
        
        st.divider()
        
        # File selection
        st.markdown("### Data File")
        data_file = st.text_input(
            "JSONL file path:",
            value=DEFAULT_DATA_FILE,
            key="admin_data_file_path"
        )
        
        if st.button("📂 Load Data", use_container_width=True):
            if os.path.exists(data_file):
                st.session_state["admin_data_file"] = data_file
                st.success("Data file selected!")
            else:
                st.error(f"File not found: {data_file}")
    
    # Get data file
    data_file = st.session_state.get("admin_data_file", DEFAULT_DATA_FILE)
    
    if not os.path.exists(data_file):
        st.warning(f"⚠️ Data file not found: {data_file}")
        st.info("Please specify a valid JSONL file path in the sidebar.")
        return
    
    # Load records for count
    is_valid, error_msg, records = data_loader.validate_jsonl_file(data_file)
    
    if not is_valid:
        st.error(f"Error loading data: {error_msg}")
        return
    
    total_records = len(records)
    
    # Overall progress
    st.markdown("### Overall Progress")
    all_progress = persistence.get_all_progress(total_records)
    
    if all_progress:
        # Create columns for progress cards
        cols = st.columns(min(len(all_progress), 4))
        
        for idx, (user_id, progress_data) in enumerate(all_progress.items()):
            with cols[idx % len(cols)]:
                st.metric(
                    label=progress_data.get("username", user_id),
                    value=f"{progress_data['completed']}/{progress_data['total']}",
                    delta=f"{progress_data['percentage']}%"
                )
        
        # Progress bar for all users combined
        total_completed = sum(p["completed"] for p in all_progress.values())
        st.markdown("#### Combined Progress")
        annotation_ui.render_progress_bar(total_completed, total_records)
    else:
        st.info("No annotations yet.")
    
    st.divider()
    
    # Audit trail
    st.markdown("### Annotation Audit Trail")
    annotations = persistence.load_annotations()
    
    if annotations:
        # Display annotations in a table
        annotation_list = []
        for record_id, annotation in annotations.items():
            # Check if conversations or translation was edited
            was_edited = bool(annotation.get("edited_translation") or annotation.get("edited_conversations"))
            annotation_list.append({
                "Record ID": record_id,
                "Annotator": annotation.get("username", "Unknown"),
                "Correct": "✓" if annotation.get("is_correct") else "✗",
                "Edited": "Yes" if was_edited else "No",
                "Timestamp": annotation.get("timestamp", "Unknown")
            })
        
        st.dataframe(annotation_list, use_container_width=True, hide_index=True)
    else:
        st.info("No annotations recorded yet.")
    
    st.divider()
    
    # Export functionality
    st.markdown("### Export Corrected Data")
    
    if st.button("📥 Export Corrected JSONL", type="primary"):
        # Create corrected records
        corrected_records = []
        
        for record in records:
            record_id = record.get("id")
            annotation = annotations.get(record_id)
            
            corrected_record = record.copy()
            
            # Update conversations if edited (new format)
            if annotation and annotation.get("edited_conversations"):
                corrected_record["conversations"] = annotation["edited_conversations"]
            
            # Update translation if edited (old format)
            if annotation and annotation.get("edited_translation"):
                corrected_record["pidgin_translation"] = annotation["edited_translation"]
            
            # Add annotation metadata
            if annotation:
                corrected_record["_annotation"] = {
                    "annotated_by": annotation.get("username"),
                    "is_correct": annotation.get("is_correct"),
                    "timestamp": annotation.get("timestamp")
                }
            
            corrected_records.append(corrected_record)
        
        # Export to file
        output_file = "corrected_translations.jsonl"
        data_loader.export_to_jsonl(corrected_records, output_file)
        
        st.success(f"✅ Exported {len(corrected_records)} records to {output_file}")
        
        # Provide download link
        with open(output_file, 'r', encoding='utf-8') as f:
            st.download_button(
                label="⬇️ Download Corrected JSONL",
                data=f.read(),
                file_name=output_file,
                mime="application/jsonl"
            )
    
    st.divider()
    
    # Batch Assignment Configuration
    st.markdown("### Batch Assignment Configuration")
    
    current_batch_size = config.get_batch_size()
    st.info(f"Current batch size: **{current_batch_size} records per user**")
    
    with st.form("batch_size_form"):
        new_batch_size = st.number_input(
            "Records per batch:",
            min_value=1,
            max_value=1000,
            value=current_batch_size,
            step=1,
            help="Number of records to assign to each user at a time"
        )
        
        if st.form_submit_button("💾 Update Batch Size", type="primary"):
            if config.set_batch_size(new_batch_size):
                st.success(f"✅ Batch size updated to {new_batch_size} records per user!")
                st.rerun()
            else:
                st.error("Invalid batch size. Please enter a number >= 1.")
    
    st.divider()
    
    # User management
    st.markdown("### User Management")
    
    # List all users (especially testers)
    st.markdown("#### All Users")
    all_users = auth.get_all_users()
    
    if all_users:
        # Separate admins and testers
        admins = {u: d for u, d in all_users.items() if d.get("role") == "admin"}
        testers = {u: d for u, d in all_users.items() if d.get("role") != "admin"}
        
        # Display testers with delete option
        if testers:
            st.markdown("**Testers:**")
            for tester_username, tester_data in testers.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"👤 **{tester_username}** (ID: {tester_data.get('user_id', tester_username)})")
                
                with col2:
                    # Count annotations by this user
                    annotations = persistence.load_annotations()
                    user_annotations_count = sum(
                        1 for ann in annotations.values() 
                        if ann.get("user_id") == tester_data.get("user_id", tester_username)
                    )
                    st.metric("Annotations", user_annotations_count)
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{tester_username}", use_container_width=True):
                        success, message = auth.delete_user(tester_username, username)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            st.divider()
        
        # Display admins (read-only)
        if admins:
            st.markdown("**Admins:**")
            for admin_username, admin_data in admins.items():
                st.write(f"👑 **{admin_username}** (ID: {admin_data.get('user_id', admin_username)})")
            
            st.divider()
    else:
        st.info("No users found.")
    
    # Register new user
    with st.expander("➕ Register New User"):
        with st.form("register_user"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["tester", "admin"])
            
            if st.form_submit_button("Register User"):
                success, message = auth.register_user(new_username, new_password, new_role)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def main():
    """Main application entry point."""
    # Check authentication
    if not auth.is_authenticated():
        login_page()
    else:
        # Route to appropriate view based on role
        if auth.is_admin():
            admin_view()
        else:
            tester_view()


if __name__ == "__main__":
    main()

