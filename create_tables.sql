-- ============================================================================
-- MCS Stats Archive Database Schema
-- Created: 2026-10-14
-- Purpose: Store hourly snapshots of MCS channel monitoring data
-- All tables prefixed with mcs_stats_ for organization
-- ============================================================================

-- ============================================================================
-- 1. Main Channel Snapshots Table
-- Stores high-level channel information for each hourly snapshot
-- ============================================================================
CREATE TABLE mcs_stats_ChannelSnapshots (
    SnapshotID BIGINT IDENTITY(1,1) PRIMARY KEY,
    CaptureDateTime DATETIME2 NOT NULL,
    ChannelUUID UNIQUEIDENTIFIER NOT NULL,
    DeviceUUID UNIQUEIDENTIFIER NOT NULL,
    ChannelLabel NVARCHAR(100) NOT NULL,
    Timestamp DATETIME2 NOT NULL,
    AccessType NVARCHAR(50),
    DefaultProfileUUID UNIQUEIDENTIFIER,
    DefaultProfileLabel NVARCHAR(100),
    CPUUsed INT,
    MemoryAllocated BIGINT,
    MemoryUsed BIGINT,
    HighestActiveSeverity NVARCHAR(50),
    ActiveEventsCount INT,
    INDEX IX_CaptureDateTime (CaptureDateTime),
    INDEX IX_ChannelLabel (ChannelLabel),
    INDEX IX_ChannelUUID (ChannelUUID),
    INDEX IX_ChannelLabel_CaptureDateTime (ChannelLabel, CaptureDateTime)
);

-- ============================================================================
-- 2. Receiver Information Table
-- Stores receiver/stream information for each snapshot
-- ============================================================================
CREATE TABLE mcs_stats_ReceiverInfo (
    ReceiverID BIGINT IDENTITY(1,1) PRIMARY KEY,
    SnapshotID BIGINT NOT NULL,
    StreamType NVARCHAR(20),
    ProgramNumber INT,
    URL NVARCHAR(500),
    ProgramBitrate BIGINT,
    CONSTRAINT FK_ReceiverInfo_Snapshot FOREIGN KEY (SnapshotID) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID) ON DELETE CASCADE,
    INDEX IX_SnapshotID (SnapshotID)
);

-- ============================================================================
-- 3. Network Information Table
-- Stores network connection details for each receiver
-- ============================================================================
CREATE TABLE mcs_stats_NetworkInfo (
    NetworkID BIGINT IDENTITY(1,1) PRIMARY KEY,
    ReceiverID BIGINT NOT NULL,
    SourceIP NVARCHAR(50),
    SourcePort NVARCHAR(10),
    NetworkName NVARCHAR(100),
    PPS INT,
    IAT INT,
    CONSTRAINT FK_NetworkInfo_Receiver FOREIGN KEY (ReceiverID) 
        REFERENCES mcs_stats_ReceiverInfo(ReceiverID) ON DELETE CASCADE,
    INDEX IX_ReceiverID (ReceiverID)
);

-- ============================================================================
-- 4. Video Components Table
-- Stores video stream details for each snapshot
-- ============================================================================
CREATE TABLE mcs_stats_VideoComponents (
    VideoComponentID BIGINT IDENTITY(1,1) PRIMARY KEY,
    SnapshotID BIGINT NOT NULL,
    PID INT,
    ParentPID INT,
    ComponentIndex INT,
    Bitrate BIGINT,
    Monitored BIT,
    Codec NVARCHAR(50),
    Framerate NVARCHAR(20),
    Resolution NVARCHAR(50),
    GOPSize INT,
    AspectRatio NVARCHAR(50),
    ColorFormat NVARCHAR(50),
    Colorspace NVARCHAR(50),
    ProfileLevel NVARCHAR(50),
    AFD INT,
    PTSInterval INT,
    PTSPCRGap INT,
    BlockingFrame INT,
    BlockingScene INT,
    Motion INT,
    Brightness INT,
    CONSTRAINT FK_VideoComponents_Snapshot FOREIGN KEY (SnapshotID) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID) ON DELETE CASCADE,
    INDEX IX_SnapshotID (SnapshotID),
    INDEX IX_SnapshotID_ComponentIndex (SnapshotID, ComponentIndex)
);

