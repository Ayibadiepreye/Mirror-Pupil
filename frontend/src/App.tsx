import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import ActiveTrades from './pages/ActiveTrades'
import TradeHistory from './pages/TradeHistory'
import Settings from './pages/Settings'
import BotControl from './pages/BotControl'
import Notifications from './pages/Notifications'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="accounts" element={<Accounts />} />
            <Route path="accounts/:accountKey" element={<AccountDetail />} />
            <Route path="trades" element={<ActiveTrades />} />
            <Route path="history" element={<TradeHistory />} />
            <Route path="settings" element={<Settings />} />
            <Route path="bot-control" element={<BotControl />} />
            <Route path="notifications" element={<Notifications />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
