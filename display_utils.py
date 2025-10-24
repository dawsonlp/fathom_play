#!/usr/bin/env python3
"""
Display utilities for clean CLI output
Separates presentation logic from business logic
"""

from typing import Any, Dict, List, Optional
import json


def print_header(text: str, width: int = 60):
    """Print a section header"""
    print("=" * width)
    print(text)
    print("=" * width)


def print_subheader(text: str, width: int = 60):
    """Print a subsection header"""
    print("\n" + "=" * width)
    print(text)
    print("=" * width)


def print_success(message: str):
    """Print a success message"""
    print(f"✅ {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"❌ {message}")


def print_info(message: str):
    """Print an info message"""
    print(f"ℹ️  {message}")


def print_debug(message: str):
    """Print a debug message"""
    print(f"🔍 {message}")


def print_result(label: str, value: Any, indent: int = 2):
    """Print a result with label"""
    spaces = " " * indent
    print(f"{spaces}{label}: {value}")


def print_api_key_info(api_info: Dict[str, Any]):
    """Print API key information"""
    print_success(f"API key loaded (length: {api_info['length']})")
    print_success(f"SDK client available: {api_info['sdk_client_available']}")


def print_response_summary(result, method_name: str = "Request"):
    """Print a summary of an API response"""
    if result.success:
        print_success(f"{method_name} successful via {result.method}")
        if result.status_code:
            print_result("Status Code", result.status_code)
    else:
        print_error(f"{method_name} failed via {result.method}")
        print_result("Error", result.error)
        if result.status_code:
            print_result("Status Code", result.status_code)


def print_json_data(data: Any, indent: int = 2):
    """Print JSON data in a readable format"""
    if isinstance(data, dict) or isinstance(data, list):
        print(json.dumps(data, indent=indent))
    else:
        print(data)


def print_meeting_summary(meetings: List[Any], max_display: int = 5):
    """Print a summary of meetings"""
    count = len(meetings)
    
    if count == 0:
        print_info("No meetings found in response")
        return
    
    print_success(f"Found {count} meeting(s)")
    
    for i, meeting in enumerate(meetings[:max_display], 1):
        print(f"\n  Meeting {i}:")
        
        # Handle different meeting object types
        if hasattr(meeting, '__dict__'):
            # Object with attributes
            for attr in dir(meeting):
                if not attr.startswith('_') and not callable(getattr(meeting, attr)):
                    value = getattr(meeting, attr)
                    if value is not None:
                        if isinstance(value, str) and len(value) > 80:
                            print(f"    {attr}: {value[:80]}...")
                        else:
                            print(f"    {attr}: {value}")
        elif isinstance(meeting, dict):
            # Dictionary
            for key, value in meeting.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"    {key}: {value[:100]}...")
                else:
                    print(f"    {key}: {value}")
    
    if count > max_display:
        print(f"\n  ... and {count - max_display} more meeting(s)")


def print_test_result(test_name: str, result, show_data: bool = False):
    """Print formatted test result"""
    print_subheader(f"Test: {test_name}")
    print_response_summary(result, test_name)
    
    if result.success and show_data and result.data:
        print("\nResponse data:")
        print_json_data(result.data)


def print_filter_test(filter_name: str, result):
    """Print result of a filter test"""
    if result.success and result.data and hasattr(result.data, 'result'):
        items = result.data.result.items if result.data.result else []
        count = len(items)
        status = "🎉" if count > 0 else "  "
        print(f"{status} {filter_name}: {count} meetings")
        if count > 0:
            print(f"     Found meetings with this filter!")
    else:
        print(f"❌ {filter_name}: Error - {result.error if not result.success else 'Unknown error'}")


def print_suggestions(suggestions: List[str]):
    """Print a list of suggestions"""
    print("\n💡 Suggestions:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")


def print_completion_message():
    """Print task completion message"""
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)


def format_response_debug(response: Any) -> Dict[str, Any]:
    """Format response object for debugging"""
    debug_info = {
        "type": str(type(response)),
        "attributes": [a for a in dir(response) if not a.startswith('_')]
    }
    
    if hasattr(response, 'result'):
        result = response.result
        debug_info["result_type"] = str(type(result))
        debug_info["result_attributes"] = [a for a in dir(result) if not a.startswith('_')]
        
        if hasattr(result, 'items'):
            debug_info["items_count"] = len(result.items)
        if hasattr(result, 'limit'):
            debug_info["limit"] = result.limit
        if hasattr(result, 'next_cursor'):
            debug_info["next_cursor"] = result.next_cursor
    
    return debug_info


def print_debug_info(response: Any):
    """Print debug information about a response"""
    debug_info = format_response_debug(response)
    print("\n🔍 Debug Information:")
    for key, value in debug_info.items():
        print_result(key, value)
