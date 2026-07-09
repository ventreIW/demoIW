import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('sw.js', () => {
  let swContent: string

  beforeAll(() => {
    const swPath = path.resolve(__dirname, '../../../../frontend/public/sw.js')
    swContent = fs.readFileSync(swPath, 'utf-8')
  })

  it('registers an install event listener', () => {
    expect(swContent).toContain("self.addEventListener('install'")
  })

  it('calls skipWaiting on install', () => {
    expect(swContent).toContain('skipWaiting()')
  })

  it('registers an activate event listener', () => {
    expect(swContent).toContain("self.addEventListener('activate'")
  })

  it('calls clients.claim on activate', () => {
    expect(swContent).toContain('clients.claim()')
  })

  it('registers a fetch event listener', () => {
    expect(swContent).toContain("self.addEventListener('fetch'")
  })
})