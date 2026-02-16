# Oura Ring MCP Server

An MCP (Model Context Protocol) server that provides Claude with access to the Oura Ring health data API. Access your sleep, activity, readiness, heart rate, and other health metrics through Claude.

## Features

- **Sleep data** — daily scores, detailed periods, HRV, sleep phases
- **Activity data** — steps, calories, active time, scores
- **Readiness data** — readiness scores, body temperature, contributors
- **Heart rate** — continuous HR samples with source context
- **Stress & resilience** — stress levels, recovery time, resilience
- **SpO2** — blood oxygen saturation data
- **Workouts & sessions** — exercise tracking, meditation sessions
- **Sleep recommendations** — optimal bedtime window

## Setup

### 1. Get Oura API Credentials

1. Go to [Oura Developer Portal](https://cloud.ouraring.com/v2/docs)
2. Create a new application
3. Note your **Client ID** and **Client Secret**

### 2. Install

```bash
# Clone the repository
git clone <repo-url>
cd oura-mcp-server

# Install in development mode
pip install -e ".[dev]"
```

### 3. Configure

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
# OURA_CLIENT_ID=your_client_id
# OURA_CLIENT_SECRET=your_client_secret
```

### 4. Run

```bash
# Run with stdio transport (for local MCP clients)
oura-mcp

# Or run directly
python -m oura_mcp.server
```

## Authentication

The server uses OAuth2 Authorization Code flow. On first use:

1. Call `start_authentication` to get an authorization URL
2. Visit the URL and authorize the application
3. Copy the authorization code
4. Call `complete_authentication` with the code

Tokens are stored locally at `~/.config/oura-mcp/tokens.json` and automatically refresh when expired.

## Available Tools

### Data Tools
| Tool | Description |
|------|-------------|
| `get_sleep_summary` | Daily sleep scores and contributors |
| `get_sleep_details` | Detailed sleep periods (HRV, phases, HR) |
| `get_sleep_recommendations` | Optimal bedtime window |
| `get_activity_summary` | Steps, calories, active time, score |
| `get_readiness_summary` | Readiness score and contributors |
| `get_stress_data` | Stress/recovery time, day summary |
| `get_spo2_data` | Blood oxygen levels |
| `get_heart_rate` | HR samples with source context |
| `get_workouts` | Activity type, duration, calories |
| `get_sessions` | Meditation/rest/breathing sessions |
| `get_personal_info` | User profile |
| `get_daily_resilience` | Resilience level and contributors |

### Auth Tools
| Tool | Description |
|------|-------------|
| `check_auth_status` | Check if account is connected |
| `start_authentication` | Start OAuth2 flow |
| `complete_authentication` | Complete OAuth2 flow with code |
| `disconnect_account` | Remove stored credentials |

## Cloud Deployment (Railway)

For deploying as a remote MCP server:

```bash
# Set environment variables on Railway
OURA_CLIENT_ID=your_client_id
OURA_CLIENT_SECRET=your_client_secret
OURA_ACCESS_TOKEN=your_access_token
OURA_REFRESH_TOKEN=your_refresh_token
```

The server uses SSE transport when deployed to cloud. See `cloud_server.py` and `Dockerfile`.

## Claude.ai Integration

Add to your Claude.ai MCP server configuration:

```json
{
  "mcpServers": {
    "oura": {
      "url": "https://your-deployment-url.railway.app/sse"
    }
  }
}
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .
```

## License

MIT
