import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Unmount components between tests (auto-cleanup only works with globals).
afterEach(cleanup)
