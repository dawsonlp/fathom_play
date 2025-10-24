#!/usr/bin/env python3
"""
Unified Fathom.ai connection class that provides both SDK and REST API access
without CLI display code mixed in.
"""

import os
import sys
import requests
import httpx
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from datetime import datetime

from fathom_python import Fathom
from fathom_python.models.security import Security
from fathom_python.models.listmeetingsop import ListMeetingsCalendarInviteesDomainsType, MeetingType
from dotenv import load_dotenv


@dataclass
class FathomResponse:
    """Standardized response format for both SDK and REST results"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    method: str = "unknown"  # 'sdk' or 'rest'
    status_code: Optional[int] = None


class DebugTransport(httpx.BaseTransport):
    """Transport that logs requests for debugging"""
    
    def __init__(self, transport: httpx.BaseTransport, debug: bool = False):
        self.transport = transport
        self.debug = debug
    
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.debug:
            print(f"DEBUG: {request.method} {request.url}")
            for key, value in request.headers.items():
                if 'auth' in key.lower() or 'key' in key.lower():
                    print(f"  {key}: {value[:20]}..." if len(value) > 20 else f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
        
        return self.transport.handle_request(request)


class FathomConnection:
    """
    Unified connection class for Fathom.ai API access via both SDK and REST.
    Separates business logic from display code.
    """
    
    def __init__(self, api_key: Optional[str] = None, debug: bool = False):
        """
        Initialize Fathom connection with both SDK and REST clients.
        
        Args:
            api_key: Fathom API key. If None, loads from ~/.env
            debug: Enable debug logging for requests
        """
        self.debug = debug
        self.api_key = self._load_api_key(api_key)
        self.base_url = "https://api.fathom.ai/external/v1"
        
        # Initialize SDK client
        self.sdk_client = self._init_sdk_client()
        
        # Initialize REST client
        self.rest_headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
    
    def _load_api_key(self, api_key: Optional[str]) -> str:
        """Load API key from parameter or environment"""
        if api_key:
            return api_key
        
        env_path = os.path.expanduser('~/.env')
        load_dotenv(env_path)
        
        api_key = os.getenv('FATHOM_API_KEY')
        if not api_key:
            raise ValueError("FATHOM_API_KEY not found in ~/.env or provided as parameter")
        
        return api_key
    
    def _init_sdk_client(self) -> Optional[Fathom]:
        """Initialize the Fathom SDK client"""
        try:
            if self.debug:
                # Use debug transport for SDK
                base_transport = httpx.HTTPTransport()
                debug_transport = DebugTransport(base_transport, debug=True)
                debug_client = httpx.Client(transport=debug_transport, follow_redirects=True)
                
                return Fathom(
                    security=Security(api_key_auth=self.api_key),
                    client=debug_client
                )
            else:
                return Fathom(security=Security(api_key_auth=self.api_key))
        except Exception as e:
            if self.debug:
                print(f"Failed to initialize SDK client: {e}")
            return None
    
    # SDK Methods
    def list_teams_sdk(self) -> FathomResponse:
        """List teams using SDK"""
        if not self.sdk_client:
            return FathomResponse(
                success=False,
                error="SDK client not initialized",
                method="sdk"
            )
        
        try:
            response = self.sdk_client.list_teams()
            return FathomResponse(
                success=True,
                data=response,
                method="sdk"
            )
        except Exception as e:
            return FathomResponse(
                success=False,
                error=str(e),
                method="sdk"
            )
    
    def list_meetings_sdk(self, **filters) -> FathomResponse:
        """
        List meetings using SDK with optional filters.
        
        Args:
            **filters: SDK filter parameters like calendar_invitees_domains_type,
                      meeting_type, created_after, etc.
        """
        if not self.sdk_client:
            return FathomResponse(
                success=False,
                error="SDK client not initialized",
                method="sdk"
            )
        
        try:
            response = self.sdk_client.list_meetings(**filters)
            return FathomResponse(
                success=True,
                data=response,
                method="sdk"
            )
        except Exception as e:
            return FathomResponse(
                success=False,
                error=str(e),
                method="sdk"
            )
    
    # REST Methods
    def list_teams_rest(self) -> FathomResponse:
        """List teams using REST API"""
        try:
            url = f"{self.base_url}/teams"
            response = requests.get(url, headers=self.rest_headers)
            
            return FathomResponse(
                success=response.status_code == 200,
                data=response.json() if response.status_code == 200 else None,
                error=response.text if response.status_code != 200 else None,
                method="rest",
                status_code=response.status_code
            )
        except Exception as e:
            return FathomResponse(
                success=False,
                error=str(e),
                method="rest"
            )
    
    def list_meetings_rest(self, **params) -> FathomResponse:
        """
        List meetings using REST API with optional parameters.
        
        Args:
            **params: REST API parameters like limit, cursor, created_after, etc.
        """
        try:
            url = f"{self.base_url}/meetings"
            response = requests.get(url, headers=self.rest_headers, params=params)
            
            return FathomResponse(
                success=response.status_code == 200,
                data=response.json() if response.status_code == 200 else None,
                error=response.text if response.status_code != 200 else None,
                method="rest",
                status_code=response.status_code
            )
        except Exception as e:
            return FathomResponse(
                success=False,
                error=str(e),
                method="rest"
            )
    
    # Combined Methods (try SDK first, fallback to REST)
    def list_teams(self, prefer_rest: bool = False) -> FathomResponse:
        """
        List teams using preferred method with fallback.
        
        Args:
            prefer_rest: If True, try REST first; otherwise try SDK first
        """
        if prefer_rest:
            result = self.list_teams_rest()
            if result.success:
                return result
            return self.list_teams_sdk()
        else:
            result = self.list_teams_sdk()
            if result.success:
                return result
            return self.list_teams_rest()
    
    def list_meetings(self, prefer_rest: bool = False, **kwargs) -> FathomResponse:
        """
        List meetings using preferred method with fallback.
        
        Args:
            prefer_rest: If True, try REST first; otherwise try SDK first
            **kwargs: Parameters for the API call
        """
        if prefer_rest:
            result = self.list_meetings_rest(**kwargs)
            if result.success:
                return result
            return self.list_meetings_sdk(**kwargs)
        else:
            result = self.list_meetings_sdk(**kwargs)
            if result.success:
                return result
            return self.list_meetings_rest(**kwargs)
    
    # Utility Methods
    def get_api_key_info(self) -> Dict[str, Any]:
        """Get information about the API key"""
        return {
            "length": len(self.api_key),
            "prefix": self.api_key[:10] + "...",
            "sdk_client_available": self.sdk_client is not None
        }
    
    def test_connection(self) -> Dict[str, FathomResponse]:
        """Test both SDK and REST connections"""
        return {
            "teams_sdk": self.list_teams_sdk(),
            "teams_rest": self.list_teams_rest(),
            "meetings_sdk": self.list_meetings_sdk(),
            "meetings_rest": self.list_meetings_rest()
        }


# Convenience functions for common filter patterns
class FathomFilters:
    """Common filter patterns for Fathom API calls"""
    
    @staticmethod
    def last_n_days(days: int) -> Dict[str, str]:
        """Get created_after filter for last N days"""
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        return {"created_after": date}
    
    @staticmethod
    def external_meetings() -> Dict[str, Any]:
        """Filter for external meetings only"""
        return {
            "calendar_invitees_domains_type": ListMeetingsCalendarInviteesDomainsType.ONE_OR_MORE_EXTERNAL
        }
    
    @staticmethod
    def internal_meetings() -> Dict[str, Any]:
        """Filter for internal meetings only"""
        return {
            "calendar_invitees_domains_type": ListMeetingsCalendarInviteesDomainsType.ONLY_INTERNAL
        }
    
    @staticmethod
    def with_details() -> Dict[str, bool]:
        """Include all available details in response"""
        return {
            "include_action_items": True,
            "include_crm_matches": True,
            "include_summary": True,
            "include_transcript": True
        }


if __name__ == "__main__":
    # Simple test when run directly
    try:
        conn = FathomConnection()
        print(f"API Key Info: {conn.get_api_key_info()}")
        
        # Test teams
        teams = conn.list_teams()
        print(f"Teams result: success={teams.success}, method={teams.method}")
        
        # Test meetings
        meetings = conn.list_meetings()
        print(f"Meetings result: success={meetings.success}, method={meetings.method}")
        
    except Exception as e:
        print(f"Error: {e}")
