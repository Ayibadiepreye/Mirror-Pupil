import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, TrendingUp, TrendingDown, Shield, X } from 'lucide-react'
import { api } from '../lib/api'
import { useState } from 'react'

export default function AccountDetail() {
  const { accountKey } = useParams<{ accountKey: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showPayoutModal, setShowPayoutModal] = useState(false)
  const [newBalance, setNewBalance] = useState('')
  
  const { data: account, isLoading } = useQuery({
    queryKey: ['account', accountKey],
    queryFn: () => api.getAccount(accountKey!),
    enabled: !!accountKey,
  })
  
  const { data: trades } = useQuery({
    queryKey: ['active-trades', accountKey],
    queryFn: () => api.getActiveTradesForAccount(accountKey!),
    enabled: !!accountKey,
    refetchInterval: 5000,
  })
  
  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: api.getChannels,
  })
  
  const { data: riskProfiles } = useQuery({
    queryKey: ['risk-profiles'],
    queryFn: api.getRiskProfiles,
  })
  
  const payoutResetMutation = useMutation({
    mutationFn: (balance: number) => api.resetPayout(accountKey!, balance),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account', accountKey] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setShowPayoutModal(false)
      setNewBalance('')
    },
  })
  
  const handlePayoutReset = () => {
    const balance = parseFloat(newBalance)
    if (isNaN(balance) || balance <= 0) {
      alert('Please enter a valid balance')
      return
    }
    
    if (!confirm(`Reset account to $${balance.toFixed(2)}? This will reset all balance tracking.`)) {
      return
    }
    
    payoutResetMutation.mutate(balance)
  }
  
  if (isLoading || !account) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-kob-text-dim">Loading account...</div>
      </div>
    )
  }
  
  const pnlPositive = account.daily_pnl >= 0
  const pnlPercentage = ((account.daily_pnl / account.initial_balance) * 100).toFixed(2)
  const withdrawable = Math.max(0, account.current_balance - account.initial_balance)
  
  // Calculate risk percentages (simplified)
  const dailyLossPercent = ((account.daily_start_balance - account.current_balance) / account.initial_balance) * 100
  const overallLossPercent = ((account.initial_balance - account.current_balance) / account.initial_balance) * 100
  
  const dailyLossLimit = 3.0 // Would come from risk profile
  const overallLossLimit = 6.0 // Would come from risk profile
  
  const currentProfile = riskProfiles?.find(p => p.profile_id === account.risk_profile_id)
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-kob-app rounded-lg transition-colors"
        >
          <ArrowLeft size={24} className="text-kob-text" />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-kob-text">
            {account.display_name || account.account_key}
          </h2>
          <p className="text-sm text-kob-text-dim">{account.tl_email}</p>
        </div>
        <div>
          {account.breached && <span className="badge badge-danger">BREACHED</span>}
          {account.paused && !account.breached && <span className="badge badge-warning">PAUSED</span>}
          {!account.paused && !account.breached && <span className="badge badge-success">ACTIVE</span>}
        </div>
      </div>
      
      {/* Balance Section */}
      <div className="card bg-gradient-to-br from-kob-base to-kob-app">
        <div className="text-center mb-6">
          <p className="text-sm text-kob-text-dim mb-2">Current Balance</p>
          <p className="text-4xl font-bold text-kob-text mb-4">
            ${account.current_balance.toFixed(2)}
          </p>
          
          <div className="flex items-center justify-center gap-2">
            {pnlPositive ? (
              <TrendingUp size={20} className="text-green-400" />
            ) : (
              <TrendingDown size={20} className="text-red-400" />
            )}
            <span className={`text-xl font-bold ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
              ${account.daily_pnl.toFixed(2)} ({pnlPercentage}%)
            </span>
          </div>
          <p className="text-xs text-kob-text-dim mt-1">Daily P&L</p>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-kob-base/50 rounded-lg p-3 text-center">
            <p className="text-xs text-kob-text-dim mb-1">Initial Balance</p>
            <p className="text-lg font-bold text-kob-text">${account.initial_balance.toFixed(2)}</p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3 text-center">
            <p className="text-xs text-kob-text-dim mb-1">Highest Banked</p>
            <p className="text-lg font-bold text-kob-text">${account.highest_banked_balance.toFixed(2)}</p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3 text-center">
            <p className="text-xs text-kob-text-dim mb-1">Daily Start</p>
            <p className="text-lg font-bold text-kob-text">${account.daily_start_balance.toFixed(2)}</p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3 text-center">
            <p className="text-xs text-kob-text-dim mb-1">Withdrawable</p>
            <p className="text-lg font-bold text-green-400">${withdrawable.toFixed(2)}</p>
          </div>
        </div>
      </div>
      
      {/* Risk Progress Bars */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={20} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Risk Limits</h3>
        </div>
        
        <div className="space-y-4">
          {/* Daily Loss */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-kob-text">Daily Loss</span>
              <span className="text-sm font-medium text-kob-text">
                {dailyLossPercent.toFixed(2)}% / {dailyLossLimit}%
              </span>
            </div>
            <div className="w-full bg-kob-app rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  dailyLossPercent >= dailyLossLimit ? 'bg-red-400' :
                  dailyLossPercent >= dailyLossLimit * 0.8 ? 'bg-amber-400' :
                  'bg-green-400'
                }`}
                style={{ width: `${Math.min((Math.abs(dailyLossPercent) / dailyLossLimit) * 100, 100)}%` }}
              />
            </div>
          </div>
          
          {/* Overall Drawdown */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-kob-text">Overall Drawdown</span>
              <span className="text-sm font-medium text-kob-text">
                {overallLossPercent.toFixed(2)}% / {overallLossLimit}%
              </span>
            </div>
            <div className="w-full bg-kob-app rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  overallLossPercent >= overallLossLimit ? 'bg-red-400' :
                  overallLossPercent >= overallLossLimit * 0.8 ? 'bg-amber-400' :
                  'bg-green-400'
                }`}
                style={{ width: `${Math.min((Math.abs(overallLossPercent) / overallLossLimit) * 100, 100)}%` }}
              />
            </div>
          </div>
          
          {/* Profit Lock Indicator */}
          {account.profit_locked && (
            <div className="bg-green-900/30 border border-green-400/30 rounded-lg p-3">
              <div className="flex items-center gap-2 text-green-400 text-sm">
                <Shield size={16} />
                <span className="font-medium">PROFIT LOCK ACTIVE</span>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Risk Profile */}
      <div className="card">
        <h3 className="text-lg font-semibold text-kob-text mb-3">Risk Profile</h3>
        <div className="bg-kob-app rounded-lg p-3">
          <p className="text-kob-text font-medium">
            {currentProfile?.profile_name || 'Default Profile'}
          </p>
          {currentProfile && (
            <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
              <div>
                <p className="text-kob-text-dim">Max Risk/Trade</p>
                <p className="text-kob-text font-medium">{currentProfile.max_risk_per_trade_pct}%</p>
              </div>
              <div>
                <p className="text-kob-text-dim">Max Concurrent</p>
                <p className="text-kob-text font-medium">{currentProfile.max_concurrent_trades}</p>
              </div>
              <div>
                <p className="text-kob-text-dim">Commission</p>
                <p className="text-kob-text font-medium">${currentProfile.commission_per_lot}</p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Open Trades */}
      <div className="card">
        <h3 className="text-lg font-semibold text-kob-text mb-3">
          Open Trades ({trades?.length || 0})
        </h3>
        
        {trades && trades.length > 0 ? (
          <div className="space-y-2">
            {trades.map((trade) => (
              <div key={trade.trade_id} className="bg-kob-app rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-kob-text">{trade.symbol}</span>
                    <span className={`badge ${
                      trade.direction === 'BUY' ? 'badge-success' : 'badge-danger'
                    }`}>
                      {trade.direction}
                    </span>
                  </div>
                  <span className="text-xs text-kob-text-dim">
                    Lot: {trade.lot_size}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-kob-text-dim">Entry</p>
                    <p className="text-kob-text font-medium">{trade.entry_price.toFixed(5)}</p>
                  </div>
                  <div>
                    <p className="text-kob-text-dim">SL</p>
                    <p className="text-kob-text font-medium">{trade.sl?.toFixed(5) || '-'}</p>
                  </div>
                  <div>
                    <p className="text-kob-text-dim">TP</p>
                    <p className="text-kob-text font-medium">{trade.tp?.toFixed(5) || '-'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-kob-text-dim py-4">No open trades</p>
        )}
      </div>
      
      {/* Channel Subscriptions */}
      {channels && channels.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-kob-text mb-3">Channel Subscriptions</h3>
          <div className="space-y-2">
            {channels.map((channel) => (
              <div key={channel.channel_id} className="flex items-center justify-between bg-kob-app rounded-lg p-3">
                <span className="text-kob-text text-sm">{channel.display_name}</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={channel.enabled}
                    className="sr-only peer"
                    readOnly
                  />
                  <div className="w-11 h-6 bg-kob-base peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-kob-red rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                </label>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Payout Management */}
      <div className="card border-kob-red/30">
        <h3 className="text-lg font-semibold text-kob-text mb-3">Payout Management</h3>
        <p className="text-sm text-kob-text-dim mb-4">
          Reset account balance after withdrawing profits
        </p>
        <button
          type="button"
          onClick={() => setShowPayoutModal(true)}
          className="w-full py-3 bg-kob-red hover:bg-kob-red/90 text-white rounded-lg font-semibold transition-all"
        >
          Payout Reset
        </button>
      </div>
      
      {/* Payout Reset Modal */}
      {showPayoutModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-kob-base rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-kob-text">Payout Reset</h3>
              <button
                type="button"
                onClick={() => {
                  setShowPayoutModal(false)
                  setNewBalance('')
                }}
                className="text-kob-text-dim hover:text-kob-text"
              >
                <X size={20} />
              </button>
            </div>
            
            <p className="text-kob-text-dim mb-4">
              Enter the new starting balance after withdrawing profits. This will reset all balance tracking fields.
            </p>
            
            <div className="mb-6">
              <label className="block text-sm text-kob-text-dim mb-2">
                New Balance ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={newBalance}
                onChange={(e) => setNewBalance(e.target.value)}
                className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
                placeholder="Enter new balance"
              />
            </div>
            
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowPayoutModal(false)
                  setNewBalance('')
                }}
                disabled={payoutResetMutation.isPending}
                className="flex-1 py-2 bg-kob-app text-kob-text rounded-lg hover:bg-kob-base disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePayoutReset}
                disabled={payoutResetMutation.isPending || !newBalance}
                className="flex-1 py-2 bg-kob-red text-white rounded-lg hover:bg-kob-red/90 disabled:opacity-50"
              >
                {payoutResetMutation.isPending ? 'Resetting...' : 'Reset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
