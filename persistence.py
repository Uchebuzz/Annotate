"""
Persistence module for managing annotations and concurrent access.

This module handles:
- Saving annotations to disk
- Loading annotations
- Managing record assignments to prevent conflicts
- Tracking progress per user
"""

import json
import os
import time
from typing import Dict, List, Optional, Set
from datetime import datetime


ANNOTATIONS_FILE = "annotations.json"
ASSIGNMENTS_FILE = "assignments.json"
BATCH_ASSIGNMENTS_FILE = "batch_assignments.json"  # Track which records belong to user's current batch
LOCK_TIMEOUT = 300  # 5 minutes in seconds


def load_json_file(file_path: str, default: Dict) -> Dict:
    """Load a JSON file, returning default if it doesn't exist."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default.copy()
    return default.copy()


def save_json_file(file_path: str, data: Dict) -> None:
    """Save data to a JSON file atomically."""
    # Write to temporary file first, then rename (atomic on most systems)
    temp_path = file_path + ".tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, file_path)


def load_annotations() -> Dict:
    """
    Load annotations from disk.
    
    Structure:
    {
        "record_id": {
            "user_id": str,
            "is_correct": bool,
            "edited_translation": Optional[str],  # For old format
            "edited_conversations": Optional[List[Dict]],  # For new format
            "timestamp": str,
            "username": str
        }
    }
    """
    return load_json_file(ANNOTATIONS_FILE, {})


def save_annotation(record_id: str, user_id: str, username: str, 
                   is_correct: bool, edited_translation: Optional[str] = None,
                   edited_conversations: Optional[List[Dict]] = None) -> None:
    """
    Save an annotation for a record.
    
    Args:
        record_id: ID of the record being annotated
        user_id: ID of the user making the annotation
        username: Username of the annotator
        is_correct: Whether the translation/conversations are correct
        edited_translation: The edited translation (for old format, if correction was made)
        edited_conversations: The edited conversations array (for new format, if correction was made)
    """
    annotations = load_annotations()
    
    annotation_data = {
        "user_id": user_id,
        "username": username,
        "is_correct": is_correct,
        "timestamp": datetime.now().isoformat()
    }
    
    # Support both old and new formats
    if edited_conversations is not None:
        annotation_data["edited_conversations"] = edited_conversations
    if edited_translation is not None:
        annotation_data["edited_translation"] = edited_translation
    
    annotations[record_id] = annotation_data
    
    save_json_file(ANNOTATIONS_FILE, annotations)


def get_annotation(record_id: str) -> Optional[Dict]:
    """Get annotation for a specific record."""
    annotations = load_annotations()
    return annotations.get(record_id)


def load_assignments() -> Dict:
    """
    Load record assignments from disk.
    
    Structure:
    {
        "record_id": {
            "user_id": str,
            "timestamp": float (Unix timestamp)
        }
    }
    """
    return load_json_file(ASSIGNMENTS_FILE, {})


def save_assignments(assignments: Dict) -> None:
    """Save assignments to disk."""
    save_json_file(ASSIGNMENTS_FILE, assignments)


def assign_record(record_id: str, user_id: str) -> bool:
    """
    Assign a record to a user if it's not already assigned or assignment expired.
    
    Returns:
        True if assignment successful, False if already assigned to another user
    """
    assignments = load_assignments()
    current_time = time.time()
    
    # Check if record is already assigned
    if record_id in assignments:
        assignment = assignments[record_id]
        assignment_time = assignment.get("timestamp", 0)
        
        # If assignment is still valid and assigned to different user
        if (current_time - assignment_time < LOCK_TIMEOUT and 
            assignment.get("user_id") != user_id):
            return False
        
        # If assignment expired, allow reassignment
        if current_time - assignment_time >= LOCK_TIMEOUT:
            # Remove expired assignment
            del assignments[record_id]
    
    # Assign to current user
    assignments[record_id] = {
        "user_id": user_id,
        "timestamp": current_time
    }
    
    save_assignments(assignments)
    return True


def release_assignment(record_id: str, user_id: str) -> None:
    """Release an assignment for a record (usually after annotation is complete)."""
    assignments = load_assignments()
    
    if record_id in assignments and assignments[record_id].get("user_id") == user_id:
        del assignments[record_id]
        save_assignments(assignments)


def load_batch_assignments() -> Dict:
    """
    Load batch assignments from disk.
    
    Structure:
    {
        "user_id": {
            "batch_record_ids": List[str],  # Records in current batch
            "timestamp": float
        }
    }
    """
    return load_json_file(BATCH_ASSIGNMENTS_FILE, {})


def save_batch_assignments(batch_assignments: Dict) -> None:
    """Save batch assignments to disk."""
    save_json_file(BATCH_ASSIGNMENTS_FILE, batch_assignments)


def assign_batch_to_user(user_id: str, batch_size: int, all_record_ids: List[str]) -> List[str]:
    """
    Assign a batch of records to a user.
    
    Enforces hard limit: users can only receive ONE batch. If they've already
    completed their batch, no new batch will be assigned.
    
    Args:
        user_id: User ID to assign batch to
        batch_size: Number of records to assign
        all_record_ids: List of all available record IDs
        
    Returns:
        List of record IDs assigned to the user (may be less than batch_size if not enough available).
        Returns empty list if user has already reached their limit.
    """
    # HARD LIMIT: Check if user has already completed their allocation
    if user_has_reached_limit(user_id, batch_size):
        return []  # User has reached limit, no new batch
    
    assignments = load_assignments()
    annotations = load_annotations()
    batch_assignments = load_batch_assignments()
    current_time = time.time()
    
    # Check if user already has a batch assigned
    if user_id in batch_assignments:
        existing_batch = batch_assignments[user_id].get("batch_record_ids", [])
        # If user has an incomplete batch, don't assign a new one
        if existing_batch:
            # Check if batch is complete
            batch_complete = all(
                record_id in annotations and annotations[record_id].get("user_id") == user_id
                for record_id in existing_batch
            )
            if not batch_complete:
                return []  # User already has an incomplete batch
    
    # Get records not yet annotated by anyone (to prevent repeated batches)
    available_records = []
    for record_id in all_record_ids:
        # Skip if already annotated by anyone (prevents repeated batches)
        if record_id in annotations:
            continue
        
        # Check if assigned to another user (and not expired)
        if record_id in assignments:
            assignment = assignments[record_id]
            assignment_time = assignment.get("timestamp", 0)
            assigned_user = assignment.get("user_id")
            
            # Skip if assigned to another user and not expired
            if (assigned_user != user_id and 
                current_time - assignment_time < LOCK_TIMEOUT):
                continue
        
        available_records.append(record_id)
    
    # Take up to batch_size records
    batch_record_ids = available_records[:batch_size]
    
    # Assign each record to the user
    for record_id in batch_record_ids:
        assignments[record_id] = {
            "user_id": user_id,
            "timestamp": current_time
        }
    
    # Save batch assignment tracking
    batch_assignments[user_id] = {
        "batch_record_ids": batch_record_ids,
        "timestamp": current_time
    }
    
    save_assignments(assignments)
    save_batch_assignments(batch_assignments)
    
    return batch_record_ids


def get_user_batch(user_id: str) -> List[str]:
    """
    Get the list of record IDs in the user's current batch.
    
    Returns:
        List of record IDs in current batch, empty list if no batch assigned
    """
    batch_assignments = load_batch_assignments()
    if user_id in batch_assignments:
        return batch_assignments[user_id].get("batch_record_ids", [])
    return []


def user_has_completed_batch(user_id: str) -> bool:
    """
    Check if user has completed all records in their current batch.
    
    Returns:
        True if batch is complete (all records annotated) or no batch exists, False otherwise
    """
    batch_record_ids = get_user_batch(user_id)
    if not batch_record_ids:
        return True  # No batch = considered "complete" (needs new batch)
    
    annotations = load_annotations()
    
    # Check if all records in batch are annotated by this user
    for record_id in batch_record_ids:
        if record_id not in annotations or annotations[record_id].get("user_id") != user_id:
            return False
    
    return True


def can_user_annotate(user_id: str, batch_size: int) -> bool:
    """
    Check if a user can still annotate (hasn't reached their limit).
    
    This is a server-side validation that should be called before serving
    any new records to a tester.
    
    Args:
        user_id: User ID to check
        batch_size: The batch size limit
        
    Returns:
        True if user can still annotate, False if they've reached their limit
    """
    # Check if user has reached their hard limit
    if user_has_reached_limit(user_id, batch_size):
        return False
    
    # Check if user has a batch and if it's complete
    batch_record_ids = get_user_batch(user_id)
    if not batch_record_ids:
        # No batch assigned yet - can annotate if under limit
        return True
    
    # Has a batch - check if it's complete
    return not user_has_completed_batch(user_id)


def clear_user_batch(user_id: str) -> None:
    """Clear the user's current batch assignment."""
    batch_assignments = load_batch_assignments()
    if user_id in batch_assignments:
        del batch_assignments[user_id]
        save_batch_assignments(batch_assignments)


def get_assigned_records(user_id: str) -> Set[str]:
    """Get set of record IDs assigned to a specific user."""
    assignments = load_assignments()
    current_time = time.time()
    
    assigned = set()
    for record_id, assignment in assignments.items():
        assignment_time = assignment.get("timestamp", 0)
        if (assignment.get("user_id") == user_id and 
            current_time - assignment_time < LOCK_TIMEOUT):
            assigned.add(record_id)
    
    return assigned


def get_user_annotation_count(user_id: str) -> int:
    """
    Get the total number of annotations completed by a user.
    
    Args:
        user_id: User ID to check
        
    Returns:
        Total number of annotations completed by this user
    """
    annotations = load_annotations()
    return sum(1 for ann in annotations.values() if ann.get("user_id") == user_id)


def user_has_reached_limit(user_id: str, batch_size: int) -> bool:
    """
    Check if a user has reached their annotation limit (one batch).
    
    Args:
        user_id: User ID to check
        batch_size: The batch size limit
        
    Returns:
        True if user has completed batch_size or more annotations, False otherwise
    """
    annotation_count = get_user_annotation_count(user_id)
    return annotation_count >= batch_size


def get_user_progress(user_id: str, total_records: int) -> Dict:
    """
    Get progress statistics for a user.
    
    Returns:
        {
            "completed": int,
            "total": int,
            "percentage": float
        }
    """
    annotations = load_annotations()
    completed = sum(1 for ann in annotations.values() if ann.get("user_id") == user_id)
    
    percentage = (completed / total_records * 100) if total_records > 0 else 0
    
    return {
        "completed": completed,
        "total": total_records,
        "percentage": round(percentage, 1)
    }


def get_all_progress(total_records: int) -> Dict[str, Dict]:
    """
    Get progress statistics for all users.
    
    Returns:
        {
            "user_id": {
                "completed": int,
                "total": int,
                "percentage": float
            }
        }
    """
    annotations = load_annotations()
    user_counts = {}
    
    for annotation in annotations.values():
        user_id = annotation.get("user_id")
        if user_id:
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
    
    progress = {}
    # Build user_id to username mapping
    user_to_username = {}
    for annotation in annotations.values():
        user_id = annotation.get("user_id")
        username = annotation.get("username")
        if user_id and username and user_id not in user_to_username:
            user_to_username[user_id] = username
    
    for user_id, completed in user_counts.items():
        percentage = (completed / total_records * 100) if total_records > 0 else 0
        progress[user_id] = {
            "completed": completed,
            "total": total_records,
            "percentage": round(percentage, 1),
            "username": user_to_username.get(user_id, user_id)
        }
    
    return progress


def get_unassigned_record_ids(all_record_ids: List[str], user_id: str) -> List[str]:
    """
    Get list of record IDs that are not assigned or assigned to the current user.
    
    Args:
        all_record_ids: List of all record IDs
        user_id: Current user ID
        
    Returns:
        List of unassigned record IDs
    """
    assignments = load_assignments()
    annotations = load_annotations()
    current_time = time.time()
    
    unassigned = []
    for record_id in all_record_ids:
        # Skip if already annotated by this user
        if record_id in annotations and annotations[record_id].get("user_id") == user_id:
            continue
        
        # Check assignment
        if record_id not in assignments:
            unassigned.append(record_id)
        else:
            assignment = assignments[record_id]
            assignment_time = assignment.get("timestamp", 0)
            
            # Include if expired or assigned to this user
            if (current_time - assignment_time >= LOCK_TIMEOUT or
                assignment.get("user_id") == user_id):
                unassigned.append(record_id)
    
    return unassigned

