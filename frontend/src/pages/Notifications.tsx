import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, AlertCircle, Info, X, CheckCheck, Bell, Zap } from 'lucide-react'
import { api } from '../lib/api'
import { Notification } from '../types'
import { formatTimeAgo } from '../lib/utils'

export default function Notifications() {
  const queryClient = useQueryClient()
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)
  
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', showUnreadOnly],
    queryFn: () => api.getNotifications(showUnreadOnly, 200),
    refetchInterval: 5000,
  })
  
  const markReadMutation = useMutation({
    mutationFn: (notificationId: number) => api.markNotificationRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
  
  const markAllReadMutation = useMutation({
    mutationFn: () => api.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
  
  const deleteMutation = useMutation({
    mutationFn: (notificationId: number) => api.deleteNotification(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
  
  const unreadCount = notifications.filter((n: Notification) => !n.read).length
  const criticalNotifications = notifications.filter(
    (n: Notification) => n.severity === 'CRITICAL' && !n.read
  )
  
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'SIGNAL':
        return <Zap size={18} className="text-blue-400" />
      case 'EXECUTION':
        return <CheckCheck size={18} className="text-green-400" />
      case 'MANAGEMENT':
        return <Info size={18} className="text-purple-400" />
      case 'BREACH':
        return <AlertTriangle size={18} className="text-red-400" />
      case 'SYSTEM':
        return <AlertCircle size={18} className="text-amber-400" />
      default:
        return <Bell size={18} className="text-kob-text-dim" />
    }
  }
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'border-l-4 border-red-500 bg-red-900/10'
      case 'ERROR':
        return 'border-l-4 border-orange-500 bg-orange-900/10'
      case 'WARNING':
        return 'border-l-4 border-yellow-500 bg-yellow-900/10'
      case 'INFO':
        return 'border-l-4 border-blue-500 bg-blue-900/10'
      default:
        return 'border-l-4 border-kob-border'
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-kob-text mb-2">Notifications</h2>
          <p className="text-kob-text-dim">
            {unreadCount} unread • {notifications.length} total
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => markAllReadMutation.mutate()}
            disabled={unreadCount === 0 || markAllReadMutation.isPending}
            className="btn-ghost text-sm flex items-center gap-2"
          >
            <CheckCheck size={16} />
            Mark All Read
          </button>
        </div>
      </div>
      
      {/* Critical Banner */}
      {criticalNotifications.length > 0 && (
        <div className="bg-gradient-to-r from-red-900/40 to-red-800/20 border-2 border-red-500/50 rounded-xl p-5 shadow-lg">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <AlertTriangle size={28} className="text-red-400" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-red-400">Critical Alerts</h3>
              <p className="text-sm text-kob-text-dim">{criticalNotifications.length} urgent notification{criticalNotifications.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <div className="space-y-2">
            {criticalNotifications.map((notification: Notification) => (
              <div key={notification.notification_id} className="bg-kob-base rounded-lg p-4 flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-semibold text-kob-text mb-1">{notification.title}</p>
                  <p className="text-sm text-kob-text-dim">{notification.message}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-kob-text-dim">{formatTimeAgo(notification.created_at)}</span>
                    {notification.account_key && (
                      <span className="text-xs px-2 py-0.5 rounded bg-kob-crimson/30 text-kob-text-dim">
                        {notification.account_key.split(':')[0]}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(notification.notification_id)}
                  className="text-kob-text-dim hover:text-kob-text ml-3"
                  aria-label="Delete notification"
                  title="Delete notification"
                >
                  <X size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Filter Toggle */}
      <div className="card">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={showUnreadOnly}
            onChange={(e) => setShowUnreadOnly(e.target.checked)}
            className="w-5 h-5 rounded border-kob-border bg-kob-app text-kob-red focus:ring-2 focus:ring-kob-red"
          />
          <span className="text-kob-text font-medium">Show unread only</span>
        </label>
      </div>
      
      {/* Notification List */}
      <div className="space-y-3">
        {notifications.map((notification: Notification) => (
          <div
            key={notification.notification_id}
            className={`card ${getSeverityColor(notification.severity)} ${
              !notification.read ? 'shadow-lg' : 'opacity-75'
            } transition-all hover:shadow-xl`}
          >
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 mt-1">
                {getCategoryIcon(notification.category)}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-kob-text">{notification.title}</h4>
                      {!notification.read && (
                        <span className="w-2 h-2 rounded-full bg-kob-red animate-pulse"></span>
                      )}
                    </div>
                    <p className="text-sm text-kob-text-dim leading-relaxed">
                      {notification.message}
                    </p>
                  </div>
                  
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {!notification.read && (
                      <button
                        onClick={() => markReadMutation.mutate(notification.notification_id)}
                        className="text-kob-text-dim hover:text-kob-text"
                        title="Mark as read"
                        aria-label="Mark as read"
                      >
                        <CheckCheck size={18} />
                      </button>
                    )}
                    <button
                      onClick={() => deleteMutation.mutate(notification.notification_id)}
                      className="text-kob-text-dim hover:text-red-400"
                      title="Delete"
                      aria-label="Delete"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`badge ${
                    notification.severity === 'CRITICAL' ? 'badge-danger' :
                    notification.severity === 'ERROR' ? 'bg-orange-900 text-orange-200' :
                    notification.severity === 'WARNING' ? 'badge-warning' :
                    'badge-info'
                  }`}>
                    {notification.severity}
                  </span>
                  
                  <span className="text-xs px-2 py-0.5 rounded bg-kob-app text-kob-text-dim">
                    {notification.category}
                  </span>
                  
                  <span className="text-xs text-kob-text-dim">
                    {formatTimeAgo(notification.created_at)}
                  </span>
                  
                  {notification.account_key && (
                    <span className="text-xs px-2 py-0.5 rounded bg-kob-crimson/30 text-kob-text-dim">
                      {notification.account_key.split(':')[0]}
                    </span>
                  )}
                </div>
                
                {notification.metadata && Object.keys(notification.metadata).length > 0 && (
                  <details className="mt-3">
                    <summary className="text-xs text-kob-red hover:underline cursor-pointer">
                      Show details
                    </summary>
                    <div className="mt-2 p-3 bg-kob-app rounded text-xs font-mono text-kob-text-dim overflow-x-auto">
                      <pre>{JSON.stringify(notification.metadata, null, 2)}</pre>
                    </div>
                  </details>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {notifications.length === 0 && (
          <div className="card text-center py-16">
            <div className="inline-block p-4 bg-kob-crimson/20 rounded-full mb-4">
              <Bell size={48} className="text-kob-text-dim" />
            </div>
            <p className="text-xl text-kob-text mb-2">No notifications</p>
            <p className="text-sm text-kob-text-dim">
              {showUnreadOnly ? 'All caught up! No unread notifications.' : 'You\'re all set!'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
