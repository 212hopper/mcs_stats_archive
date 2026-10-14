-- ============================================================================
-- MCS Stats Archive - PowerBI Summary View
-- Created: 2026-10-14
-- Purpose: Create denormalized view for fast PowerBI dashboard queries
-- ============================================================================
-- Run this AFTER create_tables.sql has been executed successfully
-- ============================================================================

CREATE VIEW vw_mcs_stats_ChannelSummary AS
SELECT 
    cs.SnapshotID,
    cs.CaptureDateTime,
    cs.ChannelLabel,
    cs.DeviceUUID,
    cs.ChannelUUID,
    cs.AccessType,
    cs.CPUUsed,
    cs.MemoryUsed,
    cs.MemoryAllocated,
    cs.HighestActiveSeverity,
    cs.ActiveEventsCount,
    ri.StreamType,
    ri.ProgramNumber,
    ri.ProgramBitrate,
    vc.Codec AS VideoCodec,
    vc.Resolution,
    vc.Framerate,
    vc.Bitrate AS VideoBitrate,
    vc.ColorFormat,
    vc.ProfileLevel,
    ac.Codec AS AudioCodec,
    ac.Channels AS AudioChannels,
    ac.Language AS AudioLanguage,
    ac.Samplerate AS AudioSamplerate,
    ac.LoudnessIntegratedHourly,
    ac.LoudnessLRAHourly,
    (SELECT COUNT(*) FROM mcs_stats_VideoComponents vc2 WHERE vc2.SnapshotID = cs.SnapshotID) AS VideoStreamCount,
    (SELECT COUNT(*) FROM mcs_stats_AudioComponents ac2 WHERE ac2.SnapshotID = cs.SnapshotID) AS AudioStreamCount
FROM mcs_stats_ChannelSnapshots cs
LEFT JOIN mcs_stats_ReceiverInfo ri ON cs.SnapshotID = ri.SnapshotID
LEFT JOIN mcs_stats_VideoComponents vc ON cs.SnapshotID = vc.SnapshotID AND vc.ComponentIndex = 1
LEFT JOIN mcs_stats_AudioComponents ac ON cs.SnapshotID = ac.SnapshotID AND ac.ComponentIndex = 1;

-- ============================================================================
-- View created successfully!
-- You can now use vw_mcs_stats_ChannelSummary in PowerBI for dashboard queries
-- ============================================================================
