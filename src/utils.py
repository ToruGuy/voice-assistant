#!/usr/bin/env python3
"""
Utility functions for the Voice Assistant application.
"""
from src.config import logger


def chunk_text_for_tts(text, buffer="", min_chunk_size=200):
    """Split text into appropriate chunks for text-to-speech processing.
    
    This simplified function accumulates text and breaks at natural phrase
    boundaries like punctuation marks. It prioritizes natural-sounding speech
    by only breaking at commas, periods, etc.
    
    Args:
        text (str): New text to process
        buffer (str, optional): Existing text buffer to append to. Defaults to "".
        min_chunk_size (int, optional): Minimum characters before processing. Defaults to 50.
    
    Returns:
        tuple: (chunk_to_process, remaining_buffer)
            - chunk_to_process: Text ready for TTS processing (None if no complete chunk)
            - remaining_buffer: Text to keep buffering for next call
    """
    # Add new text to existing buffer
    current_buffer = buffer + text
    
    # Very short text should always be buffered, not processed yet
    if len(current_buffer) < min_chunk_size:
        return None, current_buffer
    
    # Natural break points in order of priority
    break_points = [
        ".\n", "!\n", "?\n",  # End of sentence with newline (highest priority)
        ". ", "! ", "? ",     # End of sentence with space
        ".\t", "!\t", "?\t",  # End of sentence with tab
        ".", "!", "?",        # End of sentence without space
        ":\n", ": ", ":",     # Colons
        ";\n", "; ", ";",     # Semicolons
        ",\n", ", ", ","      # Commas (lowest priority)
    ]
    
    # Try to find a natural break point in the text
    for bp in break_points:
        idx = current_buffer.rfind(bp)
        # Only consider if the break point creates a substantial chunk
        if idx >= min_chunk_size:
            # Check if it's part of a common abbreviation
            if bp in [". ", ".", ".\n"]:
                abbreviations = ["dr", "mr", "ms", "jr", "sr", "np", "itp", "itd", "prof"]
                is_abbreviation = False
                for abbr in abbreviations:
                    if (idx >= len(abbr) and 
                        current_buffer[idx-len(abbr):idx].lower() == abbr):
                        is_abbreviation = True
                        break
                
                if is_abbreviation:
                    continue
            
            # We found a good breaking point
            end_pos = idx + len(bp)
            chunk = current_buffer[:end_pos]
            remaining = current_buffer[end_pos:]
            return chunk, remaining
    
    # If we have a lot of accumulated text but no good break point was found,
    # find the last space to avoid breaking mid-word
    if len(current_buffer) > 2000:
        last_space = current_buffer.rfind(" ")
        if last_space > min_chunk_size:
            return current_buffer[:last_space+1], current_buffer[last_space+1:]
    
    # No good break point found, keep buffering
    return None, current_buffer
