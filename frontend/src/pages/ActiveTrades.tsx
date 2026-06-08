import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, X, Equal, DollarSign, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import { formatTimeAgo } from '../lib/utils'

export default function ActiveTrades() {
  const queryClient = useQueryClient()
  const [selectedTrade, setSelectedTrade] = useState<number | null>(null)
  const [showActions, setShowActions] = useState(false)
  
  const { data: trades, isLoading } = useQuery({
    queryKey: ['active-trades'],
    queryFn: api.getActiveTrades,
    refetchInterval: 5000, // Refresh every 5 seconds
  })
  
  // Mutations for trade actions
  const closeTradeMutation = useMutation({
    mutationFn: (tradeId: number) => api.closeTrade(tradeId, 'Closed from GUI'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-trades'] })
      setShowActions(false)
      setSelectedTrade(null)
    },
  })
  
  const breakevenMutation = useMutation({
    mutationFn: (tradeId: number) => api.setTradeBreakeven(tradeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-trades'] })
      setShowActions(false)
      setSelectedTrade(null)
    },
  })
  
  const partialMutation = useMutation({
    mutationFn: ({ tradeId, percentage }: { tradeId: number; percentage: 25 | 50 | 75 }) =>
      api.takePartialProfit(tradeId, percentage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-trades'] })
      setShowActions(false)
      setSelectedTrade(null)
    },
  })
  
  const handleAction = (tradeId: number, action: 'close' | 'breakeven' | 'partial', percentage?: 25 | 50 | 75) => {
    if (action === 'close') {
      if (confirm('Are you sure you want to close this trade?')) {
        closeTradeMutation.mutate(tradeId)
      }
    } else if (action === 'breakeven') {
      if (confirm('Set stop loss to breakeven?')) {
        breakevenMutation.mutate(tradeId)
      }
    } else if (action === 'partial' && percentage) {
      if (confirm(`Take ${percentage}% partial profit?`)) {
        partialMutation.mutate({ tradeId, percentage })
      }
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-kob-text-dim">Loading trades...</div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-kob-text mb-2">Active Trades</h2>
          <p className="text-kob-text-dim">
            {trades?.length || 0} open position{trades?.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
      
      {/* Trades List */}
      <div className="space-y-4">
        {trades?.map((trade) => (
          <div key={trade.trade_id} className="card hover:shadow-xl transition-shadow">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl ${
                  trade.direction === 'BUY' 
                    ? 'bg-gradient-to-br from-green-900/40 to-green-800/20' 
                    : 'bg-gradient-to-br from-red-900/40 to-red-800/20'
                }`}>
                  {trade.direction === 'BUY' ? (
                    <TrendingUp size={24} className="text-green-400" />
                  ) : (
                    <TrendingDown size={24} className="text-red-400" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-lg text-kob-text">{trade.symbol}</h4>
                    <span className={`badge ${
                      trade.direction === 'BUY' ? 'badge-success' : 'badge-danger'
                    }`}>
                      {trade.direction}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {trade.channel_name && (
                      <span className="text-xs px-2 py-0.5 rounded bg-kob-crimson/30 text-kob-text-dim">
                        {trade.channel_name}
                      </span>
                    )}
                    <p className="text-xs text-kob-text-dim">
                      {trade.account_key.split(':')[0]}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <span className={`badge ${
                  trade.status === 'filled' ? 'badge-success' : 'badge-warning'
                }`}>
                  {trade.status.toUpperCase()}
                </span>
                <p className="text-xs text-kob-text-dim mt-1">
                  {formatTimeAgo(trade.entry_time)}
                </p>
              </div>
            </div>
            
            {/* Price Info */}
            <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-kob-app rounded-lg">
              <div>
                <p className="text-kob-text-dim text-xs mb-1">Entry Price</p>
                <p className="text-kob-text font-mono font-semibold text-sm">
                  {trade.entry_price.toFixed(5)}
                </p>
              </div>
              <div>
                <p className="text-kob-text-dim text-xs mb-1">Stop Loss</p>
                <p className="text-kob-text font-mono font-semibold text-sm">
                  {trade.sl ? trade.sl.toFixed(5) : '-'}
                </p>
              </div>
              <div>
                <p className="text-kob-text-dim text-xs mb-1">Take Profit</p>
                <p className="text-kob-text font-mono font-semibold text-sm">
                  {trade.tp ? trade.tp.toFixed(5) : '-'}
                </p>
              </div>
            </div>
            
            {/* Trade Details */}
            <div className="flex items-center justify-between mb-4 text-sm">
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-kob-text-dim">Lot Size: </span>
                  <span className="text-kob-text font-semibold">{trade.lot_size.toFixed(2)}</span>
                </div>
                {trade.risk_usd && (
                  <div>
                    <span className="text-kob-text-dim">Risk: </span>
                    <span className="text-red-400 font-semibold">${trade.risk_usd.toFixed(2)}</span>
                  </div>
                )}
              </div>
              
              {trade.tp1_hit && (
                <span className="badge badge-info flex items-center gap-1">
                  <DollarSign size={12} />
                  TP1 Hit
                </span>
              )}
            </div>
            
            {/* Action Buttons */}
            <div className="pt-4 border-t border-kob-border">
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => handleAction(trade.trade_id, 'close')}
                  disabled={closeTradeMutation.isPending}
                  className="btn-ghost text-red-400 hover:bg-red-900/20 flex items-center gap-2 text-sm"
                >
                  <X size={16} />
                  Close
                </button>
                
                <button
                  onClick={() => handleAction(trade.trade_id, 'breakeven')}
                  disabled={breakevenMutation.isPending}
                  className="btn-ghost hover:bg-kob-crimson/20 flex items-center gap-2 text-sm"
                >
                  <Equal size={16} />
                  Breakeven
                </button>
                
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleAction(trade.trade_id, 'partial', 25)}
                    disabled={partialMutation.isPending}
                    className="btn-ghost hover:bg-green-900/20 text-green-400 text-sm px-3"
                  >
                    25%
                  </button>
                  <button
                    onClick={() => handleAction(trade.trade_id, 'partial', 50)}
                    disabled={partialMutation.isPending}
                    className="btn-ghost hover:bg-green-900/20 text-green-400 text-sm px-3"
                  >
                    50%
                  </button>
                  <button
                    onClick={() => handleAction(trade.trade_id, 'partial', 75)}
                    disabled={partialMutation.isPending}
                    className="btn-ghost hover:bg-green-900/20 text-green-400 text-sm px-3"
                  >
                    75%
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {trades?.length === 0 && (
          <div className="card text-center py-16">
            <TrendingUp size={64} className="mx-auto text-kob-text-dim mb-4 opacity-50" />
            <p className="text-xl text-kob-text mb-2">No active trades</p>
            <p className="text-sm text-kob-text-dim">Positions will appear here when executed</p>
          </div>
        )}
      </div>
      
      {/* Loading Overlay */}
      {(closeTradeMutation.isPending || breakevenMutation.isPending || partialMutation.isPending) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-kob-base border border-kob-border rounded-lg p-6 flex items-center gap-3">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-kob-red border-t-transparent"></div>
            <span className="text-kob-text">Processing...</span>
          </div>
        </div>
      )}
    </div>
  )
}
