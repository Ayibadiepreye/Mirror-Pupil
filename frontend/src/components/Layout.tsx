import { Outlet, Link, useLocation } from 'react-router-dom'
import { Home, Users, TrendingUp, History, Settings } from 'lucide-react'

export default function Layout() {
  const location = useLocation()
  
  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }
  
  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/accounts', icon: Users, label: 'Accounts' },
    { path: '/trades', icon: TrendingUp, label: 'Trades' },
    { path: '/history', icon: History, label: 'History' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]
  
  return (
    <div className="min-h-screen bg-kob-app flex flex-col">
      {/* Header */}
      <header className="bg-kob-crimson border-b border-kob-border px-4 py-3 sticky top-0 z-50">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">Mirror Pupil v5.1</h1>
          <div className="flex items-center gap-2">
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
