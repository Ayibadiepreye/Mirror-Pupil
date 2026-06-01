import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface AddAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddAccountModal({ isOpen, onClose, onSuccess }: AddAccountModalProps) {
  const [step, setStep] = useState<'credentials' | 'discover'>('credentials')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Credentials form
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [server, setServer] = useState<'live' | 'demo'>('demo')
  
  // Discovered accounts
  const [discoveredAccounts, setDiscoveredAccounts] = useState<any[]>([])
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set())
  
  if (!isOpen) return null
  
  const handleDiscover = async () => {
    if (!email || !password) {
      setError('Please enter email and password')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const response = await api.discoverAccounts({ email, password, server })
      setDiscoveredAccounts(response.accounts || [])
      setStep('discover')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to discover accounts')
    } finally {
      setLoading(false)
    }
  }
  
  const handleAddAccounts = async () => {
    if (selectedAccounts.size === 0) {
      setError('Please select at least one account')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      await api.bulkAddAccounts({
        email,
        password,
        server,
        account_ids: Array.from(selectedAccounts)
      })
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add accounts')
    } finally {
      setLoading(false)
    }
  }
  
  const handleClose = () => {
    setStep('credentials')
    setEmail('')
    setPassword('')
    setServer('demo')
    setDiscoveredAccounts([])
    setSelectedAccounts(new Set())
    setError('')
    onClose()
  }
  
  const toggleAccount = (accountId: string) => {
    const newSelected = new Set(selectedAccounts)
    if (newSelected.has(accountId)) {
      newSelected.delete(accountId)
    } else {
      newSelected.add(accountId)
    }
    setSelectedAccounts(newSelected)
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-kob-base rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-kob-border">
          <h3 className="text-lg font-semibold text-kob-text">
            {step === 'credentials' ? 'Add TradeLocker Account' : 'Select Accounts'}
          </h3>
          <button onClick={handleClose} className="text-kob-text-dim hover:text-kob-text">
            <X size={20} />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded p-3 text-red-400 text-sm">
              {error}
            </div>
          )}
          
          {step === 'credentials' && (
            <>
              <div>
                <label className="block text-sm text-kob-text-dim mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
                  placeholder="your@email.com"
                />
              </div>
              
              <div>
                <label className="block text-sm text-kob-text-dim mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
                  placeholder="••••••••"
                />
              </div>
              
              <div>
                <label className="block text-sm text-kob-text-dim mb-1">Server</label>
                <select
                  value={server}
                  onChange={(e) => setServer(e.target.value as 'live' | 'demo')}
                  className="w-full bg-kob-app border border-kob-border rounded px-3 py-2 text-kob-text"
                >
                  <option value="demo">Demo</option>
                  <option value="live">Live</option>
                </select>
              </div>
            </>
          )}
          
          {step === 'discover' && (
            <div className="space-y-2">
              <p className="text-sm text-kob-text-dim mb-3">
                Found {discoveredAccounts.length} account(s). Select which to add:
              </p>
              
              {discoveredAccounts.map((account) => (
                <label
                  key={account.id}
                  className="flex items-center gap-3 p-3 bg-kob-app rounded cursor-pointer hover:bg-kob-app/80"
                >
                  <input
                    type="checkbox"
                    checked={selectedAccounts.has(account.id)}
                    onChange={() => toggleAccount(account.id)}
                    className="w-4 h-4"
                  />
                  <div className="flex-1">
                    <p className="text-kob-text font-medium">{account.number}</p>
                    <p className="text-xs text-kob-text-dim">
                      Balance: ${account.balance?.toLocaleString() || '0'}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="flex gap-2 p-4 border-t border-kob-border">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 bg-kob-app text-kob-text rounded hover:bg-kob-app/80"
            disabled={loading}
          >
            Cancel
          </button>
          
          {step === 'credentials' && (
            <button
              onClick={handleDiscover}
              disabled={loading || !email || !password}
              className="flex-1 px-4 py-2 bg-kob-red text-white rounded hover:bg-kob-red/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              Discover Accounts
            </button>
          )}
          
          {step === 'discover' && (
            <button
              onClick={handleAddAccounts}
              disabled={loading || selectedAccounts.size === 0}
              className="flex-1 px-4 py-2 bg-kob-red text-white rounded hover:bg-kob-red/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              Add Selected ({selectedAccounts.size})
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
