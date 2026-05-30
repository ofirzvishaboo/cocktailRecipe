import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../../api'
import { useAuth } from '../../contexts/AuthContext'
import { formatShortDateFromIso } from '../../utils/schedule'
import '../../styles/schedule.css'

const AVAILABILITY_PATHS = ['/schedule/availability', '/my-availability', '/my-schedule']

export default function StaffAvailabilityBanner() {
  const { isAuthenticated, hasStaffProfile, loading: authLoading } = useAuth()
  const { t } = useTranslation()
  const location = useLocation()
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    if (!isAuthenticated || !hasStaffProfile) {
      setMeta(null)
      return
    }
    if (AVAILABILITY_PATHS.includes(location.pathname)) return

    api
      .get('/schedule/weeks/current/meta')
      .then((res) => setMeta(res.data))
      .catch(() => setMeta(null))
  }, [isAuthenticated, hasStaffProfile, location.pathname])

  if (authLoading || !isAuthenticated || !hasStaffProfile) return null
  if (AVAILABILITY_PATHS.includes(location.pathname)) return null
  if (!meta?.can_submit) return null

  return (
    <div className="staff-availability-banner" role="status">
      <div className="staff-availability-banner-text">
        <strong>{t('schedule.availability.bannerTitle')}</strong>
        <span>
          {meta.submitted
            ? t('schedule.availability.bannerSubmitted', {
                date: formatShortDateFromIso(meta.availability_deadline),
              })
            : t('schedule.availability.bannerPending', {
                date: formatShortDateFromIso(meta.availability_deadline),
              })}
        </span>
      </div>
      <Link to="/my-schedule?tab=availability" className="button-primary staff-availability-banner-btn">
        {meta.submitted ? t('schedule.availability.bannerUpdate') : t('schedule.availability.bannerCta')}
      </Link>
    </div>
  )
}
