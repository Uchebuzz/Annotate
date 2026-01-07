"""
Data loading module for handling JSONL input files.

This module handles:
- Loading JSONL files safely
- Validating data structure
- Providing data access methods
"""

import json
import os
import hashlib
from typing import List, Dict, Optional, Tuple


def load_jsonl(file_path: str) -> List[Dict]:
    """
    Load a JSONL file and return a list of dictionaries.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        List of dictionaries, one per line
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Invalid JSON on line {line_num}: {e.msg}",
                    e.doc,
                    e.pos
                )
    
    return records


def validate_record(record: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate that a record has the required fields.
    
    Supports two formats:
    1. Old format: id, source_text, pidgin_translation
    2. New format: conversations (array of {role, content})
    
    Args:
        record: Dictionary to validate
        
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    # Check for new conversations format
    if "conversations" in record:
        conversations = record.get("conversations", [])
        if not isinstance(conversations, list):
            return False, "conversations must be a list"
        if len(conversations) == 0:
            return False, "conversations list cannot be empty"
        
        for idx, conv in enumerate(conversations):
            if not isinstance(conv, dict):
                return False, f"conversation {idx} must be a dictionary"
            if "role" not in conv or "content" not in conv:
                return False, f"conversation {idx} must have 'role' and 'content' fields"
            if conv.get("role") not in ["user", "assistant"]:
                return False, f"conversation {idx} role must be 'user' or 'assistant'"
        
        return True, None
    
    # Check for old format (backward compatibility)
    required_fields = ["id", "source_text", "pidgin_translation"]
    if all(field in record for field in required_fields):
        return True, None
    
    return False, "Record must have either 'conversations' field or 'id', 'source_text', 'pidgin_translation' fields"


def generate_record_id(record: Dict, index: int) -> str:
    """
    Generate a unique ID for a record.
    
    Uses existing ID if present, otherwise generates one from content.
    
    Args:
        record: Record dictionary
        index: Index of the record in the file
        
    Returns:
        Unique ID string
    """
    # If record already has an ID, use it
    if "id" in record:
        return str(record["id"])
    
    # Generate ID from content hash
    content_str = json.dumps(record, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.md5(content_str.encode('utf-8')).hexdigest()[:12]
    return f"record_{index}_{content_hash}"


def normalize_record(record: Dict, index: int) -> Dict:
    """
    Normalize a record to ensure it has an ID and is in a consistent format.
    
    Args:
        record: Record dictionary
        index: Index of the record in the file
        
    Returns:
        Normalized record with 'id' field
    """
    normalized = record.copy()
    
    # Generate ID if missing
    if "id" not in normalized:
        normalized["id"] = generate_record_id(record, index)
    
    return normalized


def validate_jsonl_file(file_path: str) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Load and validate a JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        
    Returns:
        (is_valid: bool, error_message: Optional[str], records: List[Dict])
    """
    try:
        records = load_jsonl(file_path)
        
        if not records:
            return False, "File is empty or contains no valid records", []
        
        # Validate each record and normalize
        invalid_records = []
        normalized_records = []
        for idx, record in enumerate(records):
            is_valid, error_msg = validate_record(record)
            if not is_valid:
                invalid_records.append((idx, error_msg))
            else:
                # Normalize record (ensure it has an ID)
                normalized = normalize_record(record, idx)
                normalized_records.append(normalized)
        
        if invalid_records:
            error_details = ", ".join([f"record {idx}: {msg}" for idx, msg in invalid_records])
            return False, f"Validation errors: {error_details}", normalized_records
        
        return True, None, normalized_records
    
    except FileNotFoundError as e:
        return False, str(e), []
    except json.JSONDecodeError as e:
        return False, str(e), []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def export_to_jsonl(records: List[Dict], output_path: str) -> None:
    """
    Export a list of records to a JSONL file.
    
    Args:
        records: List of dictionaries to export
        output_path: Path to output file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

