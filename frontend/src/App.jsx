import React, { useState, useEffect } from 'react'
import { 
  Flame, 
  Heart, 
  Calendar, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Award, 
  Clock, 
  User, 
  TrendingUp, 
  AlertTriangle 
} from 'lucide-react'

export default function App() {
  const [memberId, setMemberId] = useState(1)
  const [member, setMember] = useState(null)
  const [streak, setStreak] = useState(null)
  const [slots, setSlots] = useState([])
  const [bookings, setBookings] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancellingBooking, setCancellingBooking] = useState(null)
  const [cancelModalOpen, setCancelModalOpen] = useState(false)
  const [appealReason, setAppealReason] = useState('')
  const [appealMessage, setAppealMessage] = useState(null)

  // Fetch all state
  const fetchData = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true)
      // 1. Fetch slots
      try {
        const slotsRes = await fetch('/api/v1/slots')
        if (slotsRes.ok) {
          setSlots(await slotsRes.json())
        }
      } catch (e) {
        console.error('Error fetching slots', e)
      }

      // 2. Fetch member & streak
      try {
        const memRes = await fetch(`/api/v1/members/${memberId}`)
        if (memRes.ok) {
          setMember(await memRes.json())
        }
        const streakRes = await fetch(`/api/v1/streak/status?member_id=${memberId}`)
        if (streakRes.ok) {
          setStreak(await streakRes.json())
        }
      } catch (e) {
        console.error('Error fetching member/streak', e)
      }

      // 3. Fetch bookings
      try {
        const bookRes = await fetch(`/api/v1/bookings?member_id=${memberId}`)
        if (bookRes.ok) {
          setBookings(await bookRes.json())
        }
      } catch (e) {
        console.error('Error fetching bookings', e)
      }

      // 4. Fetch analytics
      try {
        const anaRes = await fetch('/api/v1/analytics/occupancy')
        if (anaRes.ok) {
          setAnalytics(await anaRes.json())
        }
      } catch (e) {
        console.error('Error fetching analytics', e)
      }

      setError(null)
    } catch (err) {
      console.error(err)
      if (isInitial) setError('Failed to connect to backend server. Ensure backend is running.')
    } finally {
      if (isInitial) setLoading(false)
    }
  }

  // Initial fetch and auto-refresh interval (every 3 seconds)
  useEffect(() => {
    fetchData(true)
    const interval = setInterval(() => {
      fetchData(false)
    }, 3000)
    return () => clearInterval(interval)
  }, [memberId])

  // Book a class
  const handleBookSlot = async (slotId) => {
    try {
      const res = await fetch('/api/v1/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ member_id: memberId, slot_id: slotId })
      })
      const data = await res.json()
      if (!res.ok) {
        alert(`Booking Failed: ${data.detail || 'Error'}`)
      } else {
        alert('Class Booked Successfully!')
        fetchData()
      }
    } catch (err) {
      alert('Error booking slot')
    }
  }

  // Complete a booking
  const handleCompleteBooking = async (bookingId) => {
    try {
      const res = await fetch(`/api/v1/bookings/${bookingId}/complete`, { method: 'POST' })
      if (res.ok) {
        alert('Check-in confirmed! Attended count updated.')
        fetchData()
      } else {
        const data = await res.json()
        alert(`Check-in failed: ${data.detail}`)
      }
    } catch (err) {
      alert('Error checking in')
    }
  }

  // Indian Date Format Helpers (DD/MM/YYYY)
  const formatIndianDate = (dateVal) => {
    if (!dateVal) return ''
    const d = new Date(typeof dateVal === 'string' && !dateVal.endsWith('Z') && !dateVal.includes('+') ? `${dateVal}Z` : dateVal)
    return d.toLocaleDateString('en-GB') // formats as DD/MM/YYYY
  }

  const formatIndianDateTime = (dateVal) => {
    if (!dateVal) return ''
    const d = new Date(typeof dateVal === 'string' && !dateVal.endsWith('Z') && !dateVal.includes('+') ? `${dateVal}Z` : dateVal)
    return `${d.toLocaleDateString('en-GB')} at ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }

  // Pre-cancel evaluation (Checks if < 2 hours)
  const initiateCancel = (booking) => {
    // Resolve slot from booking.slot or fallback to slots list
    const slot = booking.slot || slots.find(s => s.id === booking.slot_id)
    const slotStartStr = slot?.start_time
    let slotStartTime
    if (slotStartStr) {
      slotStartTime = new Date(typeof slotStartStr === 'string' && !slotStartStr.endsWith('Z') && !slotStartStr.includes('+') ? `${slotStartStr}Z` : slotStartStr).getTime()
    } else {
      slotStartTime = Date.now() + 3 * 3600 * 1000 // default future if unknown
    }

    const nowTime = Date.now()
    const diffHours = (slotStartTime - nowTime) / (1000 * 60 * 60)

    setCancellingBooking(booking)
    if (diffHours < 2) {
      setCancelModalOpen(true)
    } else {
      executeCancel(booking.id)
    }
  }

  // Execute cancel
  const executeCancel = async (bookingId) => {
    try {
      const res = await fetch(`/api/v1/bookings/${bookingId}`, { method: 'DELETE' })
      const data = await res.json()
      setCancelModalOpen(false)
      if (data.penalty_applied) {
        alert(`Warning: ${data.warning} (+1 penalty point added)`)
      } else {
        alert('Booking cancelled cleanly with zero penalties.')
      }
      fetchData()
    } catch (err) {
      alert('Error cancelling booking')
    }
  }

  // Submit support appeal
  const handleSupportAppeal = async (e) => {
    e.preventDefault()
    if (!appealReason.trim()) return
    try {
      const res = await fetch('/api/v1/support/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ member_id: memberId, reason: appealReason })
      })
      if (res.ok) {
        const ticket = await res.json()
        // Auto-approve simulation for quick demo
        const resolveRes = await fetch(`/api/v1/support/tickets/${ticket.id}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'APPROVE' })
        })
        if (resolveRes.ok) {
          setAppealMessage('Appeal Approved! Penalty points reset to 0 and all restrictions lifted.')
          setAppealReason('')
          fetchData()
        }
      }
    } catch (err) {
      alert('Error submitting appeal')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Sticky Restriction Banner (Mandatory UI requirement) */}
      {member?.restriction_status && member.restriction_status !== 'NONE' && (
        <div className="bg-red-600/90 text-white px-4 py-3 sticky top-0 z-50 shadow-lg flex items-center justify-between border-b border-red-500">
          <div className="flex items-center space-x-3 container mx-auto">
            <ShieldAlert className="w-6 h-6 animate-pulse" />
            <span className="font-semibold text-sm md:text-base">
              {member.restriction_status === 'FROZEN' ? (
                <>ACCOUNT FROZEN: Booking privileges suspended until {formatIndianDateTime(member.restriction_until)}.</>
              ) : (
                <>SAME-DAY RESTRICTION ACTIVE: You can only book classes starting within 2 hours until {formatIndianDate(member.restriction_until)}.</>
              )}
            </span>
          </div>
        </div>
      )}

      {/* Navigation Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-500 to-amber-400 flex items-center justify-center text-xl shadow-lg shadow-orange-500/20">
              🏋️
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Apex Fitness Portal</h1>
              <p className="text-xs text-slate-400">Automated Streaks & Facility Booking</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-medium text-slate-200">{member?.name || 'Member'}</div>
              <div className="text-xs text-orange-400 font-semibold">{member?.membership_type || 'BASIC'} PLAN</div>
            </div>
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <User className="w-5 h-5" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container mx-auto px-4 py-8 flex-1 space-y-8">
        {/* Gamified Streak & Protection Dashboard */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 1. Streak Flame Card */}
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-orange-400">Current Streak</span>
                <div className="text-4xl font-extrabold text-white mt-1 flex items-center gap-2">
                  <Flame className="w-8 h-8 text-orange-500 animate-bounce" />
                  {streak?.current_streak_weeks || 0} <span className="text-lg font-medium text-slate-400">Weeks</span>
                </div>
              </div>
              <div className="p-3 bg-orange-500/10 rounded-xl border border-orange-500/20">
                <Flame className="w-6 h-6 text-orange-400" />
              </div>
            </div>

            <div className="mt-6">
              <div className="flex justify-between text-xs text-slate-300 mb-2 font-medium">
                <span>Weekly Commitment: {streak?.attended_this_week || 0} / {streak?.weekly_target_days || 3} Classes</span>
                <span>{Math.min(100, Math.round(((streak?.attended_this_week || 0) / (streak?.weekly_target_days || 3)) * 100))}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-orange-500 to-amber-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, ((streak?.attended_this_week || 0) / (streak?.weekly_target_days || 3)) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* 2. Protective Lives Card (3 Heart Container) */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-rose-400">Streak Lives</span>
                <div className="text-3xl font-extrabold text-white mt-1 flex items-center gap-2">
                  {[...Array(3)].map((_, i) => (
                    <Heart 
                      key={i} 
                      className={`w-7 h-7 transition-all ${
                        i < (streak?.lives_remaining || 0) 
                          ? 'text-rose-500 fill-rose-500 drop-shadow-[0_0_8px_rgba(244,63,94,0.6)]' 
                          : 'text-slate-700 stroke-slate-600'
                      }`} 
                    />
                  ))}
                </div>
              </div>
              <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20">
                <Heart className="w-6 h-6 text-rose-400" />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">Weekly Cap Status:</span>
              {streak?.lives_earned_this_week >= 1 ? (
                <span className="px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 font-semibold">
                  Weekly Earned Life Limit Reached (1/1)
                </span>
              ) : (
                <span className="text-emerald-400 font-medium">Eligible for +1 Life</span>
              )}
            </div>
          </div>

          {/* 3. Penalty Points & Standing */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-indigo-400">Account Penalty Tier</span>
                <div className="text-3xl font-extrabold text-white mt-1">
                  {member?.penalty_points || 0} <span className="text-base font-normal text-slate-400">Points</span>
                </div>
              </div>
              <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
                <AlertTriangle className="w-6 h-6 text-indigo-400" />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 text-xs text-slate-400">
              Status: <span className="font-semibold text-slate-200">{member?.restriction_status || 'NONE'}</span>
              <p className="mt-1 text-[11px] text-slate-500">Points automatically reset on 1st of every month.</p>
            </div>
          </div>
        </section>

        {/* Unlocked Achievements Showcase & Demo Controls */}
        <section className="glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-400" />
                Unlocked Achievements & Milestones
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Earned from weekly over-achievements, consistency milestones, and class targets.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  await fetch('/api/v1/streak/target', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ member_id: memberId, weekly_target_days: 5 })
                  })
                  fetchData()
                }}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700"
              >
                Set Target to 5
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {[
              { id: 'OVER_ACHIEVER_1_WEEK', name: 'Overachiever (1 Wk)', desc: 'Attended > Target', icon: '⚡' },
              { id: 'OVER_ACHIEVER_2_WEEKS', name: 'Elite Consistency', desc: 'Consecutive Goals', icon: '🌟' },
              { id: 'STREAK_MILESTONE_4_WEEKS', name: '4-Week Champion', desc: 'Protected Streak', icon: '🏆' },
              { id: 'ATTENDED_5_PLUS_CLASSES', name: 'Iron Warrior', desc: '5+ Classes in Week', icon: '🛡️' },
            ].map((ach) => {
              const isUnlocked = streak?.achievements?.includes(ach.id)
              return (
                <div 
                  key={ach.id} 
                  className={`p-3 rounded-xl border flex flex-col justify-between transition ${
                    isUnlocked 
                      ? 'bg-amber-500/10 border-amber-500/30 text-amber-200' 
                      : 'bg-slate-900/60 border-slate-800 text-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xl">{ach.icon}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      isUnlocked ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-600'
                    }`}>
                      {isUnlocked ? 'Unlocked' : 'Locked'}
                    </span>
                  </div>
                  <div className="mt-2">
                    <div className="text-xs font-bold text-white truncate">{ach.name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{ach.desc}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Classes & Schedule Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Calendar className="w-6 h-6 text-orange-400" />
              Available Class Slots
            </h2>
            <button 
              onClick={fetchData} 
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition"
            >
              Refresh Schedule
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {slots.length === 0 ? (
              <div className="col-span-3 text-center py-12 glass-panel rounded-2xl text-slate-400">
                No class slots configured yet.
              </div>
            ) : (
              slots.map((slot) => {
                const rawTime = slot.start_time?.endsWith('Z') ? slot.start_time : `${slot.start_time}Z`
                const startTime = new Date(rawTime)
                const isFull = slot.booked_count >= slot.capacity
                return (
                  <div key={slot.id} className="glass-panel p-5 rounded-2xl flex flex-col justify-between hover:border-slate-700 transition duration-200">
                    <div>
                      <div className="flex justify-between items-start">
                        <h3 className="font-bold text-lg text-white">{slot.title}</h3>
                        <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                          isFull 
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' 
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        }`}>
                          {slot.booked_count} / {slot.capacity} Booked
                        </span>
                      </div>
                      <div className="flex items-center text-xs text-slate-400 mt-3 space-x-2">
                        <Clock className="w-4 h-4 text-slate-500" />
                        <span>{formatIndianDateTime(slot.start_time)}</span>
                      </div>
                    </div>

                    <div className="mt-5">
                      <button
                        onClick={() => handleBookSlot(slot.id)}
                        disabled={isFull}
                        className={`w-full py-2.5 rounded-xl font-semibold text-sm transition ${
                          isFull
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                            : 'bg-orange-500 hover:bg-orange-600 text-white shadow-lg shadow-orange-500/25 active:scale-[0.98]'
                        }`}
                      >
                        {isFull ? 'Slot Fully Booked' : 'Book Class Slot'}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </section>

        {/* Member's Active Bookings */}
        <section className="space-y-4">
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            Your Reservations
          </h2>

          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
            {bookings.length === 0 ? (
              <div className="text-center py-10 text-slate-400 text-sm">
                You have no active bookings.
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {bookings.map((b) => {
                  const bookedSlot = b.slot || slots.find(s => s.id === b.slot_id)
                  const slotTitle = bookedSlot?.title || `Class Slot #${b.slot_id}`
                  const slotTiming = bookedSlot ? formatIndianDateTime(bookedSlot.start_time) : null
                  return (
                    <div key={b.id} className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-base">{slotTitle}</span>
                          <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            b.status === 'CONFIRMED' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' :
                            b.status === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {b.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          {slotTiming && <span className="text-orange-400 font-medium mr-2">📅 {slotTiming}</span>}
                          <span>Reserved: {formatIndianDate(b.created_at)} (Ref #{b.id})</span>
                        </p>
                      </div>

                      {b.status === 'CONFIRMED' && (
                        <div className="flex items-center space-x-3 w-full sm:w-auto">
                          <button
                            onClick={() => handleCompleteBooking(b.id)}
                            className="flex-1 sm:flex-none px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 transition"
                          >
                            Check-in / Complete
                          </button>
                          <button
                            onClick={() => initiateCancel(b)}
                            className="flex-1 sm:flex-none px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 rounded-xl text-xs font-semibold transition"
                          >
                            Cancel Booking
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </section>

        {/* Dispute & Support Section */}
        <section className="glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-400" />
              Dispute Penalty / Customer Support Appeal
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Received a penalty point by mistake or faced an emergency? Submit a dispute ticket to have the penalty reviewed and cleared.
          </p>

          <form onSubmit={handleSupportAppeal} className="space-y-3">
            <input
              type="text"
              placeholder="State reason for dispute (e.g. Medical emergency, transit delay)..."
              value={appealReason}
              onChange={(e) => setAppealReason(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-orange-500"
            />
            <button
              type="submit"
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md transition"
            >
              Submit & Resolve Appeal
            </button>
          </form>

          {appealMessage && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-xl">
              {appealMessage}
            </div>
          )}
        </section>
      </main>

      {/* Late Cancellation Warning Modal (Section 2.5 Requirement) */}
      {cancelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-rose-500/40 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-500 mb-4">
              <AlertTriangle className="w-7 h-7" />
              <h3 className="text-lg font-bold text-white">Late Cancellation Warning</h3>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              Warning: This class starts in <strong className="text-rose-400">less than 2 hours</strong>. Cancelling now will add <strong className="text-rose-400">+1 Penalty Point</strong> to your account according to gym policy.
            </p>
            <div className="mt-6 flex items-center justify-end space-x-3">
              <button
                onClick={() => setCancelModalOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
              >
                Keep Booking
              </button>
              <button
                onClick={() => executeCancel(cancellingBooking.id)}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-rose-600/30 transition"
              >
                Confirm Cancellation (+1 Penalty)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        Apex Fitness SaaS Facility Management • DevOps Final Project Capstone
      </footer>
    </div>
  )
}
