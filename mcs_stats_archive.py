"""
MCS Stats Archive Script
Fetches channel statistics from MCS API and stores hourly snapshots in SQL Server
"""

import requests
import json
import urllib3
import os
import base64
import time
import pyodbc
from datetime import datetime, timedelta

# === CONFIG - READ FROM ENVIRONMENT VARIABLES ===
mcs_ip_primary = os.getenv('MCS_IP_PRIMARY')
mcs_ip_secondary = os.getenv('MCS_IP_SECONDARY')
access_port = os.getenv('MCS_PORT', '443')

if not mcs_ip_primary or not mcs_ip_secondary:
    raise Exception("MCS_IP_PRIMARY and MCS_IP_SECONDARY environment variables are required")

base_primary = f"https://{mcs_ip_primary}:{access_port}"
base_secondary = f"https://{mcs_ip_secondary}:{access_port}"

username = os.getenv('MCS_USERNAME')
password = os.getenv('MCS_PASSWORD')

if not username or not password:
    raise Exception("MCS_USERNAME and MCS_PASSWORD environment variables are required")

# === SQL SERVER CONFIG ===
SQL_SERVER = os.getenv('SQL_SERVER')
SQL_DATABASE = os.getenv('SQL_DATABASE')
SQL_USERNAME = os.getenv('SQL_USERNAME')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')

if not SQL_SERVER or not SQL_USERNAME or not SQL_PASSWORD:
    raise Exception("SQL_SERVER, SQL_USERNAME, and SQL_PASSWORD environment variables are required")

