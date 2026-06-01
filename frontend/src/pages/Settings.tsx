import { useQuery } from '@tanstack/react-query'
import { Radio, Shield, Settings as SettingsIcon } from 'lucide-react'
import { api } from '../lib/api'

export default function Settings() {
  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: api.getChannels,
  })
  
  const { data: riskProfiles } = useQuery({
    queryKey: ['risk-profiles'],
    queryFn: api.getRiskProfiles,
  })
  
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
  })
  
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Settings</h2>
        <p className="text-kob-text-dim">Configure channels, risk profiles, and bot settings</p>
      </div>
      
      {/* Bot Status */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <SettingsIcon size={20} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Bot Status</h3>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-kob-text-dim mb-1">Status</p>
            <p className="text-kob-text font-medium">{botStatus?.status || 'Unknown'}</p>
          </div>
          <div>
            <p className="text-xs text-kob-text-dim mb-1">Mode</p>
            <p className="text-kob-text font-medium">
              {botStatus?.dry_run ? 'DRY RUN' : 'LIVE'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Channels */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Radio size={20} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Signal Channels</h3>
        </div>
        <div className="space-y-3">
          {channels?.map((channel) => (
            <div
              key={channel.channel_id}
              className="flex items-center justify-between p-3 bg-kob-app rounded-lg"
            >
              <div>
                <p className="font-medium text-kob-text">{channel.display_name}</p>
                <p className="text-xs text-kob-text-dim">Priority: {channel.priority}</p>
              </div>
              <span className={`badge ${
                channel.enabled ? 'badge-success' : 'badge-warning'
              }`}>
                {channel.enabled ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Risk Profiles */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={20} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Risk Profiles</h3>
        </div>
        <div className="space-y-3">
          {riskProfiles?.map((profile) => (
            <div
              key={profile.profile_id}
              className="p-3 bg-kob-app rounded-lg"
            >
              <div className="flex items-center justify-between mb-2">
                <p className="font-medium text-kob-text">{profile.profile_name}</p>
                {profile.is_default && (
                  <span className="badge-info">DEFAULT</span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-kob-text-dim">Daily Loss</p>
                  <p className="text-kob-text font-medium">{profile.daily_loss_pct}%</p>
                </div>
                <div>
                  <p className="text-kob-text-dim">Overall Loss</p>
                  <p className="text-kob-text font-medium">{profile.overall_loss_pct}%</p>
                </div>
                <div>
                  <p className="text-kob-text-dim">Max Trades</p>
                  <p className="text-kob-text font-medium">{profile.max_concurrent_trades}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
