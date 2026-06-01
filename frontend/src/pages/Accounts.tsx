import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '../lib/api'
import AccountCard from '../components/AccountCard'

export default function Accounts() {
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-kob-text-dim">Loading accounts...</div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-kob-text mb-2">Accounts</h2>
          <p className="text-kob-text-dim">Manage your TradeLocker accounts</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          Add Account
        </button>
      </div>
      
      {/* Accounts List */}
      <div className="space-y-4">
        {accounts?.map((account) => (
          <AccountCard key={account.account_key} account={account} />
        ))}
        
        {accounts?.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-kob-text-dim mb-4">No accounts configured yet</p>
            <button className="btn-primary">
              Add Your First Account
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
