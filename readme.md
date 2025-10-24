# Fathom.ai Python Integration

Clean, modular Python integration for the Fathom.ai API with complete separation of business logic and presentation.

## Architecture

### Core Components

1. **`fathom_connection.py`** - Business Logic Layer
   - `FathomConnection` class: Unified interface for both SDK and REST API access
   - `FathomResponse` dataclass: Standardized response format
   - `FathomFilters` class: Helper methods for common filter patterns
   - Complete separation of API logic from display code

2. **`display_utils.py`** - Presentation Layer
   - Reusable display functions for CLI output
   - Consistent formatting across all test scripts
   - Easy to replace with other UI frameworks (web, GUI, etc.)

## Key Features

### FathomConnection Class

```python
from fathom_connection import FathomConnection, FathomFilters

# Initialize connection (loads from ~/.env automatically)
conn = FathomConnection()

# Or with debug mode enabled
conn = FathomConnection(debug=True)
```

### Dual API Support

```python
# Use SDK method
result = conn.list_meetings_sdk()

# Use REST API method
result = conn.list_meetings_rest()

# Use combined method (tries SDK first, falls back to REST)
result = conn.list_meetings()
```

### Standardized Response Format

```python
if result.success:
    data = result.data  # The actual API response
    method = result.method  # 'sdk' or 'rest'
    status_code = result.status_code  # For REST calls
else:
    error = result.error  # Error message
```

### Filter Helpers

```python
# Get meetings from last 30 days
filters = FathomFilters.last_n_days(30)
result = conn.list_meetings(**filters)

# Get external meetings only
filters = FathomFilters.external_meetings()
result = conn.list_meetings(**filters)

# Get all available details
filters = FathomFilters.with_details()
result = conn.list_meetings(**filters)
```

## Test Scripts

Two comprehensive test scripts demonstrate clean separation of concerns:

### test_api.py - Comprehensive API Testing
Tests both SDK and REST API methods with all core functionality:
- Connection and API key validation
- Teams listing (SDK, REST, and combined auto-fallback methods)
- Meetings listing with debug information
- Response formatting and error handling
- Helpful suggestions for API usage

```bash
python test_api.py
```

### test_filters.py - Advanced Filter Testing
Tests various filter combinations with optional debug mode:
- Default SDK filters
- Calendar invitee domain filters (internal/external)
- Date range filters (7, 30, 90, 365 days)
- Meeting type filters (all/internal/external)
- Combined filter patterns
- Debug mode to see HTTP requests

```bash
# Run with normal output
python test_filters.py

# Run with debug mode to see HTTP requests
python test_filters.py --debug
```

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up your API key in `~/.env`:
```bash
FATHOM_API_KEY=your_api_key_here
```

## Benefits of This Architecture

### Separation of Concerns
- **Business Logic** (fathom_connection.py): API calls, data processing, error handling
- **Presentation** (display_utils.py): Formatting, colors, CLI output
- **Tests** (test_*.py): Pure test logic using both layers

### Maintainability
- Change API logic without touching display code
- Update display formatting without modifying business logic
- Easy to add new output formats (web, JSON, etc.)

### Reusability
- `FathomConnection` can be used in any Python application
- Display utilities work with any data source
- Filter helpers simplify common use cases

### Testability
- Business logic can be tested independently
- Display functions can be tested with mock data
- Clean interfaces make mocking easier

### Flexibility
- Easy to swap between SDK and REST API
- Automatic fallback mechanisms
- Debug mode for troubleshooting

## Usage Examples

### Basic Usage

```python
from fathom_connection import FathomConnection

# Initialize
conn = FathomConnection()

# Get meetings
result = conn.list_meetings()

if result.success:
    meetings = result.data.result.items
    print(f"Found {len(meetings)} meetings")
else:
    print(f"Error: {result.error}")
```

### With Display Utilities

```python
from fathom_connection import FathomConnection
from display_utils import print_header, print_response_summary, print_meeting_summary

# Initialize
conn = FathomConnection()

# Display formatted header
print_header("Meeting List")

# Get and display results
result = conn.list_meetings()
print_response_summary(result, "List Meetings")

if result.success and result.data.result:
    print_meeting_summary(result.data.result.items)
```

### With Filters

```python
from fathom_connection import FathomConnection, FathomFilters

conn = FathomConnection()

# Get last 30 days of meetings
filters = FathomFilters.last_n_days(30)
result = conn.list_meetings(**filters)

# Get external meetings with full details
filters = {
    **FathomFilters.external_meetings(),
    **FathomFilters.with_details()
}
result = conn.list_meetings(**filters)
```

## API Coverage

### Currently Implemented
- ✅ List Teams (SDK + REST)
- ✅ List Meetings (SDK + REST)
- ✅ API Key Information
- ✅ Connection Testing
- ✅ Debug Mode

### Coming Soon
- 🔄 Get Meeting Details
- 🔄 Search Meetings
- 🔄 Get Transcripts
- 🔄 Get Action Items
- 🔄 Get Summaries

## Development

### Adding New API Methods

1. Add method to `FathomConnection` class:
```python
def new_method_sdk(self, **params) -> FathomResponse:
    """Description"""
    try:
        response = self.sdk_client.new_method(**params)
        return FathomResponse(success=True, data=response, method="sdk")
    except Exception as e:
        return FathomResponse(success=False, error=str(e), method="sdk")
```

2. Add corresponding REST method if needed:
```python
def new_method_rest(self, **params) -> FathomResponse:
    """Description"""
    try:
        url = f"{self.base_url}/endpoint"
        response = requests.get(url, headers=self.rest_headers, params=params)
        return FathomResponse(
            success=response.status_code == 200,
            data=response.json() if response.status_code == 200 else None,
            error=response.text if response.status_code != 200 else None,
            method="rest",
            status_code=response.status_code
        )
    except Exception as e:
        return FathomResponse(success=False, error=str(e), method="rest")
```

3. Add combined method:
```python
def new_method(self, prefer_rest: bool = False, **kwargs) -> FathomResponse:
    """Description with automatic fallback"""
    if prefer_rest:
        result = self.new_method_rest(**kwargs)
        if result.success:
            return result
        return self.new_method_sdk(**kwargs)
    else:
        result = self.new_method_sdk(**kwargs)
        if result.success:
            return result
        return self.new_method_rest(**kwargs)
```

### Adding Display Functions

Add new formatting functions to `display_utils.py`:

```python
def print_new_format(data: Any):
    """Description of what this formats"""
    # Implementation here
    pass
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Follow the separation of concerns pattern
2. Add tests for new features
3. Update documentation
4. Keep business logic separate from display code
