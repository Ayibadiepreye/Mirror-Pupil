import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface AddChannelModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddChannelModal({ isOpen, onClose, onSuccess }: AddChannelModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const [channelId, setChannelId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [signalPrefix, setSignalPrefix] = useState('')
  const [entryLogic, setEntryLogic] = useState('channels.billirichy.plugin')
  const [managementLogic, setManagementLogic] = useState('channels.billirichy.plugin')
  const [priority, setPriority] = useState('10')
  
  if (!isOpen) return null
  
  const handleSubmit = async () => {
    if (!channelId || !displayName || !signalPrefix) {
      setError('Please fill in all required fields')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      await api.createChannel({
        channel_id: parseInt(channelId),
        display_name: displayName,
        signal_prefix: signalPrefix,
        entry_logic_module: entryLogic,
        management_logic_module: managementLogic,
        priority: parseInt(priority),
        enabled: true
      })
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add channel')
    } finally {
      setLoading(false)
    }
  }
  
  const handleClose = () => {
    setChannelId('')
    setDisplayName('')
    setSignalPrefix('')
    setEntryLogic('channels.billirichy.plugin')
    setManagementLogic('channels.billirichy.plugin')
    setPriority('10')
    setError('')
    onClose()
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-kob-base rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-kob-border">
          <h3 className="text-lg font-semibold text-kob-text">Add Signal Channel</h3>
          <button onClick={handleClose} className="text-kob-text-dim hover:text-kob-text">
            <X size={20} />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded p-3 text-red-400 text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">
              Channel ID <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="-1001234567890"
            />
            <p className="text-xs text-kob-text-dim mt-1">Numeric Telegram channel ID</p>
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">
              Display Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="My Channel"
            />
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">
              Signal Prefix <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={signalPrefix}
              onChange={(e) => setSignalPrefix(e.target.value.toUpperCase())}
              maxLength={4}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="MC"
            />
            <p className="text-xs text-kob-text-dim mt-1">2-4 characters for signal IDs</p>
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">Entry Logic Module</label>
            <select
              value={entryLogic}
              onChange={(e) => setEntryLogic(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
            >
              <option value="channels.billirichy.plugin">BillirichyFX Logic</option>
              <option value="channels.firepips.plugin">Firepips Logic</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">Management Logic Module</label>
            <select
              value={managementLogic}
              onChange={(e) => setManagementLogic(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
            >
              <option value="channels.billirichy.plugin">BillirichyFX Logic</option>
              <option value="channels.firepips.plugin">Firepips Logic</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">Priority</label>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="10"
            />
            <p className="text-xs text-kob-text-dim mt-1">Lower number = higher priority</p>
          </div>
        </div>
        
        {/* Footer */}
        <div className="flex gap-2 p-4 border-t border-kob-border">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 bg-kob-app text-kob-text rounded hover:bg-kob-app/80"
            disabled={loading}
          >
            Cancel
          </button>
          
          <button
            onClick={handleSubmit}
            disabled={loading || !channelId || !displayName || !signalPrefix}
            className="flex-1 px-4 py-2 bg-kob-red text-white rounded hover:bg-kob-red/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Add Channel
          </button>
        </div>
      </div>
    </div>
  )
}
