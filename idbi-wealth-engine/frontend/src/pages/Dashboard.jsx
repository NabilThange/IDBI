import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '@/lib/apiClient'
import { Response } from '../components/ui/response'
import { Gauge } from "../components/ui/charts/gauge"
import { PieChart } from "../components/ui/charts/pie-chart"
import { PieSlice } from "../components/ui/charts/pie-slice"
import { PieCenter } from "../components/ui/charts/pie-center"
import {
  Legend,
  LegendItem,
  LegendItemComponent,
  LegendMarker,
  LegendLabel,
  LegendValue
} from "../components/ui/charts/legend"
import {
  ResponsiveContainer, Pie, Cell, Tooltip as ChartTooltip,
  BarChart, Bar, XAxis, YAxis, LineChart, Line
} from 'recharts'
import {
  User, Coins, Target, Briefcase, ChartBar as BarChart2,
  Shield, Translate as Languages, Question as HelpCircle, CheckCircle, Warning as AlertTriangle,
  ArrowRight, Plus, CaretDown as ChevronDown, ShieldWarning as ShieldAlert,
  UserPlus, CreditCard, TrendUp as TrendingUp, List as Menu, X, Sparkle as Sparkles,
  Pencil as Edit2, ChatCircle as MessageCircle, ArrowUpRight, Wallet,
  House as Home, ForkKnife as Utensils, Car, Television as Tv, Heartbeat as Activity, ShoppingCart, ThumbsUp, ThumbsDown, Check
} from '@phosphor-icons/react'

// Color constants
const COLORS = {
  essential: '#3b82f6',     // Blue
  discretionary: '#f59e0b',  // Orange
  luxury: '#ef4444',         // Red
  investment: '#10b981',     // Green
  unknown: '#6b7280'         // Gray
}

const PIE_COLORS = ['#3b82f6', '#f59e0b', '#ef4444', '#10b981', '#6b7280']

const LOADING_MESSAGES = [
  'Finding the patterns behind your money.',
  'Turning everyday activity into useful signals.',
  'Lining up the next smart move for you.',
  'Putting your goals in sharper focus.',
  'Looking for opportunities worth your attention.',
  'Connecting the details to the bigger picture.',
  'Building a clearer view of your financial life.',
  'Preparing insights made for this moment.'
]

const shuffle = (items) => [...items].sort(() => Math.random() - 0.5)
const DotmCircular3 = () => <div className="dotm-circular dotm-circular-3">{Array.from({ length: 12 }, (_, i) => <i key={i} style={{ '--dot': i }} />)}</div>
const DotmCircular4 = () => <div className="dotm-circular dotm-circular-4">{Array.from({ length: 12 }, (_, i) => <i key={i} style={{ '--dot': i }} />)}</div>
const DotmCircular11 = () => <div className="dotm-circular dotm-circular-11">{Array.from({ length: 12 }, (_, i) => <i key={i} style={{ '--dot': i }} />)}</div>
const DOT_MATRIX_LOADERS = [DotmCircular3, DotmCircular4, DotmCircular11]

function DashboardLoader() {
  const [loaderState, setLoaderState] = useState(() => ({ items: shuffle(DOT_MATRIX_LOADERS), index: 0 }))
  const [messageState, setMessageState] = useState(() => ({ items: shuffle(LOADING_MESSAGES), index: 0 }))
  const Loader = loaderState.items[loaderState.index]

  useEffect(() => {
    const timer = setTimeout(() => setLoaderState(({ items, index }) => index < items.length - 1
      ? { items, index: index + 1 }
      : { items: shuffle(DOT_MATRIX_LOADERS), index: 0 }), 1000 + Math.random() * 2000)
    return () => clearTimeout(timer)
  }, [loaderState.index])

  useEffect(() => {
    const timer = setTimeout(() => setMessageState(({ items, index }) => index < items.length - 1
      ? { items, index: index + 1 }
      : { items: shuffle(LOADING_MESSAGES), index: 0 }), 1000 + Math.random() * 2000)
    return () => clearTimeout(timer)
  }, [messageState.index])

  return <div className="dashboard-loader" aria-live="polite"><Loader /><p>{messageState.items[messageState.index]}</p></div>
}

function assignCohort(profile) {
  if (!profile || !profile.financial_summary) return 'unknown';

  const current_balance = profile.financial_summary.current_balance || 0;
  const total_investments = profile.financial_summary.total_investments || 0;
  const aum = current_balance + total_investments;

  const is_nri = profile.metadata?.nri_status || false;

  let segment = 'mass';
  if (is_nri) {
    segment = 'nri';
  } else if (aum >= 1000000) {
    segment = 'hni';
  }

  const age = profile.age || 30;
  const age_decade = `${Math.floor(age / 10) * 10}s`;

  const income = profile.financial_summary.monthly_income || 0;
  let income_bracket = '200k+';
  if (income < 50000) {
    income_bracket = '<50k';
  } else if (income < 100000) {
    income_bracket = '50-100k';
  } else if (income < 200000) {
    income_bracket = '100-200k';
  }

  return `${segment}_${age_decade}_${income_bracket}`;
}

function formatIndianCurrency(num) {
  if (num === null || num === undefined) return '0';
  if (num < 100000) {
    return num.toLocaleString('en-IN');
  } else if (num < 10000000) {
    const lakhs = num / 100000;
    return lakhs % 1 === 0 ? `${lakhs} Lakhs` : `${lakhs.toFixed(1)} Lakhs`;
  } else {
    const crores = num / 10000000;
    return crores % 1 === 0 ? `${crores} Cr` : `${crores.toFixed(1)} Cr`;
  }
}

// --- Sub-components for Recommendations ---

