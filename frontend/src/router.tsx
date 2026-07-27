import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { BacktestPage } from './pages/BacktestPage'
import { ChartPage } from './pages/ChartPage'
import { DashboardPage } from './pages/DashboardPage'
import { RulesPage } from './pages/RulesPage'
import { ScannerPage } from './pages/ScannerPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'scanner', element: <ScannerPage /> },
      { path: 'chart/:symbol', element: <ChartPage /> },
      { path: 'rules', element: <RulesPage /> },
      { path: 'backtest', element: <BacktestPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])
