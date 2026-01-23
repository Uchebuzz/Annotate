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
# Import db first to initialize database connection
import db
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
    
    # Get data file from config (set by admin)
    data_file = config.get_data_file()
    
    if not os.path.exists(data_file):
        st.warning(f"⚠️ Data file not found: {data_file}")
        st.info("Please contact the administrator to set up the annotation data file.")
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
    
    records = st.session_state.get("records", [])
    
    if not records:
        st.warning("No records to annotate.")
        return
    
    # Batch assignment logic with hard limit enforcement
    batch_size = config.get_batch_size()
    
    # HARD LIMIT CHECK: Server-side validation before serving any records
    if not persistence.can_user_annotate(user_id, batch_size):
        # User has reached their limit - show completion screen
        annotation_count = persistence.get_user_annotation_count(user_id)
        st.balloons()
        st.success("🎉 Congratulations! You've completed your annotation task!")
        st.markdown("### Task Completed!")
        st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
        st.markdown("---")
        st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
        return
    
    user_batch = persistence.get_user_batch(user_id)
    
    # Check if user needs a new batch (only if they haven't reached limit)
    if persistence.user_has_completed_batch(user_id):
        # Double-check limit before assigning (server-side enforcement)
        if persistence.user_has_reached_limit(user_id, batch_size):
            # User has reached limit - show completion screen
            annotation_count = persistence.get_user_annotation_count(user_id)
            st.balloons()
            st.success("🎉 Congratulations! You've completed your annotation task!")
            st.markdown("### Task Completed!")
            st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
            st.markdown("---")
            st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
            return
        
        # Assign new batch (only if under limit)
        all_record_ids = [r.get("id") for r in records]
        new_batch = persistence.assign_batch_to_user(user_id, batch_size, all_record_ids)
        if new_batch:
            user_batch = new_batch
            st.info(f"📦 You've been assigned {len(new_batch)} records to annotate!")
            st.rerun()
        else:
            # No batch assigned (likely reached limit or no records available)
            annotation_count = persistence.get_user_annotation_count(user_id)
            if annotation_count >= batch_size:
                # Reached limit
                st.balloons()
                st.success("🎉 Congratulations! You've completed your annotation task!")
                st.markdown("### Task Completed!")
                st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
                st.markdown("---")
                st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
            else:
                # No records available
                st.info("📦 No more records available for assignment.")
            return
    
    # Ensure user has a batch assigned
    if not user_batch:
        # Check limit before assigning
        if persistence.user_has_reached_limit(user_id, batch_size):
            annotation_count = persistence.get_user_annotation_count(user_id)
            st.balloons()
            st.success("🎉 Congratulations! You've completed your annotation task!")
            st.markdown("### Task Completed!")
            st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
            return
        
        # Try to assign initial batch
        all_record_ids = [r.get("id") for r in records]
        new_batch = persistence.assign_batch_to_user(user_id, batch_size, all_record_ids)
        if new_batch:
            user_batch = new_batch
            st.info(f"📦 You've been assigned {len(new_batch)} records to annotate!")
            st.rerun()
        else:
            st.info("📦 Waiting for batch assignment...")
            st.rerun()
        return
    
    # Show batch progress only (no overall progress)
    annotations = persistence.load_annotations()
    batch_completed = sum(1 for rid in user_batch 
                         if rid in annotations and annotations[rid].get("user_id") == user_id)
    batch_total = len(user_batch)
    
    st.markdown(f"### Your Batch Progress ({batch_completed}/{batch_total})")
    annotation_ui.render_progress_bar(batch_completed, batch_total)
    
    st.divider()
    
    # HARD LIMIT CHECK: Validate before serving any record
    if not persistence.can_user_annotate(user_id, batch_size):
        annotation_count = persistence.get_user_annotation_count(user_id)
        st.balloons()
        st.success("🎉 Congratulations! You've completed your annotation task!")
        st.markdown("### Task Completed!")
        st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
        st.markdown("---")
        st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
        return
    
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
        # All records in batch are completed - check limit first
        if persistence.user_has_reached_limit(user_id, batch_size):
            # User has reached limit - show completion screen
            annotation_count = persistence.get_user_annotation_count(user_id)
            st.balloons()
            st.success("🎉 Congratulations! You've completed your annotation task!")
            st.markdown("### Task Completed!")
            st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
            st.markdown("---")
            st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
            return
        
        # Batch completed but under limit - this shouldn't happen with single batch limit
        # But handle gracefully by showing completion
        if persistence.user_has_completed_batch(user_id):
            annotation_count = persistence.get_user_annotation_count(user_id)
            st.balloons()
            st.success("🎉 Congratulations! You've completed your annotation task!")
            st.markdown("### Task Completed!")
            st.info(f"You have successfully completed {annotation_count} annotations. Thank you for your work!")
            st.markdown("---")
            st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
            return
        else:
            # This shouldn't happen, but handle gracefully
            st.info("📦 Processing batch completion...")
            st.rerun()
            return
    
    # Display record number in batch only (no overall count)
    record_index_in_batch = user_batch.index(current_record_id) + 1 if current_record_id in user_batch else 0
    st.markdown(f"### Record {record_index_in_batch} of {len(user_batch)} in your batch")
    
    # Render annotation form
    annotation_data = annotation_ui.render_annotation_form(
        current_record, user_id, username
    )
    
    # Handle annotation submission
    if annotation_data is not None:
        record_id = current_record.get("id")
        
        # HARD LIMIT ENFORCEMENT: Check before saving annotation
        if persistence.user_has_reached_limit(user_id, batch_size):
            st.error("⚠️ You have reached your annotation limit. Cannot save additional annotations.")
            st.stop()
        
        # Validate that record is in user's batch (security check)
        if record_id not in user_batch:
            st.error("⚠️ Error: This record is not in your assigned batch. Please contact an administrator.")
            st.stop()
        
        # Additional validation: Check current count before saving
        current_count = persistence.get_user_annotation_count(user_id)
        if current_count >= batch_size:
            st.error("⚠️ You have reached your annotation limit. Cannot save additional annotations.")
            st.stop()
        
        # Save annotation (supports both old and new formats)
        persistence.save_annotation(
            record_id=record_id,
            user_id=user_id,
            username=username,
            is_correct=annotation_data["is_correct"],
            edited_translation=annotation_data.get("edited_translation"),
            edited_conversations=annotation_data.get("edited_conversations")
        )
        
        # Check if limit reached after saving
        new_count = persistence.get_user_annotation_count(user_id)
        if new_count >= batch_size:
            # User has reached limit - show completion screen
            st.balloons()
            st.success("🎉 Congratulations! You've completed your annotation task!")
            st.markdown("### Task Completed!")
            st.info(f"You have successfully completed {new_count} annotations. Thank you for your work!")
            st.markdown("---")
            st.markdown("**Your annotation task is now complete. You cannot annotate additional records.**")
            # Clear current record
            st.session_state["current_record_id"] = None
            return
        
        # Note: We don't release assignment immediately - it stays in the batch
        
        # Clear current record to move to next
        st.session_state["current_record_id"] = None
        
        st.success("✅ Annotation saved successfully!")
        st.balloons()
        
        # Auto-refresh to next record in batch
        st.rerun()
    
    # Navigation buttons (only within batch)
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("⏭️ Skip to Next Record in Batch", use_container_width=True):
            st.session_state["current_record_id"] = None
            st.rerun()


