"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Moon, Sun, Monitor, ChevronDown } from "lucide-react"

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  // Avoid hydration mismatch by only rendering after mount
  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className="w-[110px] h-9 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900" />
  }

  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-slate-500 dark:text-slate-400">
        {theme === 'light' && <Sun className="w-4 h-4" />}
        {theme === 'dark' && <Moon className="w-4 h-4" />}
        {theme === 'system' && <Monitor className="w-4 h-4" />}
      </div>
      <select
        value={theme}
        onChange={(e) => setTheme(e.target.value)}
        className="w-[110px] h-9 pl-9 pr-8 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg appearance-none cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Select theme"
      >
        <option value="light">Light</option>
        <option value="dark">Dark</option>
        <option value="system">System</option>
      </select>
      <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-500 dark:text-slate-400">
        <ChevronDown className="w-4 h-4" />
      </div>
    </div>
  )
}
