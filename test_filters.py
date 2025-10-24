#!/usr/bin/env python3
"""
Comprehensive filter testing with debug capabilities
Tests various filter combinations and date ranges
"""

from fathom_connection import FathomConnection, FathomFilters
from fathom_python.models.listmeetingsop import ListMeetingsCalendarInviteesDomainsType, MeetingType
from display_utils import (
    print_header, print_subheader, print_api_key_info,
    print_filter_test, print_error, print_meeting_summary, 
    print_result, print_success, print_completion_message
)
import sys
import argparse


def test_default_filters(conn):
    """Test default SDK filters"""
    print_subheader("Test 1: Default SDK Filters")
    print("Default filters applied:")
    print("  - calendar_invitees_domains_type=all")
    print("  - include_action_items=false")
    print("  - include_crm_matches=false")
    print("  - include_summary=false")
    print("  - include_transcript=false")
    print()
    
    result = conn.list_meetings_sdk()
    print_filter_test("Default filters", result)
    
    if result.success and result.data and result.data.result:
        print_result("Limit", result.data.result.limit)
        print_result("Next cursor", result.data.result.next_cursor)


def test_domain_filters(conn):
    """Test calendar invitee domain filters"""
    print_subheader("Test 2: Calendar Invitee Domain Filters")
    
    filters = [
        ("ONE_OR_MORE_EXTERNAL", ListMeetingsCalendarInviteesDomainsType.ONE_OR_MORE_EXTERNAL),
        ("ONLY_INTERNAL", ListMeetingsCalendarInviteesDomainsType.ONLY_INTERNAL),
    ]
    
    for name, filter_type in filters:
        result = conn.list_meetings_sdk(calendar_invitees_domains_type=filter_type)
        print_filter_test(name, result)


def test_date_range_filters(conn):
    """Test date range filters"""
    print_subheader("Test 3: Date Range Filters")
    
    date_ranges = [
        ("Last 7 days", 7),
        ("Last 30 days", 30),
        ("Last 90 days", 90),
        ("Last 365 days", 365)
    ]
    
    for name, days in date_ranges:
        filters = FathomFilters.last_n_days(days)
        print_result(name, filters['created_after'])
        result = conn.list_meetings_sdk(**filters)
        print_filter_test(name, result)
        
        # If meetings found, show sample
        if result.success and result.data and result.data.result and result.data.result.items:
            print_success(f"Found meetings! Showing first 3:")
            print_meeting_summary(result.data.result.items, max_display=3)
            print()


def test_meeting_type_filters(conn):
    """Test different meeting type filters (deprecated - shows API warning)"""
    print_subheader("Test 4: Meeting Type Filters (DEPRECATED)")
    print("⚠️  Note: meeting_type is deprecated by the Fathom API.")
    print("⚠️  Use calendar_invitees_domains_type instead (tested in Test 2).\n")
    
    # Test with meeting_type but WITHOUT calendar_invitees_domains_type to avoid conflict
    print("Testing meeting_type parameter in isolation:")
    for meeting_type in [MeetingType.ALL, MeetingType.INTERNAL, MeetingType.EXTERNAL]:
        # Must set calendar_invitees_domains_type to None to use meeting_type
        result = conn.list_meetings_sdk(
            meeting_type=meeting_type,
            calendar_invitees_domains_type=None
        )
        print_filter_test(f"meeting_type={meeting_type}", result)


def test_combined_filters(conn):
    """Test combined filter patterns"""
    print_subheader("Test 5: Combined Filter Patterns")
    
    # External meetings from last 30 days with details
    print("\n🔧 External meetings (last 30 days) with full details:")
    filters = {
        **FathomFilters.last_n_days(30),
        **FathomFilters.external_meetings(),
        **FathomFilters.with_details()
    }
    print_result("Filters applied", list(filters.keys()))
    result = conn.list_meetings_sdk(**filters)
    print_filter_test("Combined: External + Last 30 days + Details", result)
    
    # Internal meetings only
    print("\n🔧 Internal meetings only:")
    filters = FathomFilters.internal_meetings()
    print_result("Filters applied", list(filters.keys()))
    result = conn.list_meetings_sdk(**filters)
    print_filter_test("Internal meetings only", result)


def test_no_filters(conn):
    """Test with all filters set to None"""
    print_subheader("Test 6: Bypass All Default Filters")
    print("Setting all filters to None to bypass defaults\n")
    
    result = conn.list_meetings_sdk(
        calendar_invitees_domains_type=None,
        include_action_items=None,
        include_crm_matches=None,
        include_summary=None,
        include_transcript=None
    )
    print_filter_test("No filters (all None)", result)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Test Fathom API filters')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to see HTTP requests')
    args = parser.parse_args()
    
    print_header("Fathom.ai Comprehensive Filter Testing")
    
    # Initialize connection (with optional debug mode)
    try:
        conn = FathomConnection(debug=args.debug)
        api_info = conn.get_api_key_info()
        print_api_key_info(api_info)
        
        if args.debug:
            print_success("Debug mode enabled - HTTP requests will be logged")
        
        print()
    except Exception as e:
        print_error(f"ERROR: {e}")
        sys.exit(1)
    
    # Run all filter tests
    test_default_filters(conn)
    test_domain_filters(conn)
    test_date_range_filters(conn)
    test_meeting_type_filters(conn)
    test_combined_filters(conn)
    test_no_filters(conn)
    
    print_completion_message()
    
    if args.debug:
        print("\n💡 Tip: Review the HTTP request logs above to see exactly what was sent to the API")

if __name__ == "__main__":
    main()
