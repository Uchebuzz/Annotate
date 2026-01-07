"""
Annotation UI module for the annotation workflow.

This module handles:
- Displaying records for annotation
- Handling user input and validation
- Managing the annotation flow
"""

import streamlit as st
from typing import Dict, Optional, List
import persistence


def render_annotation_form(record: Dict, user_id: str, username: str) -> Optional[Dict]:
    """
    Render the annotation form for a single record.
    
    Supports both formats:
    1. Old format: id, source_text, pidgin_translation
    2. New format: id, conversations (array of {role, content})
    
    Args:
        record: Dictionary containing record data
        user_id: Current user ID
        username: Current username
        
    Returns:
        Dictionary with annotation data if submitted, None otherwise
        {
            "is_correct": bool,
            "edited_translation": Optional[str],  # For old format
            "edited_conversations": Optional[List[Dict]]  # For new format
        }
    """
    record_id = record.get("id", "")
    
    # Check if this is the new conversations format
    if "conversations" in record:
        return render_conversations_form(record, record_id, user_id, username)
    else:
        return render_old_format_form(record, record_id, user_id, username)


def render_conversations_form(record: Dict, record_id: str, user_id: str, username: str) -> Optional[Dict]:
    """
    Render annotation form for conversations format.
    
    Args:
        record: Record with conversations array
        record_id: Record ID
        user_id: Current user ID
        username: Current username
        
    Returns:
        Annotation data dict if submitted, None otherwise
    """
    conversations = record.get("conversations", [])
    
    st.markdown("### Conversation Messages")
    
    # Check if there's an existing annotation
    existing_annotation = persistence.get_annotation(record_id)
    if existing_annotation and existing_annotation.get("user_id") == user_id:
        st.success(f"✓ Previously annotated by you at {existing_annotation.get('timestamp', 'unknown time')}")
        if existing_annotation.get("edited_conversations"):
            display_conversations = existing_annotation["edited_conversations"]
        else:
            display_conversations = conversations
    else:
        display_conversations = conversations
    
    # Store original conversations for comparison
    original_conversations_json = str(conversations)
    
    # Display and allow editing of each conversation message
    edited_conversations = []
    
    for idx, conv in enumerate(display_conversations):
        role = conv.get("role", "")
        content = conv.get("content", "")
        
        # Role badge
        if role == "user":
            st.markdown(f"#### 👤 User Message {idx + 1}")
            role_color = "🔵"
        else:
            st.markdown(f"#### 🤖 Assistant Message {idx + 1}")
            role_color = "🟢"
        
        # Editable text area for each message
        edited_content = st.text_area(
            f"Edit {role} message:",
            value=content,
            height=100,
            key=f"conv_{record_id}_{idx}",
            label_visibility="collapsed"
        )
        
        edited_conversations.append({
            "role": role,
            "content": edited_content.strip()
        })
        
        # Add divider between messages (but not after the last one)
        if idx < len(display_conversations) - 1:
            st.divider()
    
    st.divider()
    
    # Correctness question
    st.markdown("### Is this conversation correct?")
    
    # Radio button for correctness
    is_correct = st.radio(
        "Select your answer:",
        ["Yes", "No"],
        key=f"correctness_{record_id}",
        horizontal=True
    )
    
    is_correct_bool = (is_correct == "Yes")
    
    # Validation: If "No", require that at least one message was edited
    if not is_correct_bool:
        # Compare edited conversations with original
        edited_conversations_json = str(edited_conversations)
        if edited_conversations_json == original_conversations_json:
            st.warning("⚠️ Please edit at least one message since you marked the conversation as incorrect.")
            st.stop()
    
    st.divider()
    
    # Submit button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("💾 Save Annotation", type="primary", key=f"submit_{record_id}", use_container_width=True):
            # Validate input - ensure all messages have content
            all_valid = True
            for idx, conv in enumerate(edited_conversations):
                if not conv["content"].strip():
                    st.error(f"Message {idx + 1} ({conv['role']}) cannot be empty!")
                    all_valid = False
            
            if not all_valid:
                st.stop()
            
            # Return annotation data
            return {
                "is_correct": is_correct_bool,
                "edited_conversations": edited_conversations if not is_correct_bool else None
            }
    
    return None


