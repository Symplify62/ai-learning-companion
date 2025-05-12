"""
Transcript Parsing Utilities
"""
import re
from typing import List, Dict, Any, Optional

def _convert_timestamp_to_seconds(time_str: str) -> Optional[float]:
    """
    Converts a timestamp string (HH:MM:SS or MM:SS) to total seconds.
    Returns None if the format is invalid.
    """
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 3:  # HH:MM:SS
        return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
    elif len(parts) == 2:  # MM:SS
        return float(parts[0] * 60 + parts[1])
    else:
        return None # Invalid format

def parse_raw_transcript_to_segments(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parses raw transcript text containing timestamps into a list of segments.

    Each segment is a dictionary: {"startTimeSeconds": float, "text": str}

    Supported timestamp formats at the beginning of a line:
    - [HH:MM:SS]
    - (HH:MM:SS)
    - HH:MM:SS
    - MM:SS
    """
    segments: List[Dict[str, Any]] = []
    lines = raw_text.strip().split('\\n')
    
    # Regex to capture timestamps and the rest of the line
    # It tries to match HH:MM:SS first, then MM:SS
    # It handles optional brackets or parentheses around the timestamp.
    # It also captures the text immediately following the timestamp on the same line.
    timestamp_pattern = re.compile(
        r"^(?:[(\[]?(\d{1,2}:\d{2}:\d{2})[)\]]?|(\d{1,2}:\d{2}))\\s*(.*)"
    )

    current_segment_text_lines: List[str] = []
    current_start_time: Optional[float] = 0.0 # Default for first segment if no initial timestamp

    for line in lines:
        match = timestamp_pattern.match(line)
        if match:
            # A new timestamp is found
            if current_segment_text_lines: # Finalize previous segment
                segments.append({
                    "startTimeSeconds": current_start_time if current_start_time is not None else 0.0,
                    "text": " ".join(current_segment_text_lines).strip()
                })
                current_segment_text_lines = []

            # Determine which group matched for the timestamp
            ts_str = match.group(1) if match.group(1) else match.group(2)
            current_start_time = _convert_timestamp_to_seconds(ts_str)
            
            # Text on the same line as the timestamp
            remaining_line_text = match.group(3)
            if remaining_line_text:
                current_segment_text_lines.append(remaining_line_text.strip())
            
            if current_start_time is None: # Should not happen if regex matches
                print(f"Warning: Could not parse timestamp string: {ts_str} from line: {line}")
                # Fallback: Treat as text for the current/previous segment
                if segments: # Append to previous segment's text
                    segments[-1]["text"] += f"\\n{line.strip()}"
                else: # Or start a new segment with default time
                    current_segment_text_lines.append(line.strip())
                    current_start_time = 0.0 # Reset for safety
        else:
            # No timestamp on this line, append to current segment's text
            current_segment_text_lines.append(line.strip())

    # Add the last segment
    if current_segment_text_lines:
        segments.append({
            "startTimeSeconds": current_start_time if current_start_time is not None else 0.0,
            "text": " ".join(current_segment_text_lines).strip()
        })
    
    if not segments and raw_text.strip(): # If no timestamps were found at all, treat as one segment
        return [{"startTimeSeconds": 0.0, "text": raw_text.strip()}]
        
    return segments

if __name__ == '__main__':
    # Example Usage and Basic Tests
    test_transcript_1 = """
    [00:00:01] Hello this is the first line.
    This is a continuation of the first segment.
    (00:00:05) Now we are at the second segment.
    00:00:08 And this is the third segment.
    More text for the third segment.
    00:10 This is the fourth segment, with MM:SS format.
    """
    
    test_transcript_2 = "Just a plain text without any timestamps."
    
    test_transcript_3 = """
    [00:00:00] Start.
    [00:00:02] Middle.
    [00:00:04] End.
    """

    test_transcript_4 = """Invalid line then
    [00:00:01] Valid segment.
    Another line for valid segment."""

    test_transcript_5 = """
    [00:00:01]First part.
    Second part of first segment.
    (00:00:05)Second segment.
    00:00:08 Third segment
    with multiple lines.
    00:10 Fourth segment.
    """


    print("--- Test Transcript 1 ---")
    parsed_segments_1 = parse_raw_transcript_to_segments(test_transcript_1)
    for seg in parsed_segments_1:
        print(seg)

    print("\\n--- Test Transcript 2 ---")
    parsed_segments_2 = parse_raw_transcript_to_segments(test_transcript_2)
    for seg in parsed_segments_2:
        print(seg)
        
    print("\\n--- Test Transcript 3 ---")
    parsed_segments_3 = parse_raw_transcript_to_segments(test_transcript_3)
    for seg in parsed_segments_3:
        print(seg)

    print("\\n--- Test Transcript 4 ---")
    parsed_segments_4 = parse_raw_transcript_to_segments(test_transcript_4)
    for seg in parsed_segments_4:
        print(seg)
    
    print("\\n--- Test Transcript 5 (from user) ---")
    parsed_segments_5 = parse_raw_transcript_to_segments(test_transcript_5)
    for seg in parsed_segments_5:
        print(seg)

    # Test with only MM:SS
    test_transcript_6 = """
    00:05 First bit.
    00:10 Second bit.
    Text for second bit.
    """
    print("\\n--- Test Transcript 6 (MM:SS only) ---")
    parsed_segments_6 = parse_raw_transcript_to_segments(test_transcript_6)
    for seg in parsed_segments_6:
        print(seg)

    test_transcript_7 = """
    [00:00:00] This is the actual start of the video.
    Some more speech.
    [00:00:05] Now we transition to a new topic.
    This topic is interesting.
    It has multiple lines.
    [00:00:12] End of the discussion for now.
    """
    print("\\n--- Test Transcript 7 (Multi-line segments) ---")
    parsed_segments_7 = parse_raw_transcript_to_segments(test_transcript_7)
    for seg in parsed_segments_7:
        print(seg) 