def admin_view():
    """Render the admin dashboard view."""
    username = auth.get_current_user()
    
    st.title("Admin Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"**Logged in as:** {username} (Admin)")
        
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()
        
        st.divider()
        
        # File upload and selection (Admin only)
        st.markdown("### Data File Management")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload JSONL file:",
            type=['jsonl', 'json'],
            key="admin_file_upload"
        )
        
        if uploaded_file is not None:
            # Save uploaded file
            save_path = uploaded_file.name
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # Update config with new file path
            config.set_data_file(save_path)
            st.success(f"✅ File uploaded and set as data file: {save_path}")
            st.session_state["admin_data_file"] = save_path
            st.rerun()
        
        st.divider()
        
        # File path selection
        current_data_file = config.get_data_file()
        data_file = st.text_input(
            "JSONL file path:",
            value=current_data_file,
            key="admin_data_file_path"
        )
        
        if st.button("📂 Set Data File", use_container_width=True):
            if os.path.exists(data_file):
                config.set_data_file(data_file)
                st.session_state["admin_data_file"] = data_file
                st.success(f"✅ Data file set to: {data_file}")
                st.rerun()
            else:
                st.error(f"File not found: {data_file}")
    
    # Get data file from config
    data_file = config.get_data_file()
    
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_all = st.checkbox("Include all records (even unannotated)", value=False)
    
    with col2:
        export_metadata = st.checkbox("Include annotation metadata", value=True)
    
    if st.button("📥 Export Corrected JSONL", type="primary"):
        # Create corrected records
        corrected_records = []
        annotated_count = 0
        unannotated_count = 0
        
        for record in records:
            record_id = record.get("id")
            annotation = annotations.get(record_id)
            
            # Skip unannotated records if export_all is False
            if not annotation and not export_all:
                unannotated_count += 1
                continue
            
            corrected_record = record.copy()
            
            # Update conversations if edited (new format)
            if annotation and annotation.get("edited_conversations"):
                corrected_record["conversations"] = annotation["edited_conversations"]
            
            # Update translation if edited (old format)
            if annotation and annotation.get("edited_translation"):
                corrected_record["pidgin_translation"] = annotation["edited_translation"]
            
            # Add annotation metadata if requested (without timestamp)
            if annotation and export_metadata:
                corrected_record["_annotation"] = {
                    "annotated_by": annotation.get("username"),
                    "is_correct": annotation.get("is_correct")
                    # Timestamp removed per requirements - export should be clean
                }
            
            corrected_records.append(corrected_record)
            if annotation:
                annotated_count += 1
        
        # Export to file
        output_file = "corrected_translations.jsonl"
        data_loader.export_to_jsonl(corrected_records, output_file)
        
        st.success(f"✅ Exported {len(corrected_records)} records to {output_file}")
        if not export_all and unannotated_count > 0:
            st.info(f"ℹ️ {unannotated_count} unannotated records were excluded. Check 'Include all records' to include them.")
        
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
    
    # Password Management
    st.markdown("### Password Management")
    
    with st.expander("🔒 Change My Password"):
        with st.form("admin_change_password"):
            current_password = st.text_input("Current Password", type="password", key="admin_current_pass")
            new_password = st.text_input("New Password", type="password", key="admin_new_pass", help="Must be at least 6 characters")
            confirm_password = st.text_input("Confirm New Password", type="password", key="admin_confirm_pass")
            
            if st.form_submit_button("Change Password", type="primary"):
                if not new_password or len(new_password) < 6:
                    st.error("New password must be at least 6 characters long")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    success, message = auth.change_password(username, current_password, new_password)
                    if success:
                        st.success(message)
                        st.info("Password changed successfully. Please log in again.")
                        auth.logout()
                        st.rerun()
                    else:
                        st.error(message)
    
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


def password_change_page():
    """Render password change page for users who need to change their password."""
    username = auth.get_current_user()
    
    st.title("🔒 Change Password Required")
    st.warning("⚠️ You are using the default password. Please change it for security.")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password", help="Must be at least 6 characters")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submit_button = st.form_submit_button("Change Password", type="primary")
        
        if submit_button:
            if not new_password or len(new_password) < 6:
                st.error("New password must be at least 6 characters long")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            else:
                success, message = auth.change_password(username, current_password, new_password)
                if success:
                    st.success(message)
                    st.info("Please log in again with your new password.")
                    auth.logout()
                    st.rerun()
                else:
                    st.error(message)


def main():
    """Main application entry point."""
    # Check authentication
    if not auth.is_authenticated():
        login_page()
    else:
        # Check if password change is required
        username = auth.get_current_user()
        if username and auth.requires_password_change(username):
            password_change_page()
        else:
            # Route to appropriate view based on role
            if auth.is_admin():
                admin_view()
            else:
                tester_view()


if __name__ == "__main__":
    main()