def render_old_format_form(record: Dict, record_id: str, user_id: str, username: str) -> Optional[Dict]:
    """
    Render annotation form for old format (source_text, pidgin_translation).
    
    Args:
        record: Record with source_text and pidgin_translation
        record_id: Record ID
        user_id: Current user ID
        username: Current username
        
    Returns:
        Annotation data dict if submitted, None otherwise
    """
    source_text = record.get("source_text", "")
    current_translation = record.get("pidgin_translation", "")
    
    # Display source text (read-only)
    st.subheader("Source Text")
    st.info(source_text)
    
    st.divider()
    
    # Display current translation
    st.subheader("Current Pidgin Translation")
    
    # Check if there's an existing annotation
    existing_annotation = persistence.get_annotation(record_id)
    if existing_annotation and existing_annotation.get("user_id") == user_id:
        # Show existing annotation
        st.success(f"✓ Previously annotated by you at {existing_annotation.get('timestamp', 'unknown time')}")
        if existing_annotation.get("edited_translation"):
            display_translation = existing_annotation["edited_translation"]
        else:
            display_translation = current_translation
    else:
        display_translation = current_translation
    
    # Editable text area for translation
    edited_translation = st.text_area(
        "Edit translation if needed:",
        value=display_translation,
        height=150,
        key=f"translation_{record_id}",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Correctness question
    st.subheader("Is this translation correct?")
    
    # Radio button for correctness
    is_correct = st.radio(
        "Select your answer:",
        ["Yes", "No"],
        key=f"correctness_{record_id}",
        horizontal=True
    )
    
    is_correct_bool = (is_correct == "Yes")
    
    # Validation: If "No", require that translation was edited
    if not is_correct_bool:
        if edited_translation.strip() == current_translation.strip():
            st.warning("⚠️ Please edit the translation since you marked it as incorrect.")
            st.stop()
    
    st.divider()
    
    # Submit button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("💾 Save Annotation", type="primary", key=f"submit_{record_id}", use_container_width=True):
            # Validate input
            if not edited_translation.strip():
                st.error("Translation cannot be empty!")
                st.stop()
            
            # Return annotation data
            return {
                "is_correct": is_correct_bool,
                "edited_translation": edited_translation.strip() if not is_correct_bool else None
            }
    
    return None


def render_progress_bar(completed: int, total: int) -> None:
    """
    Render a progress bar showing annotation progress.
    
    Args:
        completed: Number of completed items
        total: Total number of items
    """
    if total == 0:
        st.progress(0.0)
        st.caption("No items to annotate")
        return
    
    progress = completed / total
    st.progress(progress)
    st.caption(f"{completed} of {total} completed ({progress * 100:.1f}%)")


def get_next_record_to_annotate(records: list[Dict], user_id: str) -> Optional[Dict]:
    """
    Get the next record that should be annotated by the user.
    
    Returns the first record that:
    - Has not been annotated by this user
    - Is not currently assigned to another user
    """
    annotations = persistence.load_annotations()
    assignments = persistence.load_assignments()
    
    import time
    current_time = time.time()
    
    for record in records:
        record_id = record.get("id")
        
        # Skip if already annotated by this user
        if record_id in annotations:
            if annotations[record_id].get("user_id") == user_id:
                continue
        
        # Check if assigned to another user
        if record_id in assignments:
            assignment = assignments[record_id]
            assignment_time = assignment.get("timestamp", 0)
            assigned_user = assignment.get("user_id")
            
            # Skip if assigned to another user and not expired
            if (assigned_user != user_id and 
                current_time - assignment_time < persistence.LOCK_TIMEOUT):
                continue
        
        # This record is available
        return record
    
    return None
