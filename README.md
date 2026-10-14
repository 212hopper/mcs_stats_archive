# MCS Stats Archive

Automated hourly archival system for MCS channel monitoring statistics.

## Database Tables

All tables are prefixed with `mcs_stats_` for organization:

- `mcs_stats_ChannelSnapshots` - Main fact table with channel info
- `mcs_stats_ReceiverInfo` - Stream receiver details
- `mcs_stats_NetworkInfo` - Network connection details
- `mcs_stats_VideoComponents` - Video stream parameters
- `mcs_stats_AudioComponents` - Audio stream parameters (includes Dolby-E support)
- `mcs_stats_OtherComponents` - PAT, PMT, SDT, etc.
- `mcs_stats_FormatChangeLog` - Change detection audit log
- `vw_mcs_stats_ChannelSummary` - PowerBI summary view

## Setup Instructions

### 1. Create Database Tables

Run these SQL scripts in order:
```sql
-- Create all tables
create_tables.sql

-- Create PowerBI view
create_view.sql
```

### 2. Deploy to Portainer

1. Push this repo to your Git repository
2. In Portainer, create a new stack from Git
3. Add environment variables:
   - `MCS_IP_PRIMARY`
   - `MCS_IP_SECONDARY`
   - `MCS_PORT` (default: 443)
   - `MCS_USERNAME`
   - `MCS_PASSWORD`
   - `SQL_SERVER`
   - `SQL_DATABASE`
   - `SQL_USERNAME`
   - `SQL_PASSWORD`
   - `POLL_INTERVAL` (seconds, default: 3600)

### 3. Monitor

The container will:
- Poll MCS API at configured interval
- Store complete channel snapshots
- Log progress to container logs
- Auto-restart on failure

## Maintenance Scripts

### Clear All Data
```sql
clear_all_data.sql
```
⚠️ **WARNING**: Deletes all historical data and resets identity counters

## Features

✅ Continuous polling service (runs forever)
✅ Primary/secondary MCS server failover
✅ Token caching and auto-refresh
✅ Dolby-E audio support (AES3 with Dolby-E codec)
✅ Cascade deletes (removing snapshot removes all related data)
✅ PowerBI-optimized summary view
✅ Change detection audit logging table

## PowerBI Integration

Use `vw_mcs_stats_ChannelSummary` as your main data source for dashboards.

Relationship model:
```
ChannelSnapshots (1) → (∞) ReceiverInfo → (∞) NetworkInfo
ChannelSnapshots (1) → (∞) VideoComponents
ChannelSnapshots (1) → (∞) AudioComponents
ChannelSnapshots (1) → (∞) OtherComponents
```

## Logs

View logs in Portainer:
- Shows each poll cycle
- Lists channels archived
- Reports errors (continues on next cycle)
- Displays next poll time
