import { useQuery } from '@tanstack/react-query'
import { Shield, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import AccountCard from '../components/AccountCard'

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
  
  // Fetch channels
  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: api.getChannels,
  })
  
  // Calculate combined metrics
  const totalBalance = accounts?.reduce((sum, acc) => sum + acc.current_balance, 0) || 0
  const totalInitial = accounts?.reduce((sum, acc) => sum + acc.initial_balance, 0) || 0
  const totalBanked = accounts?.reduce((sum, acc) => sum + acc.highest_banked_balance, 0) || 0
  const totalPnL = accounts?.reduce((sum, acc) => sum + acc.daily_pnl, 0) || 0
  const totalTrades = botStatus?.total_active_trades || 0
  const activeAccounts = botStatus?.active_accounts || 0
  const pausedAccounts = botStatus?.paused_accounts || 0
  const breachedAccounts = botStatus?.breached_accounts || 0
  
  // Calculate overall return
  const overallReturn = totalInitial > 0 ? ((totalBalance - totalInitial) / totalInitial) * 100 : 0
  const dailyPnLPercent = totalInitial > 0 ? (totalPnL / totalInitial) * 100 : 0
  
  // Calculate withdrawable (simplified - actual would need risk profile logic)
  const withdrawable = Math.max(0, totalBalance - totalInitial)
  
  // Combined equity (balance + floating P&L - simplified)
  const combinedEquity = totalBalance
  
  // Risk status
  const riskStatus = breachedAccounts > 0 ? 'BREACHED' : 
                     pausedAccounts > 0 ? 'PAUSED' : 
                     'HEALTHY'
  
  // Active channels
  const activeChannels = channels?.filter(c => c.enabled).length || 0
  const totalChannels = channels?.length || 0
  
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-kob-text mb-2">Dashboard</h2>
          <p className="text-kob-text-dim">Overview of all trading accounts</p>
        </div>
        <Link to="/accounts">
          <button type="button" className="btn-primary flex items-center gap-2">
            <Plus size={16} />
            Add Account
          </button>
        </Link>
      </div>
      
      {/* Global Metrics Card */}
      <div className="card bg-gradient-to-br from-kob-base to-kob-app border-kob-red/20">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={24} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Global Metrics</h3>
        </div>
        
        {/* Account Status Pills */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="badge badge-success">{activeAccounts} Active</span>
          {pausedAccounts > 0 && <span className="badge badge-warning">{pausedAccounts} Paused</span>}
          {breachedAccounts > 0 && <span className="badge badge-danger">{breachedAccounts} Breached</span>}
          <span className="badge bg-kob-app text-kob-text">{accounts?.length || 0} Total</span>
        </div>
        
        {/* Main Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-kob-base/50 rounded-lg p-3">
            <p className="text-xs text-kob-text-dim mb-1">Combined Balance</p>
            <p className="text-2xl font-bold text-kob-text">${totalBalance.toFixed(2)}</p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3">
            <p className="text-xs text-kob-text-dim mb-1">Daily P&L</p>
            <p className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${totalPnL.toFixed(2)}
              <span className="text-sm ml-2">({dailyPnLPercent.toFixed(2)}%)</span>
            </p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3">
            <p className="text-xs text-kob-text-dim mb-1">Overall Return</p>
            <p className={`text-2xl font-bold ${overallReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {overallReturn >= 0 ? '+' : ''}{overallReturn.toFixed(2)}%
            </p>
          </div>
          <div className="bg-kob-base/50 rounded-lg p-3">
            <p className="text-xs text-kob-text-dim mb-1">Withdrawable</p>
            <p className="text-2xl font-bold text-green-400">${withdrawable.toFixed(2)}</p>
          </div>
        </div>
        
        {/* Secondary Metrics */}
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="text-center">
            <p className="text-kob-text-dim">Highest Banked</p>
            <p className="text-kob-text font-medium">${totalBanked.toFixed(0)}</p>
          </div>
          <div className="text-center">
            <p className="text-kob-text-dim">Open Trades</p>
            <p className="text-kob-text font-medium">{totalTrades}</p>
          </div>
          <div className="text-center">
            <p className="text-kob-text-dim">Combined Equity</p>
            <p className="text-kob-text font-medium">${combinedEquity.toFixed(0)}</p>
          </div>
          <div className="text-center">
            <p className="text-kob-text-dim">Risk Status</p>
            <p className={`font-medium ${
              riskStatus === 'HEALTHY' ? 'text-green-400' : 
              riskStatus === 'PAUSED' ? 'text-amber-400' : 
              'text-red-400'
            }`}>{riskStatus}</p>
          </div>
        </div>
      </div>
      
      {/* Channel Toggle Strip */}
      {channels && channels.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-kob-text">
              Active Channels: {activeChannels} / {totalChannels}
            </h3>
            <Link to="/settings" className="text-xs text-kob-red hover:underline">
              Manage
            </Link>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 hide-scrollbar">
            {channels.map((channel) => (
              <div
                key={channel.channel_id}
                className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium ${
                  channel.enabled
                    ? 'bg-green-900/30 text-green-400 border border-green-400/30'
                    : 'bg-kob-app text-kob-text-dim border border-kob-border'
                }`}
              >
                {channel.display_name}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Accounts List */}
      <div>
        <h3 className="text-lg font-semibold text-kob-text mb-4">Accounts</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {accounts?.map((account) => (
            <AccountCard key={account.account_key} account={account} />
          ))}
          
          {accounts?.length === 0 && (
            <div className="card text-center py-12 col-span-full">
              <p className="text-kob-text-dim mb-4">No accounts configured yet</p>
              <Link to="/accounts">
                <button type="button" className="btn-primary">
                  Add Your First Account
                </button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
