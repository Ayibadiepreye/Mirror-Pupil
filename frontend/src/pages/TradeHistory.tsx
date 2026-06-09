import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'
import { TradeHistory } from '../types'
import { formatLagosTime } from '../lib/utils'

export default function TradeHistoryPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [isExporting, setIsExporting] = useState(false)
  
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  const { data: history, isLoading } = useQuery({
    queryKey: ['trade-history', selectedAccount],
    queryFn: () => api.getTradeHistory(selectedAccount || undefined, 500, 0),
    refetchInterval: 10000,
  })
  
  const handleExport = async () => {
    try {
      setIsExporting(true)
      await api.exportTradeHistory(selectedAccount || undefined)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export trade history')
    } finally {
      setIsExporting(false)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-kob-text mb-2">Trade History</h2>
          <p className="text-kob-text-dim">
            {history?.length || 0} completed trade{history?.length !== 1 ? 's' : ''}
          </p>
        </div>
        
        <button
          onClick={handleExport}
          disabled={isExporting || !history || history.length === 0}
          className="btn-primary flex items-center gap-2"
        >
          <Download size={18} />
          {isExporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>
      
      {/* Filter */}
      <div className="card">
        <label htmlFor="account-filter" className="block text-sm font-medium text-kob-text mb-2">
          Filter by Account
        </label>
        <select
          id="account-filter"
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          className="input w-full md:w-64"
        >
          <option value="">All Accounts</option>
          {accounts?.map((account) => (
            <option key={account.account_key} value={account.account_key}>
              {account.display_name || account.account_key}
            </option>
          ))}
        </select>
      </div>
      
      {/* Trade History Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="text-center py-12 text-kob-text-dim">
            Loading trade history...
          </div>
        ) : !history || history.length === 0 ? (
          <div className="text-center py-16">
            <TrendingUp size={64} className="mx-auto text-kob-text-dim mb-4 opacity-50" />
            <p className="text-xl text-kob-text mb-2">No trade history found</p>
            <p className="text-sm text-kob-text-dim">Completed trades will appear here</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-kob-crimson/30 border-b border-kob-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Exit Time (Lagos)
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Channel
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Direction
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Entry
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Exit
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Lots
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-kob-text uppercase tracking-wider">
                    P&L (USD)
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Result
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-kob-text uppercase tracking-wider">
                    Close Reason
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-kob-border">
                {history.map((trade: TradeHistory) => (
                  <tr key={trade.history_id} className="hover:bg-kob-crimson/10 transition-colors">
                    <td className="px-4 py-3 text-sm text-kob-text whitespace-nowrap">
                      {formatLagosTime(trade.exit_time)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {trade.channel_name ? (
                        <span className="px-2 py-1 rounded bg-kob-crimson/30 text-kob-text text-xs">
                          {trade.channel_name}
                        </span>
                      ) : (
                        <span className="text-kob-text-dim text-xs">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-kob-text">
                      {trade.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                          trade.direction === 'BUY'
                            ? 'bg-green-900/30 text-green-400'
                            : 'bg-red-900/30 text-red-400'
                        }`}
                      >
                        {trade.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right font-mono">
                      {trade.entry_price.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right font-mono">
                      {trade.exit_price.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right font-mono">
                      {trade.lot_size.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-bold font-mono">
                      <span
                        className={
                          trade.pnl > 0
                            ? 'text-green-400'
                            : trade.pnl < 0
                            ? 'text-red-400'
                            : 'text-kob-text-dim'
                        }
                      >
                        {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                          trade.outcome === 'WIN'
                            ? 'bg-green-900/30 text-green-400'
                            : trade.outcome === 'LOSS'
                            ? 'bg-red-900/30 text-red-400'
                            : 'bg-gray-900/30 text-gray-400'
                        }`}
                      >
                        {trade.outcome}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text-dim">
                      <div>
                        {trade.close_reason.replace(/_/g, ' ')}
                      </div>
                      {trade.manual_action_type && (
                        <div className="mt-1">
                          <span className="px-2 py-0.5 rounded text-xs bg-blue-900/30 text-blue-400">
                            Manual: {trade.manual_action_type.replace('MANUAL_', '')}
                          </span>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Summary Stats */}
      {history && history.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card bg-gradient-to-br from-kob-base to-kob-app">
            <div className="text-sm text-kob-text-dim mb-1">Total Trades</div>
            <div className="text-3xl font-bold text-kob-text">{history.length}</div>
          </div>
          <div className="card bg-gradient-to-br from-green-900/20 to-kob-base">
            <div className="text-sm text-kob-text-dim mb-1">Winners</div>
            <div className="text-3xl font-bold text-green-400">
              {history.filter((t: TradeHistory) => t.outcome === 'WIN').length}
            </div>
            <div className="text-xs text-kob-text-dim mt-1">
              {((history.filter((t: TradeHistory) => t.outcome === 'WIN').length / history.length) * 100).toFixed(1)}% win rate
            </div>
          </div>
          <div className="card bg-gradient-to-br from-red-900/20 to-kob-base">
            <div className="text-sm text-kob-text-dim mb-1">Losers</div>
            <div className="text-3xl font-bold text-red-400">
              {history.filter((t: TradeHistory) => t.outcome === 'LOSS').length}
            </div>
          </div>
          <div className={`card bg-gradient-to-br ${
            history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0) > 0
              ? 'from-green-900/20 to-kob-base'
              : 'from-red-900/20 to-kob-base'
          }`}>
            <div className="text-sm text-kob-text-dim mb-1">Total P&L</div>
            <div
              className={`text-3xl font-bold ${
                history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0) > 0
                  ? 'text-green-400'
                  : 'text-red-400'
              }`}
            >
              {history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0) > 0 ? '+' : ''}
              ${history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0).toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