const RecommendationCard = ({ rec, index, showNotification, triggerRmLead }) => {
  const [detailsOpen, setDetailsOpen] = useState(false)

  const generatePlainLanguageReason = (trail) => {
    if (!trail || trail.length === 0) return rec.rationale
    const hasEmergencyFund = trail.some(s => s.toLowerCase().includes('emergency'))
    const hasGoal = trail.some(s => s.toLowerCase().includes('goal'))
    const hasRisk = trail.some(s => s.toLowerCase().includes('risk'))
    if (hasEmergencyFund) return `Builds your emergency fund while keeping money accessible.`
    if (hasGoal) return `Aligns with your financial goals and matches your current investment capacity.`
    if (hasRisk) return `Balances safety and returns for your risk profile.`
    return rec.rationale
  }

  return (
    <div key={index} className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3 shadow-sm">
      {/* Chip + Title */}
      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap gap-2 items-center">
          <span className="border border-border text-[10px] text-muted-foreground px-2.5 py-0.5 rounded-full font-medium uppercase tracking-wider">
            {rec.product_type}
          </span>
          {rec.requires_rm_handoff ? (
            <span className="bg-secondary text-secondary-foreground text-[10px] px-2.5 py-0.5 rounded-full font-semibold">
              Best with an advisor
            </span>
          ) : (
            <span className="bg-accent text-accent-foreground text-[10px] px-2.5 py-0.5 rounded-full font-semibold">
              Do this instantly
            </span>
          )}
        </div>
        <h3 className="text-[18px] font-bold text-foreground leading-tight">{rec.product_name}</h3>
      </div>

      {/* Amount */}
      <div>
        <p className="text-2xl font-extrabold text-primary leading-none">
          ₹{rec.recommended_amount.toLocaleString()}
          {rec.product_type === 'SIP' || rec.product_name.toLowerCase().includes('sip') || rec.product_name.toLowerCase().includes('monthly') ? <span className="text-[12px] font-normal text-muted-foreground">/mo</span> : ''}
        </p>
      </div>

      {/* One-line "why" — plain text, no box */}
      <p className="text-sm text-muted-foreground leading-relaxed">
        {generatePlainLanguageReason(rec.suitability_trail)}
      </p>

      {/* Details toggle + details panel */}
      <div>
        <button
          onClick={() => setDetailsOpen(prev => !prev)}
          className="flex items-center gap-1.5 text-xs text-primary font-semibold hover:text-primary/80 transition-colors"
        >
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${detailsOpen ? 'rotate-180' : ''}`} />
          {detailsOpen ? 'Hide Details' : 'View Details'}
        </button>

        {detailsOpen && (
          <div className="mt-3 flex flex-col gap-3">
            {/* Key Product Features */}
            {rec.key_features && rec.key_features.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-2">Key Product Features</span>
                <div className="flex flex-col gap-1.5">
                  {rec.key_features.map((f, fIdx) => (
                    <div key={fIdx} className="flex items-start gap-2">
                      <CheckCircle className="w-3.5 h-3.5 text-accent flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-muted-foreground">{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Detailed reasoning */}
            {rec.suitability_trail && rec.suitability_trail.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-2">Why we're suggesting this</span>
                <ul className="list-disc pl-4 space-y-1 text-sm text-muted-foreground">
                  {rec.suitability_trail.map((step, sIdx) => (
                    <li key={sIdx}>{step}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Row */}
      <div className="flex items-center gap-2 pt-1 border-t border-border">
        {/* Feedback */}
        <button
          onClick={() => showNotification("Thanks! We'll use this to improve future suggestions.")}
          className="p-1.5 hover:bg-muted rounded transition-colors"
          title="This recommendation is helpful"
        >
          <ThumbsUp className="w-4 h-4 text-muted-foreground hover:text-foreground" />
        </button>
        <button
          onClick={() => showNotification("Thanks! We'll use this to improve future suggestions.")}
          className="p-1.5 hover:bg-muted rounded transition-colors"
          title="This recommendation is not helpful"
        >
          <ThumbsDown className="w-4 h-4 text-muted-foreground hover:text-foreground" />
        </button>

        {/* Talk to a person */}
        <button
          onClick={() => triggerRmLead(rec)}
          className="ml-auto border border-border hover:bg-muted text-foreground font-medium text-sm px-3.5 py-2 rounded-lg transition-all"
        >
          Talk to a person
        </button>

        {/* Primary action */}
        {rec.requires_rm_handoff ? (
          <button
            onClick={() => triggerRmLead(rec)}
            className="bg-secondary hover:bg-secondary/80 text-secondary-foreground font-semibold text-sm px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all"
          >
            Talk to an Advisor <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            onClick={() => showNotification(`Redirecting to IDBI's application portal for ${rec.product_name}...`)}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-sm px-4 py-2 rounded-lg transition-all"
          >
            Invest now
          </button>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()

  // Navigation & Session
  const [currentLens, setCurrentLens] = useState('customer') // 'customer' | 'rm' | 'bank'
  const [profiles, setProfiles] = useState([])
  const [activeProfileId, setActiveProfileId] = useState(() => {
    try {
      const saved = localStorage.getItem('profile')
      if (saved) {
        const parsed = JSON.parse(saved)
        const prof = (parsed && parsed.status === 'active' && parsed.profile) ? parsed.profile : parsed
        if (prof && prof.profile_id) {
          return prof.profile_id
        }
      }
    } catch (e) {
      console.error('Error reading initial profile from localStorage:', e)
    }
    return 'rahul_001'
  })
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [quizStatus, setQuizStatus] = useState(null)
  const [healthData, setHealthData] = useState(null)

  // Customer Lens State
  const [activeCustomerTab, setActiveCustomerTab] = useState('overview') // 'overview' | 'spending' | 'goals' | 'recommendations'
  const [spendAnalysis, setSpendAnalysis] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [goals, setGoals] = useState([])
  const [insights, setInsights] = useState([])
  const [spendHoveredIndex, setSpendHoveredIndex] = useState(null)


  // What-If Simulator State
  const [selectedGoalSim, setSelectedGoalSim] = useState(null)
  const [simContribution, setSimContribution] = useState(10000)
  const [simResult, setSimResult] = useState(null)

  // Goals Accordion & Per-Goal Simulator State
  const [expandedGoalId, setExpandedGoalId] = useState(null)
  const [goalSimContributions, setGoalSimContributions] = useState({})
  const [goalSimResults, setGoalSimResults] = useState({})
  const [goalSimChips, setGoalSimChips] = useState({})



  // Notifications
  const [notification, setNotification] = useState(null)

  // Mobile Menu State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Load available profiles on mount
  useEffect(() => {
    fetchProfiles()
  }, [])

  // Load profile-specific data when active profile changes
  useEffect(() => {
    if (activeProfileId) {
      loadProfileData(activeProfileId)
    }
  }, [activeProfileId])



  const showNotification = (message, type = 'success') => {
    setNotification({ message, type })
    setTimeout(() => setNotification(null), 4000)
  }

  const fetchProfiles = async () => {
    try {
      const res = await apiClient.get('/api/profiles')
      setProfiles(res.data.profiles || res.data)
    } catch (err) {
      console.error('Error fetching profiles:', err)
    }
  }

  const loadProfileData = async (profileId) => {
    setLoading(true)
    setError(null)
    try {
      // 1. Select session
      const selRes = await apiClient.post('/api/session/select', { profile_id: profileId })
      const session_id = selRes.data.session_id

      // 2. Fetch current profile
      const profRes = await apiClient.get(`/api/session/current/${session_id}`)
      const profData = profRes.data.profile || profRes.data
      setProfile(profData)
      setGoals(profData.goals || [])

      // Keep SessionContext / localStorage in sync
      localStorage.setItem('sessionId', session_id)
      localStorage.setItem('profile', JSON.stringify(profData))

      // Fetch quiz status
      try {
        const statusRes = await apiClient.get(`/api/quiz/status?session_id=${profileId}`)
        setQuizStatus(statusRes.data)
      } catch (quizErr) {
        console.error('Error fetching quiz status:', quizErr)
        setQuizStatus(null)
      }

      // Fetch financial health
      try {
        const healthRes = await apiClient.get(`/api/financial-health?session_id=${profileId}`)
        setHealthData(healthRes.data)
      } catch (healthErr) {
        console.error('Error fetching financial health:', healthErr)
        setHealthData(null)
      }

      // 3. Fetch spending analysis
      const spendRes = await apiClient.get(`/api/spending-analysis?session_id=${profileId}`)
      setSpendAnalysis(spendRes.data)

      // 4. Fetch recommendations
      const recRes = await apiClient.get(`/api/recommendations?session_id=${profileId}`)
      setRecommendations(recRes.data)

      // 5. Fetch insights
      const insRes = await apiClient.get(`/api/wealth-insights?session_id=${profileId}`)
      setInsights(insRes.data.insights || insRes.data)

      // Reset Simulator
      if (profData.goals && profData.goals.length > 0) {
        handleSelectGoalSim(profData.goals[0])
      } else {
        setSelectedGoalSim(null)
        setSimResult(null)
      }

    } catch (err) {
      setError('Failed to load profile data. Make sure backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // What-If Goal Simulator
  const handleSelectGoalSim = (goal) => {
    setSelectedGoalSim(goal)
    setSimContribution(goal.monthly_contribution || 5000)
    runGoalSimulation(goal, goal.monthly_contribution || 5000)
  }

  const runGoalSimulation = (goal, contribution) => {
    if (!goal || !profile) return

    const targetAmount = goal.target_amount
    const currentSavings = goal.current_savings || 0
    const netNeeded = Math.max(0, targetAmount - currentSavings)

    // Assumed return rates based on risk category
    const risk = profile.risk_profile?.risk_category || 'Moderate'
    const annualRate = risk === 'Conservative' ? 0.065 : risk === 'Moderate' ? 0.10 : 0.13
    const r = annualRate / 12

    // Target months from goal
    let targetMonths = 120
    try {
      const targetDate = new Date(goal.target_date)
      const now = new Date()
      targetMonths = (targetDate.getFullYear() - now.getFullYear()) * 12 + (targetDate.getMonth() - now.getMonth())
      if (targetMonths <= 0) targetMonths = 1
    } catch (e) { }

    // Calculation: FV = PMT * ((1+r)^N - 1) / r
    // We solve for required contribution or find N with current contribution
    let projectedFV = 0
    let monthsToReach = 0

    if (r > 0) {
      // Projected FV at target date
      const factor = Math.pow(1 + r, targetMonths) - 1
      projectedFV = currentSavings * Math.pow(1 + r, targetMonths) + (contribution * factor) / r

      // Months to reach target
      // FV = Savings * (1+r)^n + PMT * ((1+r)^n - 1) / r
      // Solve using numeric loop for accuracy
      let tempSavings = currentSavings
      while (tempSavings < targetAmount && monthsToReach < 600) {
        tempSavings = tempSavings * (1 + r) + contribution
        monthsToReach++
      }
    } else {
      projectedFV = currentSavings + contribution * targetMonths
      monthsToReach = Math.ceil(netNeeded / contribution)
    }

    const difference = Math.floor(projectedFV - targetAmount)
    const onTrack = projectedFV >= targetAmount

    setSimResult({
      projectedFV,
      monthsToReach,
      difference,
      onTrack,
      targetMonths
    })
  }

  const handleSimContributionChange = (val) => {
    setSimContribution(val)
    runGoalSimulation(selectedGoalSim, val)
  }

  // RM Lead Handling


  const triggerRmLead = async (rec) => {
    try {
      await apiClient.post(`/api/recommendations/lead?session_id=${activeProfileId}`, {
        product_name: rec.product_name,
        product_type: rec.product_type,
        recommended_amount: rec.recommended_amount,
        suitability_trail: rec.suitability_trail
      })
      showNotification('Your request was sent to the Manager. An advisor will contact you in 24-48 hours.', 'success')
      // Force refresh current tab
      loadProfileData(activeProfileId)
    } catch (err) {
      showNotification('Error generating lead', 'error')
      console.error(err)
    }
  }





  // Prepare spending pie data
  const currentSips = profile?.current_investments?.filter(i => i.type === 'SIP').reduce((acc, i) => acc + (i.monthly_amount || 0), 0) || 0;
  const surplus = profile ? (profile.financial_summary?.monthly_savings || 0) - currentSips : 0;

  const getPieData = () => {
    if (!spendAnalysis || !spendAnalysis.spending_by_category) return []
    return spendAnalysis.spending_by_category.map(item => ({
      name: item.category.toUpperCase(),
      value: Math.floor(item.amount)
    }))
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Banner & Persona Picker */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4 z-40 sticky top-0">
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          {/* Mobile Burger Menu Button (visible only on mobile) */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="lg:hidden p-2 -ml-2 rounded-xl text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 active:scale-95 transition-all duration-200"
            aria-label="Open Menu"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Desktop Branding - Hidden on mobile */}
          <div className="hidden lg:flex items-center gap-3">
            <div className="bg-primary p-2 rounded-xl text-white">
              <Shield className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-primary">
                IDBI AI Wealth Engine
              </h1>
              <p className="text-xs text-slate-400">v3.0 Three-Lens Intelligence Platform</p>
            </div>
          </div>

          {/* Mobile Navigation Tabs inside the Header (visible only on mobile in customer lens) */}
          {currentLens === 'customer' && (
            <div className="lg:hidden flex-1 flex justify-around items-center h-12 ml-2">
              <button
                onClick={() => setActiveCustomerTab('overview')}
                className="flex flex-col items-center justify-center focus:outline-none cursor-pointer relative h-full flex-1 pt-1"
              >
                <div className="grid grid-cols-2 gap-0.5 w-[12px] h-[12px] mb-0.5">
                  <div className={`w-[5px] h-[5px] rounded-[1px] ${activeCustomerTab === 'overview' ? 'bg-primary' : 'bg-muted-foreground'}`}></div>
                  <div className={`w-[5px] h-[5px] rounded-[1px] ${activeCustomerTab === 'overview' ? 'bg-accent' : 'bg-muted-foreground'}`}></div>
                  <div className={`w-[5px] h-[5px] rounded-[1px] ${activeCustomerTab === 'overview' ? 'bg-primary' : 'bg-muted-foreground'}`}></div>
                  <div className={`w-[5px] h-[5px] rounded-[1px] ${activeCustomerTab === 'overview' ? 'bg-accent' : 'bg-muted-foreground'}`}></div>
                </div>
                <span className={`text-[9px] font-bold transition-colors ${activeCustomerTab === 'overview' ? 'text-primary font-extrabold' : 'text-slate-400 hover:text-slate-200'}`}>
                  Overview
                </span>
                {activeCustomerTab === 'overview' && (
                  <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-t-full"></div>
                )}
              </button>

              <button
                onClick={() => setActiveCustomerTab('spending')}
                className="flex flex-col items-center justify-center focus:outline-none cursor-pointer relative h-full flex-1 pt-1"
              >
                <CreditCard className={`w-3.5 h-3.5 mb-0.5 transition-colors ${activeCustomerTab === 'spending' ? 'text-primary' : 'text-slate-400 hover:text-slate-200'}`} />
                <span className={`text-[9px] font-bold transition-colors ${activeCustomerTab === 'spending' ? 'text-primary font-extrabold' : 'text-slate-400 hover:text-slate-200'}`}>
                  Spending
                </span>
                {activeCustomerTab === 'spending' && (
                  <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-t-full"></div>
                )}
              </button>

              <button
                onClick={() => setActiveCustomerTab('recommendations')}
                className="flex flex-col items-center justify-center focus:outline-none cursor-pointer relative h-full flex-1 pt-1"
              >
                <Sparkles className={`w-3.5 h-3.5 mb-0.5 transition-colors ${activeCustomerTab === 'recommendations' ? 'text-primary' : 'text-slate-400 hover:text-slate-200'}`} />
                <span className={`text-[9px] font-bold transition-colors ${activeCustomerTab === 'recommendations' ? 'text-primary font-extrabold' : 'text-slate-400 hover:text-slate-200'}`}>
                  Advisory
                </span>
                {activeCustomerTab === 'recommendations' && (
                  <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-t-full"></div>
                )}
              </button>

              <button
                onClick={() => setActiveCustomerTab('goals')}
                className="flex flex-col items-center justify-center focus:outline-none cursor-pointer relative h-full flex-1 pt-1"
              >
                <Target className={`w-3.5 h-3.5 mb-0.5 transition-colors ${activeCustomerTab === 'goals' ? 'text-primary' : 'text-slate-400 hover:text-slate-200'}`} />
                <span className={`text-[9px] font-bold transition-colors ${activeCustomerTab === 'goals' ? 'text-primary font-extrabold' : 'text-slate-400 hover:text-slate-200'}`}>
                  Goals
                </span>
                {activeCustomerTab === 'goals' && (
                  <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-t-full"></div>
                )}
              </button>
            </div>
          )}

          {/* Mobile Active Lens Label (visible on mobile in non-customer lenses) */}
          {currentLens !== 'customer' && (
            <span className="lg:hidden text-xs font-bold text-primary ml-2 uppercase tracking-wider">
              {currentLens === 'rm' ? 'RM Command Center' : 'Bank Intelligence'}
            </span>
          )}
        </div>

        {/* Global Controls - Hidden on mobile, visible on desktop */}
        <div className="hidden lg:flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
            <User className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-slate-300">Active Profile:</span>
            <select
              value={activeProfileId}
              onChange={(e) => setActiveProfileId(e.target.value)}
              className="bg-transparent text-sm font-semibold text-foreground focus:outline-none cursor-pointer"
            >
              {profiles.map(p => (
                <option key={p.profile_id} value={p.profile_id} className="bg-card text-foreground">
                  {p.name} ({p.occupation})
                </option>
              ))}
            </select>
          </div>


        </div>
      </header>

      {/* Floating Notifications */}
      {notification && (
        <div className={`fixed top-20 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border transition-all duration-300 animate-slide-in ${notification.type === 'error'
          ? 'bg-red-950/90 border-red-800 text-red-200'
          : 'bg-emerald-950/90 border-emerald-800 text-emerald-200'
          }`}>
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{notification.message}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto flex flex-col gap-6">
        {loading && (
          <div className="flex-1 flex flex-col justify-center items-center py-20">
            <DashboardLoader />
          </div>
        )}

        {!loading && error && (
          <div className="bg-red-950/40 border border-red-900 rounded-2xl p-6 text-center max-w-md mx-auto my-12">
            <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="font-bold text-lg mb-2">Backend Connection Required</h3>
            <p className="text-slate-400 text-sm mb-6">{error}</p>
            <button
              onClick={() => loadProfileData(activeProfileId)}
              className="bg-red-800 hover:bg-red-700 text-white font-semibold text-sm px-4 py-2 rounded-xl"
            >
              Retry Connection
            </button>
          </div>
        )}

        {!loading && !error && profile && (
          <>
            {/* ==================== LENS A: CUSTOMER APP VIEW ==================== */}
            {currentLens === 'customer' && (
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Customer Menu - Hidden on mobile, visible on desktop */}
                <div className="hidden lg:flex lg:col-span-1 bg-card border border-border rounded-2xl p-4 flex-col gap-2">
                  <div className="bg-primary text-primary-foreground font-extrabold text-xs px-3 py-2 rounded-xl text-center tracking-wider uppercase mb-2 shadow-lg">
                    IDBI BANK APP PAGE
                  </div>
                  <div className="p-3 border-b border-border mb-2">
                    <h3 className="font-bold text-foreground">{profile.name}</h3>
                    <p className="text-xs text-muted-foreground">{profile.occupation} | Age {profile.age}</p>
                    <div className="flex gap-2 mt-3">
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border bg-muted text-muted-foreground border-border">
                        {profile.risk_profile?.risk_category || 'Moderate'}
                      </span>
                      <span className="bg-primary/10 border border-primary/20 text-primary text-[10px] px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 uppercase tracking-wider">
                        <Languages className="w-2.5 h-2.5" /> {profile.language_preference || 'English'}
                      </span>
                    </div>
                  </div>

                  {/* Desktop Vertical Menu Tabs (hidden on mobile) */}
                  <div className="hidden lg:flex flex-col gap-2">
                    <button
                      onClick={() => setActiveCustomerTab('overview')}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-all cursor-pointer ${activeCustomerTab === 'overview'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                        }`}
                    >
                      <Briefcase className="w-4 h-4 text-primary" /> Account Overview
                    </button>

                    <button
                      onClick={() => setActiveCustomerTab('spending')}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-all cursor-pointer ${activeCustomerTab === 'spending'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                        }`}
                    >
                      <Coins className="w-4 h-4 text-muted-foreground" /> Spending Analyzer
                    </button>

                    <button
                      onClick={() => setActiveCustomerTab('goals')}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-all cursor-pointer ${activeCustomerTab === 'goals'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        }`}
                    >
                      <Target className="w-4 h-4 text-muted-foreground" /> Goals & What-If
                    </button>

                    <button
                      onClick={() => setActiveCustomerTab('recommendations')}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-all cursor-pointer ${activeCustomerTab === 'recommendations'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        }`}
                    >
                      <Shield className="w-4 h-4 text-muted-foreground" /> AI Wealth Advisory
                    </button>
                  </div>

                  <button
                    onClick={() => navigate('/quiz')}
                    className="w-full text-left px-4 py-3 rounded-xl text-sm font-semibold flex items-center gap-3 transition-all text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <Target className="w-4 h-4 text-muted-foreground" />
                    {quizStatus?.quiz_completed ? 'Retake Goal Quiz' : 'Take Goal Quiz'}
                  </button>


                </div>

                {/* Customer Content Panels - Full width on mobile, 3/4 width on desktop */}
                <div className="col-span-1 lg:col-span-3 flex flex-col gap-6">


                  {/* TAB 1: OVERVIEW */}
                  {activeCustomerTab === 'overview' && (() => {
                    const scoreVal = healthData ? healthData.score : 82;
                    const healthStatusText = scoreVal >= 80 ? 'Good, and improving' : scoreVal >= 60 ? 'Fair, needs minor adjustments' : 'Attention required';
                    const expensesVal = profile?.financial_summary?.monthly_expenses || 1;
                    const emergencyFundVal = profile?.financial_summary?.emergency_fund || 0;
                    const coverageMonthsVal = Math.round((emergencyFundVal / expensesVal) * 10) / 10;
                    const shortfallMonthsVal = Math.max(0, 6 - coverageMonthsVal);
                    const shortfallAmountVal = Math.round(shortfallMonthsVal * expensesVal);
                    const filledBarsCount = Math.round(scoreVal / 5);

                    // Compute Wealth Score Ring Chart Data
                    const currentBalance = profile.financial_summary?.current_balance || 0;
                    const totalInvestments = profile.financial_summary?.total_investments || 0;
                    const totalExternalDebt = profile.credit_bureau_data?.total_external_debt || 0;
                    const netWorth = currentBalance + totalInvestments - totalExternalDebt;

                    const age = profile.age || 30;
                    const monthlyIncome = profile.financial_summary?.monthly_income || 0;
                    const annualIncome = monthlyIncome * 12;
                    const expectedNw = (age * annualIncome) / 10;
                    const lwr = expectedNw > 0 ? (netWorth / expectedNw) : 0;
                    const roundedLwr = Math.round(lwr * 100) / 100;

                    const monthlyExpenses = profile.financial_summary?.monthly_expenses || 1;
                    const runwayMonths = Math.round(((currentBalance + totalInvestments) / monthlyExpenses) * 10) / 10;

                    const ringChartData = [
                      { label: "Wealth Health", value: scoreVal, maxValue: 100, color: "#10b981", rawValue: scoreVal, suffix: "/100" }, // Outer ring
                      { label: "Wealth Position", value: Math.min(3, roundedLwr), maxValue: 3, color: "#f59e0b", rawValue: roundedLwr, suffix: "x" }, // Middle ring
                      { label: "Financial Runway", value: Math.min(24, runwayMonths), maxValue: 24, color: "#0ea5e9", rawValue: runwayMonths, suffix: " Mo" } // Inner ring
                    ];

                    return (
                      <div className="flex flex-col gap-6">
                        {/* Quiz Pending Banner */}
                        {quizStatus && !quizStatus.quiz_completed && (
                          <div className="bg-destructive/10 border border-destructive/30 rounded-3xl p-6 flex flex-col md:flex-row justify-between items-center gap-6 shadow-xl">
                            <div className="flex-1">
                              <span className="text-[10px] uppercase font-bold tracking-wider text-destructive">Action Required</span>
                              <h3 className="text-xl font-bold mt-1 mb-2">Goal Discovery Quiz Pending</h3>
                              <p className="text-sm text-muted-foreground max-w-xl">
                                Complete the short 3-step quiz to capture your life stage, financial goals, timeline constraints, and risk tolerance. This will power personalized AI wealth recommendations and tracking.
                              </p>
                            </div>
                            <button
                              onClick={() => navigate('/quiz')}
                              className="bg-primary hover:bg-primary/90 text-primary-foreground font-extrabold text-xs px-6 py-3.5 rounded-xl transition-all shadow-md whitespace-nowrap"
                            >
                              Take Quiz Now
                            </button>
                          </div>
                        )}

                        {/* 1. Greeting header */}
                        <div className="flex justify-between items-center bg-slate-900/10 p-1">
                          <div className="text-left">
                            <span className="text-xs text-slate-700 font-extrabold uppercase tracking-wider">
                              {(() => {
                                const hour = new Date().getHours();
                                if (hour < 12) return 'Good morning';
                                if (hour < 17) return 'Good afternoon';
                                return 'Good evening';
                              })()}
                            </span>
                            <h2 className="text-2xl font-black text-black mt-0.5 tracking-tight flex items-center gap-1.5 select-none">
                              {profile.name}
                            </h2>
                          </div>
                        </div>

                        {/* 2. Redesigned Financial Health Card - Single hero with demoted supporting stats */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 relative overflow-hidden group transition-all duration-300 hover:border-slate-700/80">
                          {/* Shimmer background glow */}
                          <div className="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-slate-800/20 blur-3xl pointer-events-none group-hover:scale-110 transition-transform duration-500"></div>

                          {/* Account number moved to top corner */}
                          <div className="absolute top-4 right-4">
                            <span className="font-mono text-[10px] text-slate-500 tracking-wider font-medium select-none">
                              **** {profile.account_number ? profile.account_number.slice(-4) : '5699'}
                            </span>
                          </div>

                          {/* Gauge Chart displaying Wealth Health - THE HERO */}
                          <div className="w-64 h-48 mx-auto my-3 flex items-center justify-center relative">
                            <Gauge
                              value={scoreVal}
                              centerValue={scoreVal}
                              defaultLabel="Wealth Health"
                              suffix="/100"
                              totalNotches={30}
                              spacing={18}
                              notchCornerRadius={2}
                              useGradient={true}
                              activeGradient={["#10b981", "#34d399"]}
                              inactiveFill="rgba(255, 255, 255, 0.08)"
                              notchLengthPercent={75}
                            />
                          </div>

                          {/* Status chip directly under gauge as subtitle */}
                          <div className="flex justify-center mb-6">
                            <div className="flex items-center gap-1.5 bg-muted border border-border px-3 py-1.5 rounded-xl shadow-inner">
                              <span className={`w-2 h-2 rounded-full animate-pulse ${scoreVal >= 80 ? 'bg-accent' : scoreVal >= 60 ? 'bg-primary' : 'bg-destructive'}`} />
                              <span className={`text-xs font-semibold ${scoreVal >= 80 ? 'text-accent' : scoreVal >= 60 ? 'text-primary' : 'text-destructive'}`}>
                                {healthStatusText}
                              </span>
                            </div>
                          </div>

                          {/* Supporting metrics - demoted to plain text captions, no borders */}
                          <div className="grid grid-cols-2 gap-6 px-4">
                            <div className="flex flex-col items-start">
                              <span className="text-xs text-muted-foreground font-medium">Wealth position</span>
                              <span className="text-2xl font-bold text-foreground mt-1">{roundedLwr}x</span>
                              <span className={`text-xs font-medium mt-1 ${roundedLwr >= 1 ? 'text-accent' : roundedLwr >= 0.5 ? 'text-primary' : 'text-destructive'}`}>
                                {roundedLwr >= 1 
                                  ? 'Above typical for your profile' 
                                  : roundedLwr >= 0.5 
                                    ? 'Slightly below typical' 
                                    : 'Below typical for your profile'}
                              </span>
                            </div>
                            <div className="flex flex-col items-start">
                              <span className="text-xs text-muted-foreground font-medium">Financial runway</span>
                              <span className="text-2xl font-bold text-foreground mt-1">{runwayMonths} Mo</span>
                              <span className={`text-xs font-medium mt-1 ${runwayMonths >= 12 ? 'text-accent' : runwayMonths >= 6 ? 'text-primary' : 'text-destructive'}`}>
                                {runwayMonths >= 12 
                                  ? 'Strong safety buffer' 
                                  : runwayMonths >= 6 
                                    ? 'Adequate safety buffer' 
                                    : 'Below recommended 6 months'}
                              </span>
                            </div>
                          </div>
                        </div>
                        {/* Today's Financial Overview */}
                        <div>
                          <div className="flex justify-between items-center mb-5">
                            <h3 className="font-extrabold text-foreground text-sm tracking-tight">Financial Overview</h3>
                            <span
                              onClick={() => setActiveCustomerTab('spending')}
                              className="text-xs font-bold text-primary hover:text-primary/80 cursor-pointer flex items-center gap-0.5"
                            >
                              More details <ArrowRight className="w-3.5 h-3.5" />
                            </span>
                          </div>
                          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            {/* Card 1: Total Balance */}
                            <div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between h-28 relative group hover:border-primary transition-all shadow-sm">
                              <div className="flex justify-between items-start">
                                <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 text-primary flex items-center justify-center">
                                  <Wallet className="w-4 h-4" />
                                </div>
                                <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                              </div>
                              <div className="mt-1">
                                <span className="text-[10px] text-muted-foreground font-extrabold uppercase tracking-wider block">Total Balance</span>
                                <h4 className="text-xl font-black text-foreground mt-0.5">
                                  ₹{formatIndianCurrency(profile.financial_summary?.current_balance)}
                                </h4>
                              </div>
                            </div>

                            {/* Card 2: Spent this Month */}
                            <div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between h-28 relative group hover:border-destructive transition-all shadow-sm">
                              <div className="flex justify-between items-start">
                                <div className="w-9 h-9 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-center justify-center">
                                  <CreditCard className="w-4 h-4" />
                                </div>
                                <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                              </div>
                              <div className="mt-1">
                                <span className="text-[10px] text-muted-foreground font-extrabold uppercase tracking-wider block">Spent This Month</span>
                                <h4 className="text-xl font-black text-foreground mt-0.5">
                                  ₹{formatIndianCurrency(profile.financial_summary?.monthly_expenses)}
                                </h4>
                              </div>
                            </div>

                            {/* Card 3: What you Owe */}
                            <div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between h-28 relative group hover:border-primary transition-all shadow-sm">
                              <div className="flex justify-between items-start">
                                <div className="w-9 h-9 rounded-xl bg-secondary border border-secondary-foreground/20 text-secondary-foreground flex items-center justify-center">
                                  <AlertTriangle className="w-4 h-4" />
                                </div>
                                <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                              </div>
                              <div className="mt-1">
                                <span className="text-[10px] text-muted-foreground font-extrabold uppercase tracking-wider block">What You Owe</span>
                                <h4 className="text-xl font-black text-foreground mt-0.5">
                                  ₹{formatIndianCurrency(profile.credit_bureau_data?.total_external_debt)}
                                </h4>
                              </div>
                            </div>

                            {/* Card 4: Left over monthly */}
                            <div className="bg-card border border-border rounded-2xl p-4 flex flex-col justify-between h-28 relative group hover:border-accent transition-all shadow-sm">
                              <div className="flex justify-between items-start">
                                <div className="w-9 h-9 rounded-xl bg-accent/10 border border-accent/20 text-accent flex items-center justify-center">
                                  <TrendingUp className="w-4 h-4" />
                                </div>
                                <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                              </div>
                              <div className="mt-1">
                                <span className="text-[10px] text-muted-foreground font-extrabold uppercase tracking-wider block">Left Over Monthly</span>
                                <h4 className="text-xl font-black text-black mt-0.5">
                                  ₹{formatIndianCurrency(surplus)}
                                </h4>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* AI Insights - Carousel with peek, indicators, and urgency colors */}
                        <div>
                          <div className="flex justify-between items-center mb-5">
                            <div className="flex items-center gap-2">
                              <h3 className="font-extrabold text-foreground text-sm tracking-tight">AI Insights</h3>
                              <span className="text-[9px] bg-accent/10 border border-accent/30 text-accent font-extrabold px-2 py-0.5 rounded-full select-none uppercase tracking-wider animate-pulse">
                                Active
                              </span>
                            </div>
                            <span className="text-xs font-bold text-slate-400 hover:text-slate-350 cursor-pointer select-none">
                              View All
                            </span>
                          </div>

                          <div className="relative">
                            {/* Carousel container with peek effect */}
                            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none snap-x snap-mandatory">
                              {insights && insights.length > 0 ? (
                                insights.map((ins, idx) => {
                                  // Determine urgency level
                                  const title = (ins.title || ins.type || '').toLowerCase();
                                  const message = (ins.message || ins.explanation || '').toLowerCase();
                                  const isUrgent = title.includes('emergency') || title.includes('below') || title.includes('shortfall') || message.includes('below threshold');
                                  const isOpportunity = title.includes('surplus') || title.includes('leverage') || title.includes('opportunity');
                                  
                                  return (
                                    <div
                                      key={idx}
                                      className="bg-card border border-border rounded-2xl p-5 w-[280px] md:w-[320px] max-w-[320px] snap-start flex flex-col justify-between shadow-sm hover:border-primary/40 transition-all flex-shrink-0"
                                    >
                                      <div>
                                        <div className="flex items-center gap-2.5 mb-3">
                                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                            isUrgent 
                                              ? 'bg-destructive/10 border border-destructive/20 text-destructive' 
                                              : isOpportunity 
                                                ? 'bg-primary/10 border border-primary/20 text-primary'
                                                : 'bg-secondary border border-border text-secondary-foreground'
                                          }`}>
                                            <Sparkles className="w-4 h-4" />
                                          </div>
                                          <h4 className="text-xs font-extrabold text-foreground capitalize tracking-tight line-clamp-1">
                                            {ins.title || ins.type}
                                          </h4>
                                        </div>
                                        {/* Single line truncated message */}
                                        <p className="text-xs text-muted-foreground font-medium line-clamp-1">
                                          {ins.message || ins.explanation}
                                        </p>
                                      </div>
                                      <button
                                        onClick={() => {
                                          setChatOpen(true);
                                          setChatMessage(`Can you tell me more about: "${ins.title || ins.type}"?`);
                                        }}
                                        className={`w-full mt-4 py-2 font-bold text-xs rounded-xl shadow-md transition-all active:scale-[0.98] cursor-pointer text-center ${
                                          isUrgent
                                            ? 'bg-destructive hover:bg-destructive/90 text-destructive-foreground'
                                            : 'bg-primary hover:bg-primary/90 text-primary-foreground'
                                        }`}
                                      >
                                        {isUrgent ? 'Review Now →' : 'Review →'}
                                      </button>
                                    </div>
                                  );
                                })
                              ) : (
                                <div className="text-xs text-muted-foreground p-4 bg-card border border-border rounded-2xl w-full text-center shadow-sm">
                                  No transaction anomalies detected in this billing cycle.
                                </div>
                              )}
                            </div>
                            
                            {/* Dot indicators - only show if multiple insights */}
                            {insights && insights.length > 1 && (
                              <div className="flex justify-center gap-1.5 mt-3">
                                {insights.map((_, idx) => (
                                  <div
                                    key={idx}
                                    className={`w-1.5 h-1.5 rounded-full transition-all ${
                                      idx === 0 ? 'bg-slate-400 w-4' : 'bg-slate-600'
                                    }`}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })()}

                  {/* TAB 2: SPENDING */}
                  {activeCustomerTab === 'spending' && spendAnalysis && (() => {
                    const totalSpend = spendAnalysis.spending_by_category
                      ? spendAnalysis.spending_by_category.reduce((sum, item) => sum + item.amount, 0)
                      : 0;

                    const getCategoryIcon = (cat) => {
                      const normal = cat.toLowerCase();
                      if (normal.includes('housing') || normal.includes('rent') || normal.includes('home')) return <Home className="w-5 h-5 text-slate-400" />;
                      if (normal.includes('food') || normal.includes('groceries') || normal.includes('dining')) return <Utensils className="w-5 h-5 text-slate-400" />;
                      if (normal.includes('transport') || normal.includes('fuel') || normal.includes('auto') || normal.includes('cab')) return <Car className="w-5 h-5 text-slate-400" />;
                      if (normal.includes('subscription') || normal.includes('ott') || normal.includes('utility') || normal.includes('discretionary')) return <Tv className="w-5 h-5 text-slate-400" />;
                      if (normal.includes('health') || normal.includes('medical')) return <Activity className="w-5 h-5 text-slate-400" />;
                      if (normal.includes('shopping')) return <ShoppingCart className="w-5 h-5 text-slate-400" />;
                      return <CreditCard className="w-5 h-5 text-slate-400" />;
                    };

                    const getCategoryGradient = () => 'var(--primary)';

                    const getCategoryColor = (idx) => {
                      const colors = [
                        '#3b82f6', // Blue
                        '#10b981', // Emerald
                        '#f59e0b', // Amber/Gold
                        '#ec4899', // Pink
                        '#a855f7', // Purple
                        '#f97316', // Orange
                        '#0ea5e9', // Sky Blue
                        '#e11d48', // Red/Rose
                        '#14b8a6', // Teal
                        '#8b5cf6', // Violet
                      ];
                      return colors[idx % colors.length];
                    };

                    // Limit to 5 categories: top 4 + Others
                    const allCategories = (spendAnalysis?.spending_by_category || []);
                    const sortedCategories = [...allCategories].sort((a, b) => b.amount - a.amount);
                    
                    // Top 4 categories
                    const top4 = sortedCategories.slice(0, 4);
                    const remaining = sortedCategories.slice(4);
                    
                    // Create display categories (max 5)
                    const displayCategories = [...top4];
                    if (remaining.length > 0) {
                      const othersTotal = remaining.reduce((sum, item) => sum + item.amount, 0);
                      const othersPercent = (othersTotal / totalSpend) * 100;
                      displayCategories.push({
                        category: 'Others',
                        amount: othersTotal,
                        percent: othersPercent
                      });
                    }

                    const spendPieData = displayCategories.map((item, idx) => ({
                      label: item.category.charAt(0).toUpperCase() + item.category.slice(1),
                      value: Math.floor(item.amount),
                      color: getCategoryColor(idx),
                      maxValue: totalSpend,
                    }));

                    return (
                      <div className="flex flex-col gap-6">

                        {/* 1. Header Option Selector: Income, Expenses, Transfer */}
                        <div className="flex justify-center bg-muted p-1 rounded-xl max-w-[280px] w-full mx-auto border border-border shadow-inner">
                          <button disabled className="px-3.5 py-1.5 text-xs text-muted-foreground font-bold rounded-lg flex-1 text-center cursor-not-allowed">
                            Income
                          </button>
                          <button className="px-3.5 py-1.5 text-xs bg-card text-foreground font-extrabold rounded-lg flex-1 text-center shadow-md">
                            Total
                          </button>
                          <button disabled className="px-3.5 py-1.5 text-xs text-muted-foreground font-bold rounded-lg flex-1 text-center cursor-not-allowed">
                            Expenses
                          </button>
                        </div>

                        {/* 2. Date Picker Selector */}
                        <div className="flex justify-center items-center gap-6 text-sm font-extrabold text-slate-350">
                          <button className="p-1 text-slate-400 hover:text-slate-200 cursor-pointer">
                            &lt;
                          </button>
                          <span className="flex items-center gap-2 select-none">
                            July 2026
                          </span>
                          <button className="p-1 text-slate-400 hover:text-slate-200 cursor-pointer">
                            &gt;
                          </button>
                        </div>

                        {/* 3. Donut Chart Panel - Legend removed, chart only */}
                        <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
                          <div className="flex items-center justify-center">
                            {/* Donut Chart Container */}
                            <div className="relative flex items-center justify-center h-52">
                              <PieChart
                                data={spendPieData}
                                hoveredIndex={spendHoveredIndex}
                                innerRadius={60}
                                onHoverChange={setSpendHoveredIndex}
                                size={180}
                              >
                                {spendPieData.map((_, i) => (
                                  <PieSlice key={i} index={i} hoverEffect="translate" showGlow={true} />
                                ))}
                                <PieCenter defaultLabel="Total Spent" prefix="₹" />
                              </PieChart>
                            </div>
                          </div>
                        </div>

                        {/* 4. Interactive Transaction Notification Box - badge removed, count in text */}
                        <div className="bg-secondary/30 border border-border rounded-2xl p-4 flex items-center justify-between cursor-pointer hover:border-primary/40 active:scale-[0.99] transition-all duration-200">
                          <div className="flex items-center gap-3.5">
                            <div className="w-10 h-10 bg-primary/10 border border-primary/25 rounded-xl flex items-center justify-center text-primary">
                              <CreditCard className="w-5 h-5" />
                            </div>
                            <div className="text-left">
                              <p className="text-xs font-bold text-foreground">13 transactions categorized</p>
                              <p className="text-[10px] text-muted-foreground mt-0.5 font-semibold">Please check if we got it right</p>
                            </div>
                          </div>
                          <ArrowRight className="w-4 h-4 text-muted-foreground" />
                        </div>

                        {/* 5. Budget Spending List - limited to 5 categories (matches chart) */}
                        <div className="bg-card border border-border rounded-2xl p-5 shadow-xl flex flex-col gap-3">
                          <div className="flex justify-between items-center mb-1">
                            <h3 className="font-extrabold text-foreground text-sm">Budget Spending</h3>
                            <button className="p-1 bg-muted border border-border text-muted-foreground hover:text-foreground rounded-lg cursor-pointer">
                              <TrendingUp className="w-3.5 h-3.5 rotate-90" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 gap-3">
                            {displayCategories.map((item, idx) => (
                              <div key={item.category} className="flex items-center gap-3 bg-muted/40 border border-border rounded-2xl p-4 transition-all hover:border-primary/40">
                                {/* Emoji/Icon box */}
                                <div className="w-10 h-10 rounded-xl bg-muted border border-border flex items-center justify-center text-lg select-none">
                                  {getCategoryIcon(item.category)}
                                </div>

                                {/* Progress bar & metadata */}
                                <div className="flex-1 flex flex-col gap-1">
                                  <div className="flex justify-between items-center">
                                    <span className="text-xs font-bold capitalize text-foreground">{item.category}</span>
                                  </div>

                                  {/* Progress bar container */}
                                  <div className="w-full bg-muted rounded-full h-2 overflow-hidden border border-border">
                                    <div
                                      className="h-full rounded-full transition-all duration-500 bg-primary"
                                      style={{ width: `${item.percent}%` }}
                                    />
                                  </div>

                                  <div className="flex justify-between items-center text-[10px] font-bold mt-0.5">
                                    <span className="text-foreground">₹{formatIndianCurrency(Math.floor(item.amount))}</span>
                                    <span className="text-muted-foreground">{Math.round(item.percent)}%</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* 6. Recurring Subscriptions (EMI / Subscriptions) */}
                        {spendAnalysis.recurring_transactions && spendAnalysis.recurring_transactions.length > 0 && (
                          <div className="bg-card border border-border rounded-2xl p-5 shadow-xl flex flex-col gap-3">
                            <h3 className="font-extrabold text-foreground text-sm">Recurring EMIs & Subscriptions</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {spendAnalysis.recurring_transactions.map((rec, idx) => (
                                <div key={idx} className="bg-muted border border-border p-4 rounded-xl flex justify-between items-center">
                                  <div>
                                    <h5 className="text-xs font-bold text-foreground capitalize">{rec.merchant}</h5>
                                    <span className="text-[10px] text-muted-foreground block mt-0.5">Frequency: {rec.frequency}</span>
                                  </div>
                                  <span className="text-xs font-extrabold text-primary">
                                    ₹{formatIndianCurrency(rec.amount)}/mo
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Folded empty subscription state */}
                        {(!spendAnalysis.recurring_transactions || spendAnalysis.recurring_transactions.length === 0) && (
                          <div className="text-xs text-muted-foreground p-4 bg-muted/40 border border-border rounded-2xl flex items-center gap-2.5">
                            <Check className="w-4 h-4 text-accent flex-shrink-0" />
                            <span>No recurring subscriptions found this month — nothing quietly draining your account.</span>
                          </div>
                        )}

                      </div>
                    )
                  })()}

                  {/* TAB 3: GOALS — redesigned */}
                  {activeCustomerTab === 'goals' && (() => {
                    const risk = profile?.risk_profile?.risk_category || 'Moderate'
                    const annualRate = risk === 'Conservative' ? 0.065 : risk === 'Moderate' ? 0.10 : 0.13

                    const computeMonths = (g, contribution) => {
                      const r = annualRate / 12
                      const currentSavings = g.current_savings || 0
                      const targetAmount = g.target_amount
                      if (contribution <= 0) return 600
                      let tempSavings = currentSavings
                      let months = 0
                      while (tempSavings < targetAmount && months < 600) {
                        tempSavings = tempSavings * (1 + r) + contribution
                        months++
                      }
                      return months
                    }

                    const targetMonthsFor = (g) => {
                      try {
                        const d = new Date(g.target_date)
                        const now = new Date()
                        const m = (d.getFullYear() - now.getFullYear()) * 12 + (d.getMonth() - now.getMonth())
                        return Math.max(1, m)
                      } catch { return 120 }
                    }

                    const projectedFV = (g, contribution) => {
                      const r = annualRate / 12
                      const n = targetMonthsFor(g)
                      const factor = Math.pow(1 + r, n) - 1
                      return (g.current_savings || 0) * Math.pow(1 + r, n) + (contribution * factor) / r
                    }

                    const monthsToDate = (months) => {
                      const d = new Date()
                      d.setMonth(d.getMonth() + months)
                      return d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
                    }

                    const friendly = (n) => Math.round(n / 100) * 100

                    const goalStatuses = goals.map(g => {
                      const base = g.monthly_contribution || 5000
                      const fv = projectedFV(g, base)
                      const onTrack = fv >= g.target_amount
                      const monthsNeeded = computeMonths(g, base)
                      const extraNeeded = (() => {
                        if (onTrack) return 0
                        let lo = 0, hi = 200000
                        for (let i = 0; i < 40; i++) {
                          const mid = Math.round((lo + hi) / 2)
                          if (projectedFV(g, base + mid) >= g.target_amount) hi = mid
                          else lo = mid
                        }
                        return friendly(hi)
                      })()
                      return { g, base, onTrack, monthsNeeded, extraNeeded }
                    })

                    const onTrackCount = goalStatuses.filter(s => s.onTrack).length
                    const behindNames = goalStatuses.filter(s => !s.onTrack).map(s => s.g.name || s.g.goal_name)

                    const toggleGoal = (id) =>
                      setExpandedGoalId(prev => prev === id ? null : id)

                    const getSimContrib = (g) =>
                      goalSimContributions[g.goal_id] ?? (g.monthly_contribution || 5000)

                    const setSimContribForGoal = (g, val) => {
                      setGoalSimContributions(prev => ({ ...prev, [g.goal_id]: parseInt(val) }))
                      setGoalSimChips(prev => ({ ...prev, [g.goal_id]: 'custom' }))
                    }

                    const applyChip = (g, delta) => {
                      const base = g.monthly_contribution || 5000
                      const next = delta === 0 ? base : base + delta
                      setGoalSimContributions(prev => ({ ...prev, [g.goal_id]: next }))
                      setGoalSimChips(prev => ({ ...prev, [g.goal_id]: delta }))
                    }

                    return (
                      <div className="flex flex-col gap-3">

                        {/* ── Status Summary Banner ── */}
                        <div className="bg-card border border-border rounded-xl px-5 py-4">
                          <span className="text-[10px] font-extrabold uppercase tracking-widest text-muted-foreground">
                            Your goals
                          </span>
                          <p className="text-sm font-semibold text-foreground mt-1.5 leading-snug">
                            {onTrackCount === goals.length
                              ? `All ${goals.length} goals are on track. Keep going!`
                              : onTrackCount === 0
                                ? `${behindNames.join(' and ')} need${behindNames.length === 1 ? 's' : ''} attention to hit their dates.`
                                : `${onTrackCount} of ${goals.length} goals are on track.${
                                    behindNames.length === 1
                                      ? ` Your ${behindNames[0]} needs a boost to hit its date.`
                                      : ` ${behindNames.join(' and ')} need a boost.`
                                  }`
                            }
                          </p>
                          <div className="flex gap-2 mt-3 flex-wrap">
                            {onTrackCount > 0 && (
                              <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
                                {onTrackCount} on track
                              </span>
                            )}
                            {behindNames.length > 0 && (
                              <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-destructive/10 text-destructive border border-destructive/20">
                                {behindNames.length} need{behindNames.length === 1 ? 's' : ''} attention
                              </span>
                            )}
                          </div>
                        </div>

                        {/* ── Goal Accordion Cards ── */}
                        {goalStatuses.map(({ g, base, onTrack, monthsNeeded, extraNeeded }) => {
                          const id = g.goal_id
                          const isOpen = expandedGoalId === id
                          const pct = Math.min(100, Math.round((g.current_savings / g.target_amount) * 100))
                          const goalName = g.name || g.goal_name || 'Goal'
                          const arrivalDate = monthsToDate(monthsNeeded)
                          const targetDate = monthsToDate(targetMonthsFor(g))

                          const simC = getSimContrib(g)
                          const simM = computeMonths(g, simC)
                          const simDate = monthsToDate(simM)
                          const simDiff = simM - monthsNeeded
                          const selectedChip = goalSimChips[g.goal_id] ?? 0

                          return (
                            <div key={id}
                              className={`bg-card border rounded-xl overflow-hidden transition-all duration-200 ${
                                isOpen
                                  ? onTrack ? 'border-primary/40' : 'border-destructive/40'
                                  : 'border-border'
                              }`}>

                              {/* ── Card Header ── */}
                              <div
                                className="px-5 py-4 cursor-pointer select-none"
                                onClick={() => toggleGoal(id)}>

                                <div className="flex justify-between items-center">
                                  <span className="font-semibold text-sm text-foreground">{goalName}</span>
                                  <div className="flex items-center gap-2">
                                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-md border tracking-wide ${
                                      onTrack
                                        ? 'bg-primary/8 text-primary border-primary/20'
                                        : 'bg-destructive/8 text-destructive border-destructive/20'
                                    }`}>
                                      {onTrack ? 'On track' : 'Needs a boost'}
                                    </span>
                                    <ChevronDown
                                      className="w-4 h-4 text-muted-foreground transition-transform duration-200"
                                      style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
                                    />
                                  </div>
                                </div>

                                {/* Progress bar */}
                                <div className="mt-3 w-full bg-muted rounded-full h-1.5">
                                  <div
                                    className={`h-1.5 rounded-full transition-all duration-500 ${onTrack ? 'bg-primary' : 'bg-destructive'}`}
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <div className="flex justify-between text-[11px] mt-1.5">
                                  <span className="text-muted-foreground">
                                    <span className="font-semibold text-foreground">₹{g.current_savings.toLocaleString()}</span> saved
                                  </span>
                                  <span className="text-muted-foreground">of ₹{g.target_amount.toLocaleString()}</span>
                                </div>

                                {/* Status line */}
                                <p className={`text-xs mt-2.5 leading-relaxed ${onTrack ? 'text-primary' : 'text-destructive'}`}>
                                  {onTrack
                                    ? <>At <span className="font-semibold text-foreground">₹{friendly(base).toLocaleString()}/month</span>, you'll reach this by <span className="font-semibold text-foreground">{arrivalDate}</span> — right on schedule.</>
                                    : <>At ₹{friendly(base).toLocaleString()}/month you'd reach this in <span className="font-semibold">{arrivalDate}</span> — later than your target of {targetDate}. Saving <span className="font-semibold text-foreground">₹{extraNeeded.toLocaleString()}/month</span> more would get you back on schedule.</>
                                  }
                                </p>
                              </div>

                              {/* ── Simulator (expanded) ── */}
                              {isOpen && (
                                <div className="border-t border-border bg-muted/30 px-5 pb-5 pt-4">

                                  <p className="text-xs font-semibold text-foreground mb-0.5">See what happens if you save more</p>
                                  <p className="text-[11px] text-muted-foreground mb-3">Tap an option or drag the slider.</p>

                                  {/* Preset chips */}
                                  <div className="flex gap-2 flex-wrap mb-4">
                                    {[
                                      { label: 'Keep as is', delta: 0 },
                                      { label: '+₹2,000/mo', delta: 2000 },
                                      { label: '+₹5,000/mo', delta: 5000 },
                                      { label: '+₹10,000/mo', delta: 10000 },
                                    ].map(({ label, delta }) => (
                                      <button
                                        key={label}
                                        onClick={() => applyChip(g, delta)}
                                        className={`text-[11px] font-semibold px-3 py-1.5 rounded-full border transition-all ${
                                          selectedChip === delta
                                            ? 'bg-primary text-primary-foreground border-primary'
                                            : 'bg-background text-muted-foreground border-border hover:border-primary hover:text-primary'
                                        }`}>
                                        {label}
                                      </button>
                                    ))}
                                  </div>

                                  {/* Fine-tune slider */}
                                  <input
                                    type="range"
                                    min={base}
                                    max={base + 50000}
                                    step={500}
                                    value={simC}
                                    onChange={(e) => setSimContribForGoal(g, e.target.value)}
                                    className="w-full h-1.5 rounded-lg appearance-none cursor-pointer accent-primary"
                                  />
                                  <div className="flex justify-between text-[10px] text-muted-foreground mt-1 mb-4">
                                    <span>₹{friendly(base).toLocaleString()}/mo (current)</span>
                                    <span>₹{friendly(base + 50000).toLocaleString()}/mo</span>
                                  </div>

                                  {/* Result card */}
                                  <div className="bg-card border border-border rounded-lg p-4">
                                    <div className="flex justify-between items-start">
                                      <div>
                                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-bold mb-0.5">Projected arrival</p>
                                        <p className="text-base font-bold text-foreground">{simDate}</p>
                                        {simC !== base && (
                                          <p className={`text-[11px] mt-0.5 font-semibold ${simDiff < 0 ? 'text-primary' : 'text-destructive'}`}>
                                            {simDiff < 0
                                              ? `${Math.abs(simDiff)} month${Math.abs(simDiff) !== 1 ? 's' : ''} earlier`
                                              : `${simDiff} month${simDiff !== 1 ? 's' : ''} later`
                                            }
                                          </p>
                                        )}
                                      </div>
                                      <div className="text-right">
                                        <p className="text-[10px] text-muted-foreground uppercase tracking-wide font-bold mb-0.5">Monthly saving</p>
                                        <p className={`text-base font-bold ${onTrack ? 'text-primary' : 'text-destructive'}`}>
                                          ₹{simC.toLocaleString()}/mo
                                        </p>
                                      </div>
                                    </div>
                                  </div>

                                  {/* Assumption disclosure */}
                                  <p className="text-[10.5px] leading-relaxed mt-3 px-3 py-2.5 rounded-lg bg-primary/5 border border-primary/15 text-primary">
                                    Assumes ~{Math.round(annualRate * 100)}% average yearly growth based on your {risk.toLowerCase()} risk profile.
                                    Real markets move up and down — this is an estimate, not a guarantee.
                                  </p>

                                  {/* CTA */}
                                  {simC > base && (
                                    <button
                                      className="w-full mt-3 py-3 rounded-lg text-sm font-bold bg-primary text-primary-foreground hover:opacity-90 active:opacity-75 transition-opacity"
                                      onClick={() => showNotification(`Your request to increase contributions for "${goalName}" has been sent to your advisor.`, 'success')}
                                    >
                                      Increase my monthly contribution
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}

                      </div>
                    )
                  })()}

                  {/* TAB 4: RECOMMENDATIONS */}
                  {activeCustomerTab === 'recommendations' && recommendations && (
                    <div className="flex flex-col gap-6">
                      <div className="bg-card border border-border rounded-2xl p-6">
                        <h2 className="text-xl font-bold">What we suggest, and why</h2>
                        <p className="text-sm text-muted-foreground mt-1">{recommendations.summary}</p>
                      </div>

                      <div className="flex flex-col gap-4">
                        {recommendations.recommendations && recommendations.recommendations.map((rec, index) => (
                          <RecommendationCard
                            key={index}
                            rec={rec}
                            index={index}
                            showNotification={showNotification}
                            triggerRmLead={triggerRmLead}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}


          </>
        )}
      </main>

      {/* Mobile Slide-over Menu Drawer */}
      <div
        className={`fixed inset-0 z-50 transition-opacity duration-300 ${mobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
      >
        {/* Backdrop overlay */}
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        />

        {/* Drawer Content */}
        <div
          className={`absolute top-0 bottom-0 left-0 w-80 bg-card border-r border-border p-6 flex flex-col justify-between shadow-2xl transition-transform duration-350 ease-out transform ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
            }`}
        >
          <div>
            {/* Drawer Header with Close Button */}
            <div className="flex items-center justify-between pb-6 border-b border-border">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-primary" />
                <span className="font-bold text-sm tracking-tight text-foreground">IDBI AI Menu</span>
              </div>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>



            {/* Active Profile Switcher (Mobile Menu) */}
            <div className="mt-4 p-3.5 bg-muted border border-border rounded-2xl">
              <label className="text-[10px] font-extrabold text-muted-foreground uppercase tracking-wider mb-2 block">
                Active Profile
              </label>
              <div className="flex items-center gap-2 bg-card border border-border rounded-xl px-3 py-2">
                <User className="w-4 h-4 text-primary" />
                <select
                  value={activeProfileId}
                  onChange={(e) => {
                    setActiveProfileId(e.target.value)
                    setMobileMenuOpen(false)
                  }}
                  className="bg-transparent text-xs font-semibold text-foreground focus:outline-none cursor-pointer w-full"
                >
                  {profiles.map(p => (
                    <option key={p.profile_id} value={p.profile_id} className="bg-card text-foreground">
                      {p.name} ({p.occupation})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Customer Specific Drawer Items */}
            {currentLens === 'customer' && (
              <>
                {/* Profile Brief */}
                <div className="mt-4 p-3.5 bg-muted/50 border border-border rounded-2xl flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                      <User className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-xs font-bold text-foreground truncate">{profile?.name}</h4>
                      <p className="text-[10px] text-muted-foreground truncate">{profile?.occupation} | Age {profile?.age}</p>
                    </div>
                  </div>

                  <div className="flex gap-2 border-t border-border pt-3">
                    <span className="text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border bg-muted text-muted-foreground border-border">
                      {profile?.risk_profile?.risk_category || 'Moderate'}
                    </span>
                    <span className="bg-primary/10 border border-primary/20 text-primary text-[10px] px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 uppercase tracking-wider">
                      <Languages className="w-2.5 h-2.5" /> {profile?.language_preference || 'English'}
                    </span>
                  </div>
                </div>

                {/* Menu Options */}
                <nav className="mt-6 flex flex-col gap-2">
                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1 px-1">
                    Navigation
                  </div>

                  {/* Navigation Menu Items */}
                  <button
                    onClick={() => {
                      setActiveCustomerTab('overview')
                      setMobileMenuOpen(false)
                    }}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all duration-200 ${activeCustomerTab === 'overview'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted/20 border-border hover:border-primary/40 text-muted-foreground hover:text-foreground'
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <Briefcase className="w-4 h-4" />
                      <span className="text-xs font-semibold">Account Overview</span>
                    </div>
                    {activeCustomerTab === 'overview' && <CheckCircle className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => {
                      setActiveCustomerTab('spending')
                      setMobileMenuOpen(false)
                    }}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all duration-200 ${activeCustomerTab === 'spending'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted/20 border-border hover:border-primary/40 text-muted-foreground hover:text-foreground'
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <Coins className="w-4 h-4" />
                      <span className="text-xs font-semibold">Spending Analyzer</span>
                    </div>
                    {activeCustomerTab === 'spending' && <CheckCircle className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => {
                      setActiveCustomerTab('goals')
                      setMobileMenuOpen(false)
                    }}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all duration-200 ${activeCustomerTab === 'goals'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted/20 border-border hover:border-primary/40 text-muted-foreground hover:text-foreground'
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <Target className="w-4 h-4" />
                      <span className="text-xs font-semibold">Goals & What-If</span>
                    </div>
                    {activeCustomerTab === 'goals' && <CheckCircle className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => {
                      setActiveCustomerTab('recommendations')
                      setMobileMenuOpen(false)
                    }}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all duration-200 ${activeCustomerTab === 'recommendations'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted/20 border-border hover:border-primary/40 text-muted-foreground hover:text-foreground'
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <Shield className="w-4 h-4" />
                      <span className="text-xs font-semibold">AI Wealth Advisory</span>
                    </div>
                    {activeCustomerTab === 'recommendations' && <CheckCircle className="w-4 h-4" />}
                  </button>

                  {/* Space divider */}
                  <div className="h-px bg-border my-3" />

                  <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1 px-1">
                    Actions
                  </div>

                  {/* Retake Goal Quiz Button - Highlighted */}
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false)
                      navigate('/quiz')
                    }}
                    className="flex items-center justify-between p-3.5 rounded-2xl bg-secondary border border-border hover:border-primary/40 text-secondary-foreground cursor-pointer active:scale-[0.98] transition-all duration-200 shadow-lg group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
                        <Target className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex flex-col text-left">
                        <span className="text-xs font-bold text-foreground">
                          {quizStatus?.quiz_completed ? 'Retake Goal Quiz' : 'Take Goal Quiz'}
                        </span>
                        <span className="text-[8px] text-muted-foreground font-semibold tracking-wider uppercase mt-0.5">
                          Update your profile
                        </span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-primary group-hover:translate-x-1 transition-transform" />
                  </button>
                </nav>
              </>
            )}
          </div>

          {/* Drawer Footer */}
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="w-full px-4 py-2.5 bg-muted hover:bg-muted/80 border border-border rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground transition-all"
            >
              Close Menu
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
