import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, Users, TrendingUp, Settings, Power, Bell } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Layout() {
  const location = useLocation()
  
  // Fetch notification count
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.getNotifications(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })
  
  const notificationCount = notifications.length
  
  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }
  
  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/accounts', icon: Users, label: 'Accounts' },
    { path: '/trades', icon: TrendingUp, label: 'Trades' },
    { path: '/bot-control', icon: Power, label: 'Bot' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]
  
  return (
    <div className="min-h-screen bg-kob-app flex flex-col">
      {/* Header */}
      <header className="bg-kob-crimson border-b border-kob-border px-4 py-3 sticky top-0 z-50">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">Mirror Pupil v5.1</h1>
          <div className="flex items-center gap-4">
            <Link to="/notifications" className="relative">
              <Bell size={20} className="text-white" />
              {notificationCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                  {notificationCount}
                </span>
              )}
            </Link>
            <span className="text-xs text-white/80">Knights of the Blood Oath</span>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="flex-1 overflow-y-auto pb-20">
        <div className="container mx-auto px-4 py-6">
          <Outlet />
        </div>
      </main>
      
      {/* Bottom Navigation */}
      <nav className="bg-kob-base border-t border-kob-border fixed bottom-0 left-0 right-0 z-50">
        <div className="flex items-center justify-around py-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.path)
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-all ${
                  active
                    ? 'text-kob-red bg-kob-app'
                    : 'text-kob-text-dim hover:text-kob-text hover:bg-kob-app/50'
                }`}
              >
                <Icon size={20} />
                <span className="text-xs font-medium">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
