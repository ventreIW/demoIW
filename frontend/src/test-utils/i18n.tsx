import type { ReactNode } from 'react'
import { NextIntlClientProvider } from 'next-intl'
import { render, type RenderOptions } from '@testing-library/react'
import esMessages from '../../messages/es.json'
import enMessages from '../../messages/en.json'

const messagesByLocale: Record<string, typeof esMessages> = {
  es: esMessages,
  en: enMessages,
}

function IntlWrapper({ children, locale = 'es' }: { children: ReactNode; locale?: string }) {
  return (
    <NextIntlClientProvider locale={locale} messages={messagesByLocale[locale] ?? esMessages}>
      {children}
    </NextIntlClientProvider>
  )
}

export function renderWithIntl(
  ui: ReactNode,
  options?: RenderOptions & { locale?: string },
) {
  const { locale, ...renderOptions } = options ?? {}
  return render(ui, {
    wrapper: ({ children }) => <IntlWrapper locale={locale}>{children}</IntlWrapper>,
    ...renderOptions,
  })
}
