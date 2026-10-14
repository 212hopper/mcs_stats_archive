-- ============================================================================
-- Clear All Data from MCS Stats Archive Tables
-- WARNING: This will delete ALL historical data!
-- ============================================================================

-- Delete all data (foreign keys will cascade)
DELETE FROM mcs_stats_ChannelSnapshots;

-- Reset identity seeds to start from 1 again
DBCC CHECKIDENT ('mcs_stats_ChannelSnapshots', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_ReceiverInfo', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_NetworkInfo', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_VideoComponents', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_AudioComponents', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_OtherComponents', RESEED, 0);
DBCC CHECKIDENT ('mcs_stats_FormatChangeLog', RESEED, 0);

-- Verify all tables are empty
SELECT 'mcs_stats_ChannelSnapshots' AS TableName, COUNT(*) AS [RowCount] FROM mcs_stats_ChannelSnapshots
UNION ALL
SELECT 'mcs_stats_ReceiverInfo', COUNT(*) FROM mcs_stats_ReceiverInfo
UNION ALL
SELECT 'mcs_stats_NetworkInfo', COUNT(*) FROM mcs_stats_NetworkInfo
UNION ALL
SELECT 'mcs_stats_VideoComponents', COUNT(*) FROM mcs_stats_VideoComponents
UNION ALL
SELECT 'mcs_stats_AudioComponents', COUNT(*) FROM mcs_stats_AudioComponents
UNION ALL
SELECT 'mcs_stats_OtherComponents', COUNT(*) FROM mcs_stats_OtherComponents
UNION ALL
SELECT 'mcs_stats_FormatChangeLog', COUNT(*) FROM mcs_stats_FormatChangeLog;

-- Success message
-- All tables cleared and identity seeds reset to start fresh
