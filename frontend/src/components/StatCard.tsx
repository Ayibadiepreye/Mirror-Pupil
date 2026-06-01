import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string
  icon: LucideIcon
  trend?: 'up' | 'down'
  valueColor?: string
}

export default function StatCard({ title, value, icon: Icon, trend, valueColor }: StatCardProps) {
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs text-kob-text-dim uppercase tracking-wide">{title}</p>
        <div className={`p-2 rounded-lg ${
          trend === 'up' ? 'bg-green-900/30' : 
          trend === 'down' ? 'bg-red-900/30' : 
          'bg-kob-app'
        }`}>
          <Icon size={16} className={
            trend === 'up' ? 'text-green-400' : 
            trend === 'down' ? 'text-red-400' : 
            'text-kob-text-dim'
          } />
        </div>
      </div>
      <p className={`text-2xl font-bold ${valueColor || 'text-kob-text'}`}>
        {value}
      </p>
    </div>
  )
}
