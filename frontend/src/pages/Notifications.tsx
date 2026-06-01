import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, AlertCircle, Info, X, ChevronDown, ChevronUp, Bell } from 'lucide-react'
import { api } from '../lib/api'

// Notification type from backend
interface Notification {
  id: number
  severity: 'CRITICAL' | 'HIGH' | 'WARNING' | 'INFO'
  message: string
  timestamp: string
  account_key?: string
  details?: any
}

export default function Notifications() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'WARNING' | 'INFO'>('ALL')
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', filter],
    queryFn: () => api.getNotifications(filter === 'ALL' ? undefined : filter),
    refetchInterval: 5000,
  })
  
  const dismissMutation = useMutation({
    mutationFn: (id: number) => api.dismissNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
  
  const filteredNotifications = notifications
  
  const criticalNotifications = notifications.filter((n: Notification) => n.severity === 'CRITICAL')
  
  const counts = {
    ALL: notifications.length,
    CRITICAL: notifications.filter((n: Notification) => n.severity === 'CRITICAL').length,
    HIGH: notifications.filter((n: Notification) => n.severity === 'HIGH').length,
    WARNING: notifications.filter((n: Notification) => n.severity === 'WARNING').length,
    INFO: notifications.filter((n: Notification) => n.severity === 'INFO').length,
  }
  
  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }
  
  const dismissNotification = (id: number) => {
    dismissMutation.mutate(id)
  }
  
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'HIGH':
        return <AlertTriangle size={20} className="text-red-400" />
      case 'WARNING':
        return <AlertCircle size={20} className="text-amber-400" />
      case 'INFO':
        return <Info size={20} className="text-blue-400" />
      default:
        return <Info size={20} className="text-kob-text-dim" />
    }
  }
  
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-danger">{severity}</span>
      case 'HIGH':
        return <span className="badge bg-red-800 text-red-200">{severity}</span>
      case 'WARNING':
        return <span className="badge badge-warning">{severity}</span>
      case 'INFO':
        return <span className="badge badge-info">{severity}</span>
      default:
        return <span className="badge">{severity}</span>
    }
  }
  
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-kob-text mb-2">Notifications</h2>
        <p className="text-kob-text-dim">System alerts and messages</p>
      </div>
      
      {/* Critical Banner */}
      {criticalNotifications.length > 0 && (
        <div className="bg-red-900/30 border border-red-400/50 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <AlertTriangle size={24} className="text-red-400" />
            <h3 className="text-lg font-semibold text-red-400">Critical Alerts</h3>
          </div>
          <div className="space-y-2">
            {criticalNotifications.map((notification: Notification) => (
              <div key={notification.id} className="flex items-start justify-between bg-kob-base/50 rounded p-3">
                <div className="flex-1">
                  <p className="text-kob-text text-sm">{notification.message}</p>
                  <p className="text-xs text-kob-text-dim mt-1">
                    {formatTimestamp(notification.timestamp)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => dismissNotification(notification.id)}
                  className="text-kob-text-dim hover:text-kob-text ml-2"
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Severity Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        {(['ALL', 'CRITICAL', 'HIGH', 'WARNING', 'INFO'] as const).map((severity) => (
          <button
            key={severity}
            type="button"
            onClick={() => setFilter(severity)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === severity
                ? 'bg-kob-red text-white'
                : 'bg-kob-app text-kob-text hover:bg-kob-base'
            }`}
          >
            {severity} ({counts[severity]})
          </button>
        ))}
      </div>
      
      {/* Notification List */}
      <div className="space-y-3">
        {filteredNotifications.map((notification: Notification) => {
          const isExpanded = expandedIds.has(notification.id)
          
          return (
            <div key={notification.id} className="card">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  {getSeverityIcon(notification.severity)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-kob-text text-sm flex-1">{notification.message}</p>
                    <button
                      type="button"
                      onClick={() => dismissNotification(notification.id)}
                      className="text-kob-text-dim hover:text-kob-text flex-shrink-0"
                    >
                      <X size={16} />
                    </button>
                  </div>
                  
                  <div className="flex items-center gap-2 flex-wrap">
                    {getSeverityBadge(notification.severity)}
                    <span className="text-xs text-kob-text-dim">
                      {formatTimestamp(notification.timestamp)}
                    </span>
                    {notification.account_key && (
                      <span className="text-xs text-kob-text-dim">
                        {notification.account_key}
                      </span>
                    )}
                  </div>
                  
                  {notification.details && (
                    <div className="mt-2">
                      <button
                        type="button"
                        onClick={() => toggleExpand(notification.id)}
                        className="flex items-center gap-1 text-xs text-kob-red hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp size={14} />
                            Hide Details
                          </>
                        ) : (
                          <>
                            <ChevronDown size={14} />
                            Show Details
                          </>
                        )}
                      </button>
                      
                      {isExpanded && (
                        <div className="mt-2 p-3 bg-kob-app rounded text-xs font-mono text-kob-text-dim overflow-x-auto">
                          <pre>{JSON.stringify(notification.details, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
        
        {filteredNotifications.length === 0 && (
          <div className="card text-center py-12">
            <Bell size={48} className="mx-auto text-kob-text-dim mb-4" />
            <p className="text-kob-text-dim">No notifications</p>
            <p className="text-xs text-kob-text-dim mt-2">
              {filter !== 'ALL' ? `No ${filter.toLowerCase()} notifications` : 'All clear!'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
