import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Radio, Shield, Settings as SettingsIcon, Plus, Power, PowerOff, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import AddChannelModal from '../components/AddChannelModal'
import AddRiskProfileModal from '../components/AddRiskProfileModal'

export default function Settings() {
  const [showAddChannelModal, setShowAddChannelModal] = useState(false)
  const [showAddProfileModal, setShowAddProfileModal] = useState(false)
  
  const { data: channels, refetch: refetchChannels } = useQuery({
    queryKey: ['channels'],
    queryFn: api.getChannels,
  })
  
  const { data: riskProfiles, refetch: refetchProfiles } = useQuery({
    queryKey: ['risk-profiles'],
    queryFn: api.getRiskProfiles,
  })
  
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
  })
  
  const handleToggleChannel = async (channelId: number, enabled: boolean) => {
    try {
      if (enabled) {
        await api.disableChannel(channelId)
      } else {
        await api.enableChannel(channelId)
      }
      refetchChannels()
    } catch (err) {
      console.error('Failed to toggle channel:', err)
    }
  }
  
  const handleDeleteChannel = async (channelId: number, displayName: string) => {
    if (!confirm(`Delete channel "${displayName}"? This cannot be undone.`)) {
      return
    }
    
    try {
      await api.deleteChannel(channelId)
      refetchChannels()
    } catch (err) {
      console.error('Failed to delete channel:', err)
      alert('Failed to delete channel. It may be in use.')
    }
  }
  
  const handleDeleteProfile = async (profileId: number, profileName: string, isDefault: boolean) => {
    if (isDefault) {
      alert('Cannot delete the default risk profile. Set another profile as default first.')
      return
    }
    
    if (!confirm(`Delete risk profile "${profileName}"? This cannot be undone.`)) {
      return
    }
    
    try {
      await api.deleteRiskProfile(profileId)
      refetchProfiles()
    } catch (err) {
      console.error('Failed to delete profile:', err)
      alert('Failed to delete profile. It may be in use by accounts.')
    }
  }
  
  return (
    <>
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
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Radio size={20} className="text-kob-red" />
              <h3 className="text-lg font-semibold text-kob-text">Signal Channels</h3>
            </div>
            <button
              type="button"
              onClick={() => setShowAddChannelModal(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={14} />
              Add Channel
            </button>
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
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleToggleChannel(channel.channel_id, channel.enabled)}
                    className="flex items-center gap-2"
                  >
                    {channel.enabled ? (
                      <>
                        <Power size={16} className="text-green-400" />
                        <span className="badge badge-success">ENABLED</span>
                      </>
                    ) : (
                      <>
                        <PowerOff size={16} className="text-kob-text-dim" />
                        <span className="badge badge-warning">DISABLED</span>
                      </>
                    )}
                  </button>
                  
                  <button
                    type="button"
                    onClick={() => handleDeleteChannel(channel.channel_id, channel.display_name)}
                    className="p-2 text-kob-text-dim hover:text-red-400 transition-colors"
                    title="Delete channel"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Risk Profiles */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Shield size={20} className="text-kob-red" />
              <h3 className="text-lg font-semibold text-kob-text">Risk Profiles</h3>
            </div>
            <button
              type="button"
              onClick={() => setShowAddProfileModal(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={14} />
              Add Profile
            </button>
          </div>
          <div className="space-y-3">
            {riskProfiles?.map((profile) => (
              <div
                key={profile.profile_id}
                className="p-3 bg-kob-app rounded-lg"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-kob-text">{profile.profile_name}</p>
                    {profile.is_default && (
                      <span className="badge-info">DEFAULT</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleDeleteProfile(profile.profile_id, profile.profile_name, profile.is_default)}
                      className="p-2 text-kob-text-dim hover:text-red-400 transition-colors"
                      title="Delete profile"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
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
      
      <AddChannelModal
        isOpen={showAddChannelModal}
        onClose={() => setShowAddChannelModal(false)}
        onSuccess={() => refetchChannels()}
      />
      
      <AddRiskProfileModal
        isOpen={showAddProfileModal}
        onClose={() => setShowAddProfileModal(false)}
        onSuccess={() => refetchProfiles()}
      />
    </>
  )
}
