import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Power, AlertTriangle, PlayCircle, StopCircle, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

export default function BotControl() {
  const queryClient = useQueryClient()
  const [showForceCloseModal, setShowForceCloseModal] = useState(false)
  const [forceCloseTarget, setForceCloseTarget] = useState<string | null>(null)
  
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 3000,
  })
  
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
  })
  
  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: api.getChannels,
  })
  
  const controlBotMutation = useMutation({
    mutationFn: (action: 'start' | 'stop') => api.controlBot(action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bot-status'] })
    },
  })
  
  const forceCloseAllMutation = useMutation({
    mutationFn: () => api.forceCloseAllPositions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-trades'] })
      queryClient.invalidateQueries({ queryKey: ['bot-status'] })
      setShowForceCloseModal(false)
    },
  })
  
  const forceCloseAccountMutation = useMutation({
    mutationFn: (accountKey: string) => api.forceCloseAccountPositions(accountKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-trades'] })
      queryClient.invalidateQueries({ queryKey: ['bot-status'] })
      setShowForceCloseModal(false)
    },
  })
  
  const skipSignalMutation = useMutation({
    mutationFn: (channelId: number) => api.skipNextSignal(channelId),
  })
  
  const isRunning = botStatus?.status === 'running'
  const isDryRun = botStatus?.dry_run || false
  
  const handleBotControl = () => {
    controlBotMutation.mutate(isRunning ? 'stop' : 'start')
  }
  
  const handleForceClose = () => {
    if (forceCloseTarget) {
      forceCloseAccountMutation.mutate(forceCloseTarget)
    } else {
      forceCloseAllMutation.mutate()
    }
  }
  
  const handleSkipSignal = (channelId: number) => {
    skipSignalMutation.mutate(channelId)
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Bot Control</h2>
        <p className="text-kob-text-dim">Manage bot operations and settings</p>
      </div>
      
      {/* Signal Monitoring Card */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <Power size={20} className="text-kob-red" />
          <h3 className="text-lg font-semibold text-kob-text">Signal Monitoring</h3>
        </div>
        
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
            <span className="text-kob-text font-medium">
              {isRunning ? 'RUNNING' : 'STOPPED'}
            </span>
          </div>
        </div>
        
        <button
          type="button"
          onClick={handleBotControl}
          disabled={controlBotMutation.isPending}
          className={`w-full py-3 rounded-lg font-semibold text-white transition-all ${
            isRunning
              ? 'bg-red-600 hover:bg-red-700'
              : 'bg-green-600 hover:bg-green-700'
          } disabled:opacity-50`}
        >
          {controlBotMutation.isPending ? (
            'Processing...'
          ) : isRunning ? (
            <>
              <StopCircle size={20} className="inline mr-2" />
              Stop Bot
            </>
          ) : (
            <>
              <PlayCircle size={20} className="inline mr-2" />
              Start Bot
            </>
          )}
        </button>
      </div>
      
      {/* Dry-Run Mode Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-kob-text">Dry-Run Mode</h3>
            <p className="text-xs text-kob-text-dim mt-1">
              Simulate trades without real execution
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isDryRun}
              className="sr-only peer"
              readOnly
            />
            <div className="w-14 h-7 bg-kob-app peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-kob-red rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-kob-red"></div>
          </label>
        </div>
        
        {isDryRun && (
          <div className="bg-red-900/20 border border-red-400/30 rounded-lg p-3 animate-pulse">
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertTriangle size={16} />
              <span className="font-medium">DRY-RUN MODE ACTIVE</span>
            </div>
          </div>
        )}
      </div>
      
      {/* Weekend Trading Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-kob-text">Weekend Trading</h3>
            <p className="text-xs text-kob-text-dim mt-1">
              Allow trading on weekends
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={false}
              className="sr-only peer"
              readOnly
            />
            <div className="w-14 h-7 bg-kob-app peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-kob-red rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
          </label>
        </div>
      </div>
      
      {/* EOD Trading Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-kob-text">EOD Trading</h3>
            <p className="text-xs text-kob-text-dim mt-1">
              Close all positions at end of day
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={false}
              className="sr-only peer"
              readOnly
            />
            <div className="w-14 h-7 bg-kob-app peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-kob-red rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
          </label>
        </div>
      </div>
      
      {/* Emergency Actions Card */}
      <div className="card border-red-400/30">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle size={20} className="text-red-400" />
          <h3 className="text-lg font-semibold text-kob-text">Emergency Actions</h3>
        </div>
        
        <button
          type="button"
          onClick={() => {
            setForceCloseTarget(null)
            setShowForceCloseModal(true)
          }}
          className="w-full py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition-all"
        >
          Force Close All Positions ({botStatus?.total_active_trades || 0})
        </button>
        
        {accounts && accounts.length > 1 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-kob-text-dim">Per-Account Force Close:</p>
            {accounts.map((account) => (
              <button
                key={account.account_key}
                type="button"
                onClick={() => {
                  setForceCloseTarget(account.account_key)
                  setShowForceCloseModal(true)
                }}
                className="w-full py-2 bg-kob-app hover:bg-kob-base text-kob-text rounded-lg text-sm transition-all"
              >
                Close {account.display_name || account.account_key}
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Skip Next Signal Card */}
      {channels && channels.filter(c => c.enabled).length > 0 && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <RefreshCw size={20} className="text-kob-red" />
            <h3 className="text-lg font-semibold text-kob-text">Skip Next Signal</h3>
          </div>
          
          <div className="space-y-2">
            {channels.filter(c => c.enabled).map((channel) => (
              <button
                key={channel.channel_id}
                type="button"
                onClick={() => handleSkipSignal(channel.channel_id)}
                disabled={skipSignalMutation.isPending}
                className="w-full py-2 bg-kob-app hover:bg-kob-base text-kob-text rounded-lg text-sm transition-all disabled:opacity-50"
              >
                {skipSignalMutation.isPending ? 'Processing...' : `Skip next from ${channel.display_name}`}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Force Close Confirmation Modal */}
      {showForceCloseModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-kob-base rounded-lg max-w-md w-full p-6">
            <div className="flex flex-col items-center text-center">
              <AlertTriangle size={48} className="text-red-400 mb-4" />
              <h3 className="text-xl font-bold text-kob-text mb-2">
                Force Close All Positions?
              </h3>
              <p className="text-kob-text-dim mb-6">
                This will immediately close all {botStatus?.total_active_trades || 0} active trades
                {forceCloseTarget && ` for this account`}.
                This action cannot be undone.
              </p>
              
              <div className="flex gap-3 w-full">
                <button
                  type="button"
                  onClick={() => {
                    setShowForceCloseModal(false)
                    setForceCloseTarget(null)
                  }}
                  disabled={forceCloseAllMutation.isPending || forceCloseAccountMutation.isPending}
                  className="flex-1 py-2 bg-kob-app text-kob-text rounded-lg hover:bg-kob-base disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleForceClose}
                  disabled={forceCloseAllMutation.isPending || forceCloseAccountMutation.isPending}
                  className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {(forceCloseAllMutation.isPending || forceCloseAccountMutation.isPending) ? 'Closing...' : 'Force Close'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
