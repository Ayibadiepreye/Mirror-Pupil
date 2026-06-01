import { TrendingUp, TrendingDown } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Account } from '../types'

interface AccountCardProps {
  account: Account
}

export default function AccountCard({ account }: AccountCardProps) {
  const navigate = useNavigate()
  const pnlPositive = account.daily_pnl >= 0
  const pnlPercentage = ((account.daily_pnl / account.initial_balance) * 100).toFixed(2)
  
  const handleClick = () => {
    // URL encode the account key for safe routing
    const encodedKey = encodeURIComponent(account.account_key)
    navigate(`/accounts/${encodedKey}`)
  }
  
  return (
    <div 
      onClick={handleClick}
      className="card hover:border-kob-crimson transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-semibold text-kob-text">
            {account.display_name || account.account_key}
          </h4>
          <p className="text-xs text-kob-text-dim mt-1">{account.tl_server.toUpperCase()}</p>
        </div>
        
        <div className="flex items-center gap-2">
          {account.breached && (
            <span className="badge-danger">BREACHED</span>
          )}
          {account.paused && !account.breached && (
            <span className="badge-warning">PAUSED</span>
          )}
          {!account.paused && !account.breached && (
            <span className="badge-success">ACTIVE</span>
          )}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {/* Balance */}
        <div>
          <p className="text-xs text-kob-text-dim mb-1">Balance</p>
          <p className="text-lg font-bold text-kob-text">
            ${account.current_balance.toFixed(2)}
          </p>
        </div>
        
        {/* Daily P&L */}
        <div>
          <p className="text-xs text-kob-text-dim mb-1">Daily P&L</p>
          <div className="flex items-center gap-1">
            {pnlPositive ? (
              <TrendingUp size={16} className="text-green-400" />
            ) : (
              <TrendingDown size={16} className="text-red-400" />
            )}
            <p className={`text-lg font-bold ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
              ${account.daily_pnl.toFixed(2)}
            </p>
            <span className={`text-xs ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
              ({pnlPercentage}%)
            </span>
          </div>
        </div>
      </div>
      
      {/* Risk Metrics */}
      <div className="mt-4 pt-4 border-t border-kob-border">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <p className="text-kob-text-dim">Initial</p>
            <p className="text-kob-text font-medium">${account.initial_balance.toFixed(0)}</p>
          </div>
          <div>
            <p className="text-kob-text-dim">Peak</p>
            <p className="text-kob-text font-medium">${account.highest_banked_balance.toFixed(0)}</p>
          </div>
          <div>
            <p className="text-kob-text-dim">Profit Lock</p>
            <p className="text-kob-text font-medium">{account.profit_locked ? 'YES' : 'NO'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