-- ============================================================================
-- 5. Audio Components Table
-- Stores audio stream details for each snapshot (including Dolby-E)
-- ============================================================================
CREATE TABLE mcs_stats_AudioComponents (
    AudioComponentID BIGINT IDENTITY(1,1) PRIMARY KEY,
    SnapshotID BIGINT NOT NULL,
    PID INT,
    ParentPID INT,
    ComponentIndex INT,
    Bitrate BIGINT,
    Monitored BIT,
    Codec NVARCHAR(50),
    Language NVARCHAR(10),
    Channels NVARCHAR(10),
    Samplerate NVARCHAR(20),
    PTSInterval INT,
    PTSPCRGap INT,
    AudioStat NVARCHAR(10),
    LoudnessIntegratedHourly DECIMAL(10,2),
    LoudnessLRAHourly DECIMAL(10,2),
    LoudnessPeakHourly DECIMAL(10,2),
    LoudnessIntegratedDaily DECIMAL(10,2),
    LoudnessLRADaily DECIMAL(10,2),
    Level DECIMAL(10,2),
    TruePeak DECIMAL(10,2),
    Level3Sec DECIMAL(10,2),
    DolbyEPrograms NVARCHAR(50),
    DolbyEDesc230 NVARCHAR(200),
    DolbyEDesc231 NVARCHAR(200),
    DolbyEDesc232 NVARCHAR(200),
    CONSTRAINT FK_AudioComponents_Snapshot FOREIGN KEY (SnapshotID) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID) ON DELETE CASCADE,
    INDEX IX_SnapshotID (SnapshotID),
    INDEX IX_SnapshotID_ComponentIndex (SnapshotID, ComponentIndex)
);

-- ============================================================================
-- 6. Other Components Table
-- Stores PAT, PMT, SDT, and other PIDs
-- ============================================================================
CREATE TABLE mcs_stats_OtherComponents (
    ComponentID BIGINT IDENTITY(1,1) PRIMARY KEY,
    SnapshotID BIGINT NOT NULL,
    PID INT,
    ContentType NVARCHAR(50),
    Bitrate BIGINT,
    Monitored BIT,
    ServiceName NVARCHAR(200),
    ProviderName NVARCHAR(200),
    CONSTRAINT FK_OtherComponents_Snapshot FOREIGN KEY (SnapshotID) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID) ON DELETE CASCADE,
    INDEX IX_SnapshotID (SnapshotID)
);

-- ============================================================================
-- 7. Format Change Log Table
-- Explicitly tracks detected format changes for quick PowerBI access
-- ============================================================================
CREATE TABLE mcs_stats_FormatChangeLog (
    ChangeID BIGINT IDENTITY(1,1) PRIMARY KEY,
    ChannelLabel NVARCHAR(100) NOT NULL,
    DetectedAt DATETIME2 NOT NULL,
    ChangeType NVARCHAR(50) NOT NULL, -- 'VideoCodec', 'Resolution', 'Framerate', 'AudioCodec', 'AudioChannels', 'AudioAdded', 'AudioRemoved', 'VideoAdded', 'VideoRemoved'
    OldValue NVARCHAR(200),
    NewValue NVARCHAR(200),
    SnapshotIDBefore BIGINT,
    SnapshotIDAfter BIGINT NOT NULL,
    CONSTRAINT FK_FormatChangeLog_SnapshotBefore FOREIGN KEY (SnapshotIDBefore) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID),
    CONSTRAINT FK_FormatChangeLog_SnapshotAfter FOREIGN KEY (SnapshotIDAfter) 
        REFERENCES mcs_stats_ChannelSnapshots(SnapshotID),
    INDEX IX_DetectedAt (DetectedAt),
    INDEX IX_ChannelLabel (ChannelLabel),
    INDEX IX_ChannelLabel_DetectedAt (ChannelLabel, DetectedAt)
);

-- ============================================================================
-- Success Message
-- ============================================================================
-- MCS Stats Archive tables created successfully!
-- Tables created:
--   - mcs_stats_ChannelSnapshots (main fact table)
--   - mcs_stats_ReceiverInfo
--   - mcs_stats_NetworkInfo
--   - mcs_stats_VideoComponents
--   - mcs_stats_AudioComponents (includes Dolby-E columns)
--   - mcs_stats_OtherComponents
--   - mcs_stats_FormatChangeLog
--
-- NOTE: Run create_view.sql next to create the PowerBI summary view
