import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { TradeHistory } from '../types'
import { format } from 'date-fns'

export default function TradeHistoryPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  const { data: history, isLoading } = useQuery({
    queryKey: ['trade-history', selectedAccount],
    queryFn: () => api.getTradeHistory(selectedAccount || undefined, 100, 0),
    refetchInterval: 5000,
  })
  
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Trade History</h2>
        <p className="text-kob-text-dim">View past trades and performance</p>
      </div>
      
      {/* Filter */}
      <div className="card">
        <label className="block text-sm font-medium text-kob-text mb-2">
          Filter by Account
        </label>
        <select
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          className="w-full md:w-64 bg-kob-bg-secondary border border-kob-border rounded-lg px-4 py-2 text-kob-text focus:outline-none focus:ring-2 focus:ring-kob-accent"
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
          <div className="text-center py-12 text-kob-text-dim">
            No trade history found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-kob-bg-tertiary border-b border-kob-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Exit Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Signal ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Direction
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Entry
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Exit
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Lots
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    P&L (USD)
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Outcome
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-kob-text-dim uppercase tracking-wider">
                    Close Reason
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-kob-border">
                {history.map((trade: TradeHistory) => (
                  <tr key={trade.history_id} className="hover:bg-kob-bg-secondary transition-colors">
                    <td className="px-4 py-3 text-sm text-kob-text whitespace-nowrap">
                      {format(new Date(trade.exit_time), 'MMM dd, HH:mm')}
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text-dim">
                      {trade.signal_id}
                      {trade.sub_signal_id && (
                        <span className="text-xs ml-1">({trade.sub_signal_id})</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-kob-text">
                      {trade.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          trade.direction === 'BUY'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {trade.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right">
                      {trade.entry_price.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right">
                      {trade.exit_price.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text text-right">
                      {trade.lot_size.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium">
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
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          trade.outcome === 'WIN'
                            ? 'bg-green-500/20 text-green-400'
                            : trade.outcome === 'LOSS'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {trade.outcome}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-kob-text-dim">
                      {trade.close_reason.replace(/_/g, ' ')}
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <div className="text-sm text-kob-text-dim mb-1">Total Trades</div>
            <div className="text-2xl font-bold text-kob-text">{history.length}</div>
          </div>
          <div className="card">
            <div className="text-sm text-kob-text-dim mb-1">Winners</div>
            <div className="text-2xl font-bold text-green-400">
              {history.filter((t: TradeHistory) => t.outcome === 'WIN').length}
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-kob-text-dim mb-1">Losers</div>
            <div className="text-2xl font-bold text-red-400">
              {history.filter((t: TradeHistory) => t.outcome === 'LOSS').length}
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-kob-text-dim mb-1">Total P&L</div>
            <div
              className={`text-2xl font-bold ${
                history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0) > 0
                  ? 'text-green-400'
                  : 'text-red-400'
              }`}
            >
              ${history.reduce((sum: number, t: TradeHistory) => sum + t.pnl, 0).toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

