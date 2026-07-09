'use client'

import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}

function Sidebar() {
  const t = useTranslations()

  return (
    <aside className="hidden w-64 flex-shrink-0 border-r bg-slate-50 md:block">
      <div className="flex h-full flex-col">
        <div className="border-b px-6 py-4">
          <span className="text-lg font-semibold text-slate-800">{t('app.title')}</span>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          <SidebarLink href="#">{t('sidebar.operations')}</SidebarLink>
          <SidebarLink href="#">{t('sidebar.executive')}</SidebarLink>
          <SidebarLink href="/scenarios">{t('sidebar.scenarios')}</SidebarLink>
        </nav>
      </div>
    </aside>
  )
}

function SidebarLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className={cn(
        'block rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-200 hover:text-slate-900',
      )}
    >
      {children}
    </a>
  )
}