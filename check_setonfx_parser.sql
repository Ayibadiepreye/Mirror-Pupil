-- Check what parser/logic Setonfx channel is using
SELECT 
    channel_id,
    display_name,
    signal_prefix,
    entry_logic_module,
    management_logic_module,
    priority,
    enabled
FROM channels
WHERE display_name = 'Setonfx' OR channel_id = -1003708350949;
