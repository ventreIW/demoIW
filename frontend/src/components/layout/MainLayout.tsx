'use client'

import { useLocale, useTranslations } from 'next-intl'
import { usePathname } from '@/i18n/routing'
import { cn } from '@/lib/utils'
import LocaleSwitcher from '@/components/locale/LocaleSwitcher'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations()

  return (
    <div className="flex min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:inline-flex focus:h-10 focus:items-center focus:rounded-lg focus:bg-white focus:px-4 focus:text-sm focus:text-slate-900 focus:shadow-lg focus:outline-2 focus:outline-ring"
        tabIndex={0}
      >
        {t('app.skipToContent')}
      </a>
      <Sidebar />
      <main id="main-content" aria-label={t('app.mainContentLabel')} className="flex-1 p-6">
        {children}
      </main>
    </div>
  )
}

function Sidebar() {
  const t = useTranslations()
  const locale = useLocale()
  const pathname = usePathname()

  const links = [
    { href: '/cases', label: t('sidebar.operations') },
    { href: `/${locale}/executive`, label: t('sidebar.executive') },
    { href: '/scenarios', label: t('sidebar.scenarios') },
  ]

  function isActive(href: string): boolean {
    // Compare the locale-agnostic path against pathname
    const normalizedHref = href.replace(`/${locale}`, '') || '/'
    return pathname.startsWith(normalizedHref)
  }

  return (
    <aside className="hidden w-64 flex-shrink-0 border-r bg-slate-50 md:block">
      <div className="flex h-full flex-col">
        <div className="border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-slate-800">{t('app.title')}</span>
            <LocaleSwitcher />
          </div>
        </div>
        <nav aria-label={t('sidebar.navLabel')} className="flex-1 space-y-1 p-4">
          {links.map((link) => (
            <SidebarLink key={link.href} href={link.href} isActive={isActive(link.href)}>
              {link.label}
            </SidebarLink>
          ))}
        </nav>
      </div>
    </aside>
  )
}

function SidebarLink({
  href,
  children,
  isActive,
}: {
  href: string
  children: React.ReactNode
  isActive: boolean
}) {
  return (
    <a
      href={href}
      aria-current={isActive ? 'page' : undefined}
      className={cn(
        'block rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
        isActive
          ? 'bg-slate-200 font-medium text-slate-900'
          : 'text-slate-600 hover:bg-slate-200 hover:text-slate-900',
      )}
    >
      {children}
    </a>
  )
}
