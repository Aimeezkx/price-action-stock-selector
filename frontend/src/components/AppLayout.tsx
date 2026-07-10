import { Activity, BarChart3, BookOpenCheck, CandlestickChart, FlaskConical, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const navigation = [
  { to: '/', label: '总览', icon: Activity, end: true },
  { to: '/scanner', label: '扫描器', icon: CandlestickChart },
  { to: '/chart/AAPL', label: 'K 线分析', icon: BarChart3 },
  { to: '/rules', label: '规则库', icon: BookOpenCheck },
  { to: '/backtest', label: '回测', icon: FlaskConical },
]

export function AppLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="app-shell">
      <aside className={open ? 'sidebar sidebar-open' : 'sidebar'}>
        <div className="brand">
          <div className="brand-mark"><CandlestickChart size={22} /></div>
          <div><strong>PA Selector</strong><span>Price action research</span></div>
          <button className="icon-button sidebar-close" onClick={() => setOpen(false)} aria-label="关闭导航"><X size={20} /></button>
        </div>
        <nav>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" />
          <p><strong>只读研究模式</strong><br />不发送任何订单</p>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setOpen(true)} aria-label="打开导航"><Menu size={20} /></button>
          <div><span className="eyebrow">DAILY · IBKR · EXPLAINABLE</span></div>
          <div className="market-pill"><span /> US EOD</div>
        </header>
        <div className="content"><Outlet /></div>
      </main>
      {open && <button className="backdrop" onClick={() => setOpen(false)} aria-label="关闭导航遮罩" />}
    </div>
  )
}
