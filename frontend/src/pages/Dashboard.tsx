import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, DollarSign, Activity, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import AccountCard from '../components/AccountCard'
import StatCard from '../components/StatCard'

export default function Dashboard() {
  // Fetch all accounts
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  // Fetch bot status
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  })
  
  // Calculate combined metrics
  const totalBalance = accounts?.reduce((sum, acc) => sum + acc.current_balance, 0) || 0
  const totalPnL = accounts?.reduce((sum, acc) => sum + acc.daily_pnl, 0) || 0
  const totalTrades = botStatus?.total_active_trades || 0
  const activeAccounts = botStatus?.active_accounts || 0
  
  if (accountsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-kob-text-dim">Loading dashboard...</div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Dashboard</h2>
        <p className="text-kob-text-dim">Overview of all trading accounts</p>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4">
        <StatCard
          title="Total Balance"
          value={`$${totalBalance.toFixed(2)}`}
          icon={DollarSign}
          trend={totalPnL >= 0 ? 'up' : 'down'}
        />
        <StatCard
          title="Daily P&L"
          value={`$${totalPnL.toFixed(2)}`}
          icon={totalPnL >= 0 ? TrendingUp : TrendingDown}
          trend={totalPnL >= 0 ? 'up' : 'down'}
          valueColor={totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}
        />
        <StatCard
          title="Active Trades"
          value={totalTrades.toString()}
          icon={Activity}
        />
        <StatCard
          title="Active Accounts"
          value={`${activeAccounts}/${accounts?.length || 0}`}
          icon={AlertTriangle}
        />
      </div>
      
      {/* Accounts List */}
      <div>
        <h3 className="text-lg font-semibold text-kob-text mb-4">Accounts</h3>
        <div className="space-y-4">
          {accounts?.map((account) => (
            <AccountCard key={account.account_key} account={account} />
          ))}
          
          {accounts?.length === 0 && (
            <div className="card text-center py-8">
              <p className="text-kob-text-dim">No accounts configured yet</p>
              <p className="text-sm text-kob-text-dim mt-2">
                Add your first account in Settings
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
