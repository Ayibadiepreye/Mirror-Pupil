import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import AccountCard from '../components/AccountCard'
import AddAccountModal from '../components/AddAccountModal'

export default function Accounts() {
  const [showAddModal, setShowAddModal] = useState(false)
  
  const { data: accounts, isLoading, refetch } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  const handleAddSuccess = () => {
    refetch()
  }
  
  const handleDeleteAccount = async (accountKey: string, displayName: string | null) => {
    if (!confirm(`Delete account "${displayName || accountKey}"? This will remove all associated trades and data. This cannot be undone.`)) {
      return
    }
    
    try {
      await api.deleteAccount(accountKey)
      refetch()
    } catch (err) {
      console.error('Failed to delete account:', err)
      alert('Failed to delete account. It may have active trades.')
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-kob-text-dim">Loading accounts...</div>
      </div>
    )
  }
  
  return (
    <>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-kob-text mb-2">Accounts</h2>
            <p className="text-kob-text-dim">Manage your TradeLocker accounts</p>
          </div>
          <button 
            type="button"
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} />
            Add Account
          </button>
        </div>
        
        {/* Accounts List */}
        <div className="space-y-4">
          {accounts?.map((account) => (
            <div key={account.account_key} className="relative group">
              <AccountCard account={account} />
              <button
                type="button"
                onClick={() => handleDeleteAccount(account.account_key, account.display_name)}
                className="absolute top-4 right-4 p-2 bg-kob-base/90 text-kob-text-dim hover:text-red-400 rounded opacity-0 group-hover:opacity-100 transition-all"
                title="Delete account"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          
          {accounts?.length === 0 && (
            <div className="card text-center py-12">
              <p className="text-kob-text-dim mb-4">No accounts configured yet</p>
              <button 
                type="button"
                onClick={() => setShowAddModal(true)}
                className="btn-primary"
              >
                Add Your First Account
              </button>
            </div>
          )}
        </div>
      </div>
      
      <AddAccountModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />
    </>
  )
}
