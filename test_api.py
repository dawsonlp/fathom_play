#!/usr/bin/env python3
"""
Comprehensive API testing for Fathom.ai
Tests both SDK and REST API methods with clean interface
"""

from fathom_connection import FathomConnection
from display_utils import (
    print_header, print_subheader, print_api_key_info,
    print_response_summary, print_result, print_suggestions,
    print_error, print_json_data, print_meeting_summary,
    print_debug_info, print_completion_message
)
import sys


def test_connection_and_api_key(conn):
    """Test connection and display API key information"""
    print_header("Fathom.ai API Connection Test")
    api_info = conn.get_api_key_info()
    print_api_key_info(api_info)
    print()
    
    # Show API key details
    print_subheader("API Key Information")
    print_result("API Key starts with", api_info['prefix'])
    print_result("API Key length", api_info['length'])
    print_result("SDK Client Available", api_info['sdk_client_available'])
    print()


def test_teams_both_methods(conn):
    """Test listing teams with both SDK and REST methods"""
    print_subheader("Test: List Teams - Both Methods")
    
    # Test SDK
    print("\n📊 SDK Method:")
    teams_sdk = conn.list_teams_sdk()
    print_response_summary(teams_sdk, "List Teams SDK")
    
    if teams_sdk.success and hasattr(teams_sdk.data, 'teams'):
        teams = teams_sdk.data.teams
        print_result("Teams count", len(teams))
        for i, team in enumerate(teams, 1):
            print(f"\n  Team {i}:")
            print_result("Name", team.name if hasattr(team, 'name') else 'N/A', indent=4)
            print_result("ID", team.id if hasattr(team, 'id') else 'N/A', indent=4)
    
    # Test REST
    print("\n📊 REST Method:")
    teams_rest = conn.list_teams_rest()
    print_response_summary(teams_rest, "List Teams REST")
    
    if teams_rest.success and teams_rest.data:
        print("\nResponse:")
        print_json_data(teams_rest.data)
    
    # Test Combined (with automatic fallback)
    print("\n📊 Combined Method (auto-fallback):")
    teams_combined = conn.list_teams()
    print_response_summary(teams_combined, "List Teams Combined")
    print_result("Method used", teams_combined.method)


def test_meetings_both_methods(conn):
    """Test listing meetings with both SDK and REST methods"""
    print_subheader("Test: List Meetings - Both Methods")
    
    # Test SDK with debug info
    print("\n📊 SDK Method:")
    meetings_sdk = conn.list_meetings_sdk()
    print_response_summary(meetings_sdk, "List Meetings SDK")
    
    if meetings_sdk.success and meetings_sdk.data:
        print_debug_info(meetings_sdk.data)
        
        if hasattr(meetings_sdk.data, 'result') and hasattr(meetings_sdk.data.result, 'items'):
            meetings = meetings_sdk.data.result.items
            print_meeting_summary(meetings, max_display=3)
            
            if len(meetings) == 0:
                print_result("Next cursor", meetings_sdk.data.result.next_cursor if hasattr(meetings_sdk.data.result, 'next_cursor') else 'N/A')
                print_result("Limit", meetings_sdk.data.result.limit if hasattr(meetings_sdk.data.result, 'limit') else 'N/A')
    
    # Test REST
    print("\n📊 REST Method:")
    meetings_rest = conn.list_meetings_rest()
    print_response_summary(meetings_rest, "List Meetings REST")
    
    if meetings_rest.success and meetings_rest.data:
        print("\nResponse:")
        print_json_data(meetings_rest.data)
        
        if 'items' in meetings_rest.data:
            items = meetings_rest.data.get('items', [])
            print()
            print_meeting_summary(items, max_display=3)


def show_suggestions():
    """Display helpful suggestions for API usage"""
    print_subheader("Suggestions & Next Steps")
    
    suggestions = [
        "Check your Fathom account settings to verify:\n   - Which account/workspace this API key belongs to\n   - What permissions/scopes the API key has\n   - If the key has 'read meetings' permission",
        "Try creating a new API key with full permissions",
        "Verify you're logged into the correct Fathom account",
        "Use test_filters.py to test various filter combinations",
        "Enable debug mode: FathomConnection(debug=True) to see HTTP requests"
    ]
    print_suggestions(suggestions)


def main():
    # Initialize connection
    try:
        conn = FathomConnection()
    except Exception as e:
        print_error(f"ERROR: {e}")
        print("\nPlease add your API key to ~/.env:")
        print("  FATHOM_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # Run all tests
    test_connection_and_api_key(conn)
    test_teams_both_methods(conn)
    test_meetings_both_methods(conn)
    show_suggestions()
    
    print_completion_message()


if __name__ == "__main__":
    main()
