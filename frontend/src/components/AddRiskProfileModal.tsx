import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface AddRiskProfileModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddRiskProfileModal({ isOpen, onClose, onSuccess }: AddRiskProfileModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const [profileName, setProfileName] = useState('')
  const [maxRiskPerTrade, setMaxRiskPerTrade] = useState('1.0')
  const [dailyLoss, setDailyLoss] = useState('3.0')
  const [dailyTrailing, setDailyTrailing] = useState(true)
  const [overallLoss, setOverallLoss] = useState('6.0')
  const [overallTrailing, setOverallTrailing] = useState(true)
  const [trailFromClosed, setTrailFromClosed] = useState(true)
  const [profitLock, setProfitLock] = useState('6.0')
  const [profitLockFloor, setProfitLockFloor] = useState('0.0')
  const [payoutBuffer, setPayoutBuffer] = useState('1.0')
  const [maxConcurrent, setMaxConcurrent] = useState('5')
  const [commission, setCommission] = useState('6.0')
  const [safetyBuffer, setSafetyBuffer] = useState('10.0')
  const [notes, setNotes] = useState('')
  
  if (!isOpen) return null
  
  const handleSubmit = async () => {
    if (!profileName) {
      setError('Please enter a profile name')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      await api.createRiskProfile({
        profile_name: profileName,
        is_default: false,
        max_risk_per_trade_pct: parseFloat(maxRiskPerTrade),
        daily_loss_pct: parseFloat(dailyLoss),
        daily_trailing: dailyTrailing,
        overall_loss_pct: parseFloat(overallLoss),
        overall_trailing: overallTrailing,
        overall_trail_from_closed_balance: trailFromClosed,
        profit_lock_pct: profitLock ? parseFloat(profitLock) : null,
        profit_lock_floor_pct: profitLockFloor ? parseFloat(profitLockFloor) : null,
        payout_buffer_pct: parseFloat(payoutBuffer),
        max_concurrent_trades: parseInt(maxConcurrent),
        commission_per_lot: parseFloat(commission),
        safety_buffer_pct: parseFloat(safetyBuffer),
        notes: notes || null
      })
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add risk profile')
    } finally {
      setLoading(false)
    }
  }
  
  const handleClose = () => {
    setProfileName('')
    setMaxRiskPerTrade('1.0')
    setDailyLoss('3.0')
    setDailyTrailing(true)
    setOverallLoss('6.0')
    setOverallTrailing(true)
    setTrailFromClosed(true)
    setProfitLock('6.0')
    setProfitLockFloor('0.0')
    setPayoutBuffer('1.0')
    setMaxConcurrent('5')
    setCommission('6.0')
    setSafetyBuffer('10.0')
    setNotes('')
    setError('')
    onClose()
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-kob-base rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-kob-border">
          <h3 className="text-lg font-semibold text-kob-text">Add Risk Profile</h3>
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
              Profile Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="My Custom Profile"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Max Risk Per Trade (%)</label>
              <input
                type="number"
                step="0.1"
                value={maxRiskPerTrade}
                onChange={(e) => setMaxRiskPerTrade(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
            
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Daily Loss Limit (%)</label>
              <input
                type="number"
                step="0.1"
                value={dailyLoss}
                onChange={(e) => setDailyLoss(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
          </div>
          
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={dailyTrailing}
                onChange={(e) => setDailyTrailing(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-kob-text">Daily Trailing</span>
            </label>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Overall Loss Limit (%)</label>
              <input
                type="number"
                step="0.1"
                value={overallLoss}
                onChange={(e) => setOverallLoss(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
            
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Profit Lock Trigger (%)</label>
              <input
                type="number"
                step="0.1"
                value={profitLock}
                onChange={(e) => setProfitLock(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={overallTrailing}
                onChange={(e) => setOverallTrailing(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-kob-text">Overall Trailing</span>
            </label>
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={trailFromClosed}
                onChange={(e) => setTrailFromClosed(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-kob-text">Trail from Closed Balance Only</span>
            </label>
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Profit Lock Floor (%)</label>
              <input
                type="number"
                step="0.1"
                value={profitLockFloor}
                onChange={(e) => setProfitLockFloor(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
            
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Payout Buffer (%)</label>
              <input
                type="number"
                step="0.1"
                value={payoutBuffer}
                onChange={(e) => setPayoutBuffer(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
            
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Max Concurrent</label>
              <input
                type="number"
                value={maxConcurrent}
                onChange={(e) => setMaxConcurrent(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Commission Per Lot ($)</label>
              <input
                type="number"
                step="0.1"
                value={commission}
                onChange={(e) => setCommission(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
            
            <div>
              <label className="block text-sm text-kob-text-dim mb-1">Safety Buffer (%)</label>
              <input
                type="number"
                step="0.1"
                value={safetyBuffer}
                onChange={(e) => setSafetyBuffer(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm text-kob-text-dim mb-1">Notes (Optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
              placeholder="Additional notes about this profile..."
            />
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
            disabled={loading || !profileName}
            className="flex-1 px-4 py-2 bg-kob-red text-white rounded hover:bg-kob-red/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Add Profile
          </button>
        </div>
      </div>
    </div>
  )
}
