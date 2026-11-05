import { describe, it, expect } from 'vitest'
import {
  mockUser,
  mockGame,
  mockStats,
  mockLeaderboardEntry,
  mockLeaderboard,
} from './index'

describe('mock factories', () => {
  it('returns the documented API shapes', () => {
    expect(mockUser()).toMatchObject({
      user_id: expect.any(String),
      email: expect.any(String),
      username: expect.any(String),
      created_at: expect.any(String),
    })
    expect(mockGame()).toMatchObject({
      game_id: expect.any(String),
      game_mode: 'custom',
      word_length: 5,
      max_turns: 6,
      status: 'in_progress',
      guesses: [],
      feedback: [],
    })
    expect(mockStats()).toMatchObject({
      games_played: expect.any(Number),
      win_rate: expect.any(Number),
      guess_distribution: expect.any(Object),
    })
    expect(mockLeaderboard()).toMatchObject({
      leaderboard: expect.any(Array),
      current_user_rank: expect.any(Number),
    })
  })

  it('returns a fresh object on every call', () => {
    const a = mockGame()
    const b = mockGame()
    expect(a).not.toBe(b)
    expect(a.guesses).not.toBe(b.guesses)
  })

  it('merges overrides', () => {
    expect(mockGame({ status: 'won', word_length: 7 }).status).toBe('won')
    expect(mockGame({ word_length: 7 }).word_length).toBe(7)
    expect(mockUser({ username: 'other' }).username).toBe('other')
  })

  it('produces consistent leaderboard entries', () => {
    const lb = mockLeaderboard({
      leaderboard: [mockLeaderboardEntry({ rank: 3 })],
    })
    expect(lb.leaderboard[0].rank).toBe(3)
    expect(lb.current_user_rank).toBe(1)
  })
})