# === POLL INTERVAL CONFIG ===
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '3600'))  # Default 3600 seconds (1 hour)
print(f"Poll interval set to: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# === Pure-Python JWT exp extractor ===
def get_jwt_exp(token):
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        decoded = base64.b64decode(payload)
        return json.loads(decoded).get("exp", 0)
    except:
        return 0


# === Single DB connection function ===
def get_db_connection():
    return pyodbc.connect(
        f'Driver={{ODBC Driver 18 for SQL Server}};'
        f'Server={SQL_SERVER};'
        f'Database={SQL_DATABASE};'
        f'UID={SQL_USERNAME};'
        f'PWD={SQL_PASSWORD};'
        f'TrustServerCertificate=yes;'
    )


def get_token_columns(base_url):
    """Return the column names for the given base_url"""
    if base_url == base_primary:
        return "token_access_primary", "token_refresh_primary", "token_exp_primary"
    else:
        return "token_access_secondary", "token_refresh_secondary", "token_exp_secondary"


def load_token(base_url):
    try:
        access_col, refresh_col, exp_col = get_token_columns(base_url)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {access_col}, {refresh_col}, {exp_col} FROM dbo.mcs_admin WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return None

        token_access, token_refresh, token_exp = row
        exp = int(token_exp) if token_exp else 0

        if exp and exp > time.time() + 60:
            return {
                "access_token": token_access,
                "refresh_token": token_refresh,
                "exp": exp
            }
    except Exception as e:
        print(f"Token load error: {e}")

    return None


def save_token(access_token, refresh_token, base_url):
    try:
        exp = get_jwt_exp(access_token)
        access_col, refresh_col, exp_col = get_token_columns(base_url)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE dbo.mcs_admin 
            SET {access_col} = ?, {refresh_col} = ?, {exp_col} = ?
            WHERE id = 1
        """, (access_token, refresh_token, int(exp)))
        conn.commit()
        conn.close()
        server = "PRIMARY" if base_url == base_primary else "SECONDARY"
        print(f"Token saved to database ({server})")
    except Exception as e:
        print(f"Token save error: {e}")
        raise


def login(base_url):
    print(f"Logging in to {base_url}/api/5.1/auth/login ...")
    url = f"{base_url}/api/5.1/auth/login"
    r = requests.post(
        url,
        json={"username": username, "password": password},
        headers={"accept": "application/json", "content-type": "application/json"},
        verify=False,
        timeout=10
    )
    r.raise_for_status()
    data = r.json()["data"]
    save_token(data["access_token"], data["refresh_token"], base_url)
    return data["access_token"]


def refresh_token(base_url, refresh_token_str):
    print("Refreshing access token...")
    url = f"{base_url}/api/5.1/auth/token/refresh"
    r = requests.post(
        url,
        json={"refresh_token": refresh_token_str},
        headers={"accept": "application/json", "content-type": "application/json"},
        verify=False,
        timeout=10
    )
    if r.status_code >= 400:
        raise Exception("Refresh failed")
    data = r.json()["data"]
    save_token(data["access_token"], data["refresh_token"], base_url)
    return data["access_token"]


# === Global token cache ===
_cached_tokens = {}
_refresh_tokens = {}


def get_valid_token(base_url):
    global _cached_tokens, _refresh_tokens

    cache = load_token(base_url)
    if cache:
        _cached_tokens[base_url] = cache["access_token"]
        _refresh_tokens[base_url] = cache["refresh_token"]

    if base_url in _refresh_tokens:
        try:
            _cached_tokens[base_url] = refresh_token(base_url, _refresh_tokens[base_url])
            return _cached_tokens[base_url]
        except:
            print("Refresh failed, will try login")

    try:
        _cached_tokens[base_url] = login(base_url)
        cache = load_token(base_url)
        if cache:
            _refresh_tokens[base_url] = cache["refresh_token"]
        return _cached_tokens[base_url]
    except Exception as e:
        print(f"Login failed on {base_url}: {e}")
        raise Exception("Could not authenticate to MCS")


def bearer_token(base_url):
    global _cached_tokens
    if base_url not in _cached_tokens or not _cached_tokens[base_url]:
        _cached_tokens[base_url] = get_valid_token(base_url)
    return _cached_tokens[base_url]


def send_api_get_call(full_path, base_url=base_primary):
    global _cached_tokens

    url = base_url + full_path
    headers = {
        "Authorization": f"Bearer {bearer_token(base_url)}",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, verify=False, timeout=15)
        if r.status_code == 401:
            print("401 Unauthorized → forcing token refresh")
            _cached_tokens[base_url] = None
            headers["Authorization"] = f"Bearer {bearer_token(base_url)}"
            r = requests.get(url, headers=headers, verify=False, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        if "401" in str(e):
            print("Still 401 after retry → trying secondary")
            return send_api_get_call(full_path, base_secondary)
        raise


# === API Functions ===
def get_all_channels_stats():
    """Fetch all channel statistics from MCS API"""
    try:
        print("Fetching channel stats from primary...")
        return send_api_get_call("/api/5.1/channels/status")
    except Exception as e:
        print(f"Primary failed ({e}) → trying secondary")
        return send_api_get_call("/api/5.1/channels/status", base_secondary)


# === Database Insert Functions ===
def insert_channel_snapshot(cursor, channel, capture_time):
    """
    Insert a complete channel snapshot including all related tables
    Returns the SnapshotID of the inserted record
    """
    
    # Parse main channel data
    config = channel.get('config', {})
    resources = channel.get('resources', {})
    status = channel.get('status', {})
    default_profile = config.get('default_profile', {})
    
    # Insert main snapshot
    cursor.execute("""
        INSERT INTO mcs_stats_ChannelSnapshots 
        (CaptureDateTime, ChannelUUID, DeviceUUID, ChannelLabel, Timestamp, 
         AccessType, DefaultProfileUUID, DefaultProfileLabel, CPUUsed, 
         MemoryAllocated, MemoryUsed, HighestActiveSeverity, ActiveEventsCount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, 
        capture_time,
        channel.get('uuid'),
        channel.get('device'),
        channel.get('label'),
        channel.get('timestamp'),
        config.get('access_type'),
        default_profile.get('uuid'),
        default_profile.get('label'),
        resources.get('cpu_used'),
        resources.get('memory_allocated'),
        resources.get('memory_used'),
        status.get('highest_active_severity'),
        status.get('active_events')
    )
    
    # Get the SnapshotID
    cursor.execute("SELECT @@IDENTITY")
    snapshot_id = cursor.fetchone()[0]
    
    # Insert receiver info
    for receiver in status.get('receivers', []):
        cursor.execute("""
            INSERT INTO mcs_stats_ReceiverInfo 
            (SnapshotID, StreamType, ProgramNumber, URL, ProgramBitrate)
            VALUES (?, ?, ?, ?, ?)
        """, 
            snapshot_id,
            receiver.get('stream_type'),
            receiver.get('program_number'),
            receiver.get('url'),
            receiver.get('program_bitrate')
        )
        
        # Get the ReceiverID
        cursor.execute("SELECT @@IDENTITY")
        receiver_id = cursor.fetchone()[0]
        
        # Insert network info
        for network in receiver.get('networks', []):
            cursor.execute("""
                INSERT INTO mcs_stats_NetworkInfo 
                (ReceiverID, SourceIP, SourcePort, NetworkName, PPS, IAT)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                receiver_id,
                network.get('source_ip'),
                network.get('source_port'),
                network.get('name'),
                network.get('pps'),
                network.get('iat')
            )
    
    # Insert components (video, audio, others)
    for component in status.get('components', []):
        content_type = component.get('content_type')
        codec = component.get('codec', '')
        
        if content_type == 'Video':
            cursor.execute("""
                INSERT INTO mcs_stats_VideoComponents 
                (SnapshotID, PID, ParentPID, ComponentIndex, Bitrate, Monitored,
                 Codec, Framerate, Resolution, GOPSize, AspectRatio, ColorFormat,
                 Colorspace, ProfileLevel, AFD, PTSInterval, PTSPCRGap, 
                 BlockingFrame, BlockingScene, Motion, Brightness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                snapshot_id,
                component.get('pid'),
                component.get('parent_pid'),
                component.get('index'),
                component.get('bitrate'),
                component.get('monitored'),
                component.get('codec'),
                component.get('framerate'),
                component.get('resolution'),
                component.get('gop_size'),
                component.get('aspect'),
                component.get('color_format'),
                component.get('colorspace'),
                component.get('profile_level'),
                component.get('afd'),
                component.get('pts_interval'),
                component.get('pts_pcr_gap'),
                component.get('blocking_frame'),
                component.get('blocking_scene'),
                component.get('motion'),
                component.get('brightness')
            )
            
        elif content_type == 'Audio' or (content_type == 'AES3' and codec == 'Dolby-E'):
            loudness = component.get('loudness', {})
            hourly = loudness.get('hourly', {})
            daily = loudness.get('daily', {})
            
            cursor.execute("""
                INSERT INTO mcs_stats_AudioComponents 
                (SnapshotID, PID, ParentPID, ComponentIndex, Bitrate, Monitored,
                 Codec, Language, Channels, Samplerate, PTSInterval, PTSPCRGap,
                 AudioStat, LoudnessIntegratedHourly, LoudnessLRAHourly, 
                 LoudnessPeakHourly, LoudnessIntegratedDaily, LoudnessLRADaily, 
                 Level, TruePeak, Level3Sec, DolbyEPrograms, DolbyEDesc230, 
                 DolbyEDesc231, DolbyEDesc232)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                snapshot_id,
                component.get('pid'),
                component.get('parent_pid'),
                component.get('index'),
                component.get('bitrate'),
                component.get('monitored'),
                component.get('codec'),
                component.get('language'),
                component.get('channels'),
                component.get('samplerate'),
                component.get('pts_interval'),
                component.get('pts_pcr_gap'),
                component.get('audio_stat'),
                hourly.get('integrated'),
                hourly.get('lra'),
                hourly.get('peak'),
                daily.get('integrated'),
                daily.get('lra'),
                component.get('level'),
                component.get('truepeak'),
                component.get('level_3sec'),
                component.get('desc_230_560'),  # Dolby-E programs info
                component.get('desc_230_560'),  # Same as programs for now
                component.get('desc_231_561'),  # Dolby-E CH 5.1 description
                component.get('desc_232_562')   # Dolby-E CH 2 description
            )
            
        else:
            # Other components (PAT, PMT, SDT, etc.)
            cursor.execute("""
                INSERT INTO mcs_stats_OtherComponents
                (SnapshotID, PID, ContentType, Bitrate, Monitored, ServiceName, ProviderName)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                snapshot_id,
                component.get('pid'),
                content_type,
                component.get('bitrate'),
                component.get('monitored'),
                component.get('service'),
                component.get('provider')
            )
    
    return snapshot_id


def archive_channel_stats():
    """
    Main function to fetch and archive channel statistics
    """
    print("=" * 80)
    print(f"MCS Stats Archive - Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Get current timestamp
        capture_time = datetime.now()
        
        # Fetch all channel stats from API
        api_response = get_all_channels_stats()
        channels = api_response.get('data', [])
        
        if not channels:
            print("WARNING: No channels returned from API")
            return
        
        print(f"Retrieved {len(channels)} channels from MCS API")
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert each channel snapshot
        snapshot_count = 0
        for channel in channels:
            try:
                channel_label = channel.get('label', 'UNKNOWN')
                insert_channel_snapshot(cursor, channel, capture_time)
                snapshot_count += 1
                print(f"  ✓ Archived: {channel_label}")
            except Exception as e:
                print(f"  ✗ Failed to archive {channel_label}: {e}")
                # Continue with next channel even if one fails
        
        # Commit all inserts
        conn.commit()
        conn.close()
        
        print("=" * 80)
        print(f"Archive complete: {snapshot_count}/{len(channels)} channels stored successfully")
        print(f"Capture time: {capture_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR: Archive failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 80)
    print("MCS Stats Archive Service Started")
    print(f"Poll Interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")
    print(f"Database: {SQL_SERVER}/{SQL_DATABASE}")
    print("=" * 80)
    
    while True:
        try:
            archive_channel_stats()
        except Exception as e:
            print(f"ERROR in archive cycle: {e}")
            print("Will retry on next cycle...")
        
        print(f"\nSleeping for {POLL_INTERVAL} seconds until next poll...")
        print(f"Next run at: {(datetime.now() + timedelta(seconds=POLL_INTERVAL)).strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        time.sleep(POLL_INTERVAL)
