import type { ReactNode } from 'react'
import { NextIntlClientProvider } from 'next-intl'
import { render, type RenderOptions } from '@testing-library/react'
import esMessages from '../../messages/es.json'

function IntlWrapper({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="es" messages={esMessages}>
      {children}
    </NextIntlClientProvider>
  )
}

export function renderWithIntl(ui: ReactNode, options?: RenderOptions) {
  return render(ui, { wrapper: IntlWrapper, ...options })
}