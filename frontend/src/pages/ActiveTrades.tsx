import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { api } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function ActiveTrades() {
  const { data: trades, isLoading } = useQuery({
    queryKey: ['active-trades'],
    queryFn: api.getActiveTrades,
    refetchInterval: 5000, // Refresh every 5 seconds
  })
  
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
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Active Trades</h2>
        <p className="text-kob-text-dim">
          {trades?.length || 0} open position{trades?.length !== 1 ? 's' : ''}
        </p>
      </div>
      
      {/* Trades List */}
      <div className="space-y-3">
        {trades?.map((trade) => (
          <div key={trade.trade_id} className="card">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  trade.direction === 'BUY' ? 'bg-green-900/30' : 'bg-red-900/30'
                }`}>
                  {trade.direction === 'BUY' ? (
                    <TrendingUp size={20} className="text-green-400" />
                  ) : (
                    <TrendingDown size={20} className="text-red-400" />
                  )}
                </div>
                <div>
                  <h4 className="font-semibold text-kob-text">{trade.symbol}</h4>
                  <p className="text-xs text-kob-text-dim">
                    {trade.account_key.split(':')[0]}
                  </p>
                </div>
              </div>
              
              <span className={`badge ${
                trade.status === 'filled' ? 'badge-success' : 'badge-warning'
              }`}>
                {trade.status.toUpperCase()}
              </span>
            </div>
            
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-kob-text-dim text-xs mb-1">Entry</p>
                <p className="text-kob-text font-medium">{trade.entry_price.toFixed(5)}</p>
              </div>
              <div>
                <p className="text-kob-text-dim text-xs mb-1">SL</p>
                <p className="text-kob-text font-medium">
                  {trade.sl ? trade.sl.toFixed(5) : '-'}
                </p>
              </div>
              <div>
                <p className="text-kob-text-dim text-xs mb-1">TP</p>
                <p className="text-kob-text font-medium">
                  {trade.tp ? trade.tp.toFixed(5) : '-'}
                </p>
              </div>
            </div>
            
            <div className="mt-3 pt-3 border-t border-kob-border flex items-center justify-between text-xs">
              <div className="flex items-center gap-4">
                <span className="text-kob-text-dim">
                  Lot: <span className="text-kob-text font-medium">{trade.lot_size}</span>
                </span>
                {trade.risk_usd && (
                  <span className="text-kob-text-dim">
                    Risk: <span className="text-kob-text font-medium">${trade.risk_usd.toFixed(2)}</span>
                  </span>
                )}
              </div>
              <span className="text-kob-text-dim">
                {formatDistanceToNow(new Date(trade.entry_time), { addSuffix: true })}
              </span>
            </div>
          </div>
        ))}
        
        {trades?.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-kob-text-dim">No active trades</p>
          </div>
        )}
      </div>
    </div>
  )
}
