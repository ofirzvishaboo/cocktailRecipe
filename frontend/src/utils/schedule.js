/** Sunday-based week (0=Sun .. 6=Sat). */
export function getSunday(date) {
  const d = new Date(date)
  const day = d.getDay()
  d.setDate(d.getDate() - day)
  d.setHours(0, 0, 0, 0)
  return d
}

export function toLocalDateStr(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function parseTimeMinutes(t) {
  if (!t) return 0
  const parts = String(t).split(':')
  return Number(parts[0]) * 60 + Number(parts[1] || 0)
}

export function formatTime(t) {
  if (!t) return ''
  const parts = String(t).split(':')
  return `${parts[0]}:${parts[1]}`
}

export function templateAllowedOnDay(template, dayOfWeek, fridayLastStartHour = 18) {
  if (dayOfWeek === 6) return false
  if (dayOfWeek !== 5) return true
  const start = parseTimeMinutes(template.start_time)
  const end = parseTimeMinutes(template.end_time)
  const cutoff = fridayLastStartHour * 60
  if (start >= cutoff) return false
  if (end <= start) return false
  if (end > cutoff) return false
  return true
}

export const DAY_KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

/** Tuesday before the Sunday that starts the schedule week. */
export function getAvailabilityDeadline(weekStartSunday) {
  const d = new Date(weekStartSunday)
  d.setDate(d.getDate() - 5)
  d.setHours(0, 0, 0, 0)
  return d
}

export function canStaffSubmit(weekStartSunday, today = new Date()) {
  const deadline = getAvailabilityDeadline(weekStartSunday)
  const t = new Date(today)
  t.setHours(0, 0, 0, 0)
  return t.getTime() <= deadline.getTime()
}

/** Sunday of the week staff should fill in now. */
export function getTargetWeekSunday(today = new Date()) {
  let sun = getSunday(today)
  if (canStaffSubmit(sun, today)) return sun
  sun = new Date(sun)
  sun.setDate(sun.getDate() + 7)
  return sun
}

export function formatShortDate(date) {
  return `${date.getDate()}/${date.getMonth() + 1}`
}

export function formatShortDateFromIso(isoDate) {
  if (!isoDate) return ''
  const [y, m, d] = String(isoDate).split('-').map(Number)
  return formatShortDate(new Date(y, m - 1, d))
}
