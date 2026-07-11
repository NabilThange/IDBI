import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext'
import apiClient from '@/lib/apiClient'
import { 
  CaretRight as ChevronRight, CaretLeft as ChevronLeft, CheckCircle, Target, TrendUp as TrendingUp, 
  Shield, Sparkle as Sparkles, Question, Briefcase, Plus,
  Lifebuoy, House, GraduationCap, TreePalm, Airplane, CreditCard
} from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
 
const PRIORITY_OPTIONS = [
  { value: 'emergency_fund', label: 'Emergency Fund', icon: 'LifeBuoy', desc: 'Safety net coverage' },
  { value: 'home_purchase', label: 'Buy a Home', icon: 'Home', desc: 'Real estate savings' },
  { value: 'children_education', label: "Child's Education", icon: 'GraduationCap', desc: 'School & college funds' },
  { value: 'retirement', label: 'Retirement', icon: 'Palmtree', desc: 'Pension & long-term wealth' },
  { value: 'business_startup', label: 'Start/Grow Business', icon: 'Briefcase', desc: 'Equity & venture capital' },
  { value: 'travel_lifestyle', label: 'Travel & Lifestyle', icon: 'Plane', desc: 'Leisure and milestones' },
  { value: 'debt_repayment', label: 'Debt Repayment', icon: 'CreditCard', desc: 'Clearing high-cost loans' },
  { value: 'wealth_growth', label: 'Wealth Growth', icon: 'TrendingUp', desc: 'General compounding' }
]
 
const renderPriorityIcon = (iconName, className = "w-5 h-5") => {
  switch (iconName) {
    case 'LifeBuoy': return <Lifebuoy className={className} />;
    case 'Home': return <House className={className} />;
    case 'GraduationCap': return <GraduationCap className={className} />;
    case 'Palmtree': return <TreePalm className={className} />;
    case 'Briefcase': return <Briefcase className={className} />;
    case 'Plane': return <Airplane className={className} />;
    case 'CreditCard': return <CreditCard className={className} />;
    case 'TrendingUp': return <TrendingUp className={className} />;
    default: return null;
  }
}

const TIMELINE_OPTIONS = [
  { value: 'within_1_year', label: '< 1 year' },
  { value: '1_3_years', label: '1-3 years' },
  { value: '3_5_years', label: '3-5 years' },
  { value: '5_10_years', label: '5-10 years' },
  { value: '10_plus_years', label: '10+ years' },
  { value: 'ongoing', label: 'Ongoing' }
]

export default function GoalQuiz() {
  const { profile } = useSession()
  const navigate = useNavigate()
  
  const [currentStep, setCurrentStep] = useState(0) // 0 = Framing, 1 = About, 2 = Protection, 3 = Goals, 4 = Risk, 5 = Confirm
  const [submitting, setSubmitting] = useState(false)
  
  // Step 1: About You
  const [lifeStage, setLifeStage] = useState('building_wealth')
  const [dependents, setDependents] = useState('nobody')
  const [incomeStability, setIncomeStability] = useState('fixed')
  
  // Step 2: Protection Check
  const [healthInsurance, setHealthInsurance] = useState('employer_only')
  const [emergencySource, setEmergencySource] = useState('savings')
  
  // Step 3: Goals
  const [priorities, setPriorities] = useState(['emergency_fund', 'home_purchase'])
  const [goals, setGoals] = useState([])
  
  // Step 4: Risk Tolerance
  const [priorExperience, setPriorExperience] = useState('little')
  const [investmentPreference, setInvestmentPreference] = useState('balanced_mf')
  const [volatilityTolerance, setVolatilityTolerance] = useState('stay_calm')
  const [capacityLossTolerance, setCapacityLossTolerance] = useState('manage')

  const handlePriorityToggle = (priority) => {
    if (priorities.includes(priority)) {
      setPriorities(priorities.filter(p => p !== priority))
      setGoals(goals.filter(g => g.goal_type !== priority))
    } else if (priorities.length < 3) {
      setPriorities([...priorities, priority])
      // Initialize goal detail if not present
      if (!goals.some(g => g.goal_type === priority)) {
        setGoals(prev => [...prev, {
          goal_type: priority,
          timeline: '1_3_years',
          target_amount: 1000000,
          current_savings: 100000,
          priority: priorities.length + 1
        }])
      }
    }
  }

  const handleGoalDetailUpdate = (goalType, field, value) => {
    setGoals(prev => {
      const idx = prev.findIndex(g => g.goal_type === goalType)
      const updated = [...prev]
      if (idx >= 0) {
        updated[idx] = { ...updated[idx], [field]: value }
      } else {
        updated.push({
          goal_type: goalType,
          timeline: '1_3_years',
          target_amount: 1000000,
          current_savings: 100000,
          priority: priorities.indexOf(goalType) + 1,
          [field]: value
        })
      }
      return updated
    })
  }

  const getGoalDetail = (goalType) => {
    const existing = goals.find(g => g.goal_type === goalType)
    if (existing) return existing
    
    // Default fallback values
    return {
      goal_type: goalType,
      timeline: '1_3_years',
      target_amount: 1000000,
      current_savings: 0,
      priority: priorities.indexOf(goalType) + 1
    }
  }

  const canProceedFromStep3 = () => {
    if (priorities.length === 0) return false
    return priorities.every(p => {
      const g = getGoalDetail(p)
      if (g.timeline !== 'ongoing') {
        return g.target_amount !== null && g.target_amount > 0
      }
      return true
    })
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const submission = {
        customer_id: profile?.profile_id || 'guest_user',
        step1: {
          life_stage: lifeStage,
          priorities: priorities,
          dependents: dependents,
          income_stability: incomeStability,
          health_insurance: healthInsurance,
          emergency_source: emergencySource
        },
        step2: {
          goals: priorities.map((p, idx) => {
            const detail = getGoalDetail(p)
            return {
              goal_type: p,
              timeline: detail.timeline,
              target_amount: detail.timeline === 'ongoing' ? null : detail.target_amount,
              current_savings: detail.current_savings,
              priority: idx + 1
            }
          })
        },
        step3: {
          investment_preference: investmentPreference,
          volatility_tolerance: volatilityTolerance,
          prior_experience: priorExperience,
          capacity_loss_tolerance: capacityLossTolerance
        }
      }
      await apiClient.post('/api/quiz/submit', submission)
      navigate('/dashboard')
    } catch (error) {
      console.error('Error submitting quiz:', error)
      alert('Failed to save onboarding details. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const stepLabels = ["Start", "About You", "Safety Net", "Goals", "Risk Comfort", "Confirm"]

  return (
    <div className="quiz-page h-[100dvh] overflow-hidden bg-slate-950 text-slate-100 p-3 sm:p-8 flex flex-col relative font-sans select-none">

      <div className="quiz-shell max-w-xl mx-auto w-full min-h-0 flex-1 flex flex-col">
        
        {/* Stepper (Only show after step 0) */}
        {currentStep > 0 && (
          <div className="quiz-progress mb-8 mt-2">
            <div className="flex justify-between items-center relative px-2">
              <div className="absolute top-3.5 left-6 right-6 h-[2px] bg-slate-800 z-0"></div>
              {stepLabels.map((label, idx) => {
                if (idx === 0) return null
                const isActive = currentStep === idx
                const isCompleted = currentStep > idx
                return (
                  <div key={idx} className="flex flex-col items-center gap-1.5 z-10 cursor-pointer" onClick={() => goStep(idx)}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all border ${
                      isActive 
                        ? 'bg-primary border-primary text-primary-foreground shadow-lg' 
                        : isCompleted 
                        ? 'bg-card border-accent text-accent' 
                        : 'bg-muted border-border text-muted-foreground'
                    }`}>
                      {isCompleted ? '✓' : idx}
                    </div>
                    <span className={`text-[9px] font-bold tracking-tight uppercase ${isActive ? 'text-primary' : 'text-muted-foreground'}`}>
                      {label}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Wizard Panel */}
        <Card className="quiz-card bg-slate-900/40 backdrop-blur-xl border border-slate-850 shadow-2xl rounded-3xl min-h-0 flex-1 flex flex-col mb-6 overflow-hidden">
          
          {/* Step Headers */}
          {currentStep > 0 && (
            <CardHeader className="quiz-step-header p-5 border-b border-slate-850 bg-slate-950/20">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-center">
                  {currentStep === 1 && <Target className="w-5 h-5 text-primary" />}
                  {currentStep === 2 && <Shield className="w-5 h-5 text-accent" />}
                  {currentStep === 3 && <TrendingUp className="w-5 h-5 text-primary" />}
                  {currentStep === 4 && <Question className="w-5 h-5 text-primary" />}
                  {currentStep === 5 && <Sparkles className="w-5 h-5 text-primary" />}
                </div>
                <div>
                  <CardTitle className="text-sm font-extrabold text-slate-100">
                    {currentStep === 1 && "About Your Life"}
                    {currentStep === 2 && "Emergency Safety Net"}
                    {currentStep === 3 && "Financial Goals Planner"}
                    {currentStep === 4 && "Risk Tolerance & Capacity"}
                    {currentStep === 5 && "Review Onboarding Recap"}
                  </CardTitle>
                  <CardDescription className="text-[10px] text-slate-400">
                    {currentStep === 1 && "Understand income streams and dependencies"}
                    {currentStep === 2 && "Evaluate insurance and emergency readiness"}
                    {currentStep === 3 && "Calculate target timelines and savings progress"}
                    {currentStep === 4 && "Check risk attitude vs objective risk capacity"}
                    {currentStep === 5 && "Confirm details before mapping recommendations"}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
          )}

          <CardContent className="quiz-content space-y-6 flex-1 min-h-0 overflow-y-auto overscroll-contain">
            
            {/* SCREEN 0: Framing */}
            {currentStep === 0 && (
              <div className="quiz-welcome space-y-6 py-6 text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-primary/10 border border-primary/20 rounded-2xl mb-2">
                  <Sparkles className="w-7 h-7 text-primary" />
                </div>
                <div className="space-y-2">
                  <span className="text-[10px] font-bold tracking-widest text-primary uppercase">Your financial snapshot</span>
                  <h1 className="text-2xl font-black text-slate-100 tracking-tight">Build a plan that fits your life</h1>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                    We will ask about your dependents, your safety buffers, and risk thresholds — so we never recommend something that doesn't fit your life.
                  </p>
                </div>

                <div className="quiz-start-progress" aria-label="You are 16% of the way through your financial snapshot">
                  <div className="flex items-center justify-between text-[11px] font-bold">
                    <span>Profile started</span>
                    <span>16%</span>
                  </div>
                  <div><span /></div>
                </div>

                <div className="bg-slate-950/40 border border-slate-850 p-4 rounded-2xl text-left max-w-sm mx-auto">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-300">What you will cover</h4>
                  <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                    Standard risk questionnaires miss financial capacity. Evaluating dependents and safety buffers ensures we prioritize protection and safety nets before exposing savings to market risks.
                  </p>
                </div>

                <div className="pt-4">
                  <Button onClick={() => setCurrentStep(1)} className="quiz-primary-action w-full sm:w-60 mx-auto py-5 bg-accent hover:bg-accent/90 text-accent-foreground font-extrabold text-xs rounded-2xl shadow-lg shadow-accent/30 active:scale-[0.98] transition">
                    Continue to your profile
                  </Button>
                </div>
              </div>
            )}

            {/* SCREEN 1: About You */}
            {currentStep === 1 && (
              <div className="space-y-6">
                {/* Life Stage */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">1. Describe where you are right now</label>
                  <div className="space-y-2">
                    {[
                      { val: 'starting_career', title: 'Just starting out', desc: 'First job, building first savings' },
                      { val: 'building_wealth', title: 'Building wealth', desc: 'Established income, growing family or assets' },
                      { val: 'major_milestones', title: 'Planning major milestones', desc: 'Buying a home, marriage, education' },
                      { val: 'retired', title: 'Nearing or in retirement', desc: 'Protecting capital and legacy' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setLifeStage(opt.val)}
                        className={`p-3 border rounded-2xl cursor-pointer transition-all duration-200 ${
                          lifeStage === opt.val 
                            ? 'border-primary bg-primary/10' 
                            : 'border-slate-800 bg-slate-950/20 hover:border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-bold text-slate-100">{opt.title}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Dependents */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">2. Who depends on you financially?</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { val: 'nobody', label: 'Nobody' },
                      { val: 'spouse', label: 'Spouse' },
                      { val: 'kids', label: 'Kids' },
                      { val: 'parents', label: 'Parents' },
                      { val: 'multiple', label: 'Multiple Dependents' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setDependents(opt.val)}
                        className={`px-4 py-2 border rounded-full text-xs font-bold cursor-pointer transition-all ${
                          dependents === opt.val 
                            ? 'bg-primary border-primary text-white' 
                            : 'bg-slate-950/30 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        {opt.label}
                      </div>
                    ))}
                  </div>
                  <div className="bg-slate-950/30 border border-slate-855 p-3.5 rounded-2xl text-[11px] text-slate-400 leading-relaxed mt-2">
                    <span className="font-bold text-primary block mb-0.5">Why we ask:</span>
                    Family dependencies represent non-negotiable liabilities. Higher dependency scores shift AI recommendations toward emergency savings and insurance.
                  </div>
                </div>

                {/* Income Stability */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">3. How steady is your income?</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { val: 'fixed', label: 'Fixed Salary' },
                      { val: 'commission', label: 'Commission/Bonus' },
                      { val: 'business', label: 'Business Owner' },
                      { val: 'mixed', label: 'Mix of These' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setIncomeStability(opt.val)}
                        className={`px-4 py-2 border rounded-full text-xs font-bold cursor-pointer transition-all ${
                          incomeStability === opt.val 
                            ? 'bg-primary border-primary text-primary-foreground' 
                            : 'bg-muted/30 border-border text-muted-foreground hover:border-primary'
                        }`}
                      >
                        {opt.label}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* SCREEN 2: Protection Check */}
            {currentStep === 2 && (
              <div className="space-y-6">
                {/* Health Insurance */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">1. Do you have health insurance beyond what your employer gives you?</label>
                  <div className="space-y-2">
                    {[
                      { val: 'own_cover', title: 'Yes, I have my own cover', desc: 'Independently owned health coverage' },
                      { val: 'employer_only', title: 'Only what my employer provides', desc: 'Provided by employer; risk of lapse on job change' },
                      { val: 'no_cover', title: 'No cover', desc: 'Critical protection gap' },
                      { val: 'not_sure', title: 'Not sure', desc: 'Needs compliance review' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setHealthInsurance(opt.val)}
                        className={`p-3 border rounded-2xl cursor-pointer transition-all duration-200 ${
                          healthInsurance === opt.val 
                            ? 'border-primary bg-primary/10' 
                            : 'border-border bg-muted/20 hover:border-primary'
                        }`}
                      >
                        <div className="text-xs font-bold text-slate-100">{opt.title}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Emergency Buffer */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">2. Emergency funding sources</label>
                  <span className="block text-[11px] text-slate-405">If you needed ₹1,00,000 tomorrow for an emergency, where would it come from?</span>
                  <div className="space-y-2">
                    {[
                      { val: 'savings', title: 'From savings, easily', desc: 'Safety buffer is fully operational' },
                      { val: 'sell_investments', title: "I'd have to sell investments", desc: 'Depletes investment growth prematurely' },
                      { val: 'borrow', title: "I'd have to borrow", desc: 'Generates high-interest liability' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setEmergencySource(opt.val)}
                        className={`p-3 border rounded-2xl cursor-pointer transition-all duration-200 ${
                          emergencySource === opt.val 
                            ? 'border-primary bg-primary/10' 
                            : 'border-border bg-muted/20 hover:border-primary'
                        }`}
                      >
                        <div className="text-xs font-bold text-slate-100">{opt.title}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-slate-950/30 border border-slate-855 p-3.5 rounded-2xl text-[11px] text-slate-400 leading-relaxed mt-2">
                    <span className="font-bold text-accent block mb-0.5">Why we ask:</span>
                    Safety buffers protect against market shocks. Debt-funded emergency coverage implies extreme downside vulnerability.
                  </div>
                </div>
              </div>
            )}

            {/* SCREEN 3: Goals */}
            {currentStep === 3 && (
              <div className="space-y-6">
                {/* Priorities Multiselect */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">1. Select your top priorities</label>
                  <span className="block text-[10px] text-slate-405 mt-1">(Select 1 to 3 goals you want to plan for)</span>
                  <div className="grid grid-cols-2 gap-2">
                    {PRIORITY_OPTIONS.map(opt => {
                      const isSelected = priorities.includes(opt.value)
                      return (
                        <div 
                          key={opt.value}
                          onClick={() => handlePriorityToggle(opt.value)}
                          className={`p-2.5 border rounded-2xl cursor-pointer transition-all flex items-center gap-2.5 ${
                            isSelected 
                              ? 'bg-primary/10 border-primary text-foreground font-bold' 
                              : 'bg-muted/30 border-border text-muted-foreground hover:border-primary'
                          } ${priorities.length >= 3 && !isSelected ? 'opacity-40 cursor-not-allowed' : ''}`}
                        >
                          {renderPriorityIcon(opt.icon, isSelected ? "w-4.5 h-4.5 text-primary" : "w-4.5 h-4.5 text-muted-foreground")}
                          <span className="text-[10px] truncate">{opt.label}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Inline Goals Setup */}
                {priorities.length > 0 && (
                  <div className="space-y-4 pt-2 border-t border-slate-850">
                    <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">2. Goal configuration ({goals.length} of {priorities.length})</label>
                    <div className="space-y-4">
                      {priorities.map((priority, idx) => {
                        const g = getGoalDetail(priority)
                        const opt = PRIORITY_OPTIONS.find(o => o.value === priority)
                        const hasTarget = g.timeline !== 'ongoing'
                        const progressPct = hasTarget && g.target_amount ? Math.min(100, Math.round((g.current_savings / g.target_amount) * 100)) : 0
                        
                        return (
                          <div key={priority} className="bg-slate-950/50 border border-slate-850 p-4 rounded-2xl space-y-4">
                            <div className="flex justify-between items-center">
                              <span className="text-xs font-bold text-foreground flex items-center gap-2">
                                {renderPriorityIcon(opt?.icon, "w-4.5 h-4.5 text-primary")} {opt?.label}
                              </span>
                              <span className="bg-slate-900 border border-slate-800 text-[9px] text-slate-400 px-2 py-0.5 rounded font-mono uppercase">
                                Goal {idx + 1}
                              </span>
                            </div>

                            {/* Goal Timeline Selection */}
                            <div className="space-y-1.5">
                              <span className="text-[10px] text-slate-400 font-semibold block">Target Timeline</span>
                              <div className="flex flex-wrap gap-1.5">
                                {TIMELINE_OPTIONS.map(timeOpt => (
                                  <button
                                    key={timeOpt.value}
                                    type="button"
                                    onClick={() => handleGoalDetailUpdate(priority, 'timeline', timeOpt.value)}
                                    className={`px-2.5 py-1 text-[9px] font-bold rounded-lg border transition-all ${
                                      g.timeline === timeOpt.value
                                        ? 'bg-primary/20 border-primary text-primary'
                                        : 'bg-muted/60 border-border text-muted-foreground hover:border-primary'
                                    }`}
                                  >
                                    {timeOpt.label}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Goal Target Amount (Only if timeline != ongoing) */}
                            {hasTarget && (
                              <div className="space-y-1.5">
                                <div className="flex justify-between items-center">
                                  <span className="text-[10px] text-slate-400 font-semibold">Target Amount</span>
                                  <span className="text-xs font-bold text-primary">₹{(g.target_amount || 0).toLocaleString('en-IN')}</span>
                                </div>
                                <input
                                  type="number"
                                  placeholder="Enter Target Amount in ₹"
                                  value={g.target_amount || ''}
                                  onChange={(e) => handleGoalDetailUpdate(priority, 'target_amount', parseInt(e.target.value) || 0)}
                                  className="w-full p-2.5 bg-muted border border-border rounded-xl text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary font-mono"
                                />
                                
                                {/* Amount Quick Chips */}
                                <div className="flex gap-1.5 flex-wrap">
                                  {[
                                    { label: '₹1L', val: 100000 },
                                    { label: '₹5L', val: 500000 },
                                    { label: '₹10L', val: 1000000 },
                                    { label: '₹25L', val: 2500000 }
                                  ].map(chip => (
                                    <button
                                      key={chip.val}
                                      type="button"
                                      onClick={() => handleGoalDetailUpdate(priority, 'target_amount', chip.val)}
                                      className="px-2.5 py-1 text-[9px] font-bold border border-slate-800 bg-slate-900 hover:bg-slate-800 rounded-lg text-slate-400 transition-all"
                                    >
                                      {chip.label}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Goal Current Savings */}
                            <div className="space-y-1.5">
                              <div className="flex justify-between items-center">
                                <span className="text-[10px] text-slate-400 font-semibold">How much have you already saved?</span>
                                  <span className="text-xs font-bold text-accent">₹{(g.current_savings || 0).toLocaleString('en-IN')}</span>
                              </div>
                              <input
                                type="number"
                                placeholder="Enter current savings in ₹"
                                value={g.current_savings || ''}
                                onChange={(e) => handleGoalDetailUpdate(priority, 'current_savings', parseInt(e.target.value) || 0)}
                                className="w-full p-2.5 bg-muted border border-border rounded-xl text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary font-mono"
                              />

                              {/* Live Progress feedback if target is positive */}
                              {hasTarget && g.target_amount > 0 && (
                                <div className="pt-2">
                                  <div className="flex justify-between text-[9px] text-slate-405 font-semibold mb-1">
                                    <span>Goal Progress</span>
                                    <span>{progressPct}% of target reached</span>
                                  </div>
                                  <div className="w-full bg-slate-900 border border-slate-850 h-2 rounded-full overflow-hidden">
                                    <div className="bg-accent h-full rounded-full transition-all duration-300" style={{ width: `${progressPct}%` }}></div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* SCREEN 4: Risk Comfort */}
            {currentStep === 4 && (
              <div className="space-y-6">
                {/* Investment Experience */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">1. Prior investment experience</label>
                  <span className="block text-[11px] text-slate-400">Have you invested in anything besides FDs or a savings account before?</span>
                  <div className="flex gap-2">
                    {[
                      { val: 'never', label: 'Never' },
                      { val: 'little', label: 'A little' },
                      { val: 'regular', label: 'Yes, regularly' }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setPriorExperience(opt.val)}
                        className={`flex-1 text-center py-3 border rounded-2xl text-xs font-bold cursor-pointer transition-all ${
                          priorExperience === opt.val 
                            ? 'bg-primary border-primary text-white' 
                            : 'bg-slate-950/30 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        {opt.label}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Attitudinal Volatility comfort */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">2. Attitudinal reaction to market drops</label>
                  <span className="block text-[11px] text-slate-400">If ₹10,000 dropped to ₹8,500 for a while before recovering, what would you do?</span>
                  <div className="space-y-2">
                    {[
                      { val: 'panic_withdraw', title: "Sell — I can't watch it drop further", desc: "Withdraw everything, I cannot tolerate watching asset value slide" },
                      { val: 'uncomfortable_wait', title: "Uncomfortable, but I'd wait it out", desc: "Feel uncomfortable, but wait it out rather than crystallize loss" },
                      { val: 'stay_calm', title: "Stay calm, I know it can recover", desc: "Keep holding, I know markets recover over time" },
                      { val: 'buying_opportunity', title: "Add more — it's a better price", desc: "See it as a buying opportunity and allocate more capital" }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setVolatilityTolerance(opt.val)}
                        className={`p-3 border rounded-2xl cursor-pointer transition-all duration-200 ${
                          volatilityTolerance === opt.val 
                            ? 'border-primary bg-primary/10' 
                            : 'border-slate-800 bg-slate-950/20 hover:border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-bold text-slate-100">{opt.title}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Capacity Volatility comfort */}
                <div className="space-y-2.5">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">3. Capacity for loss in specific goal</label>
                  <span className="block text-[11px] text-slate-400">If your primary savings goals dropped in value right when you needed to withdraw, what would happen?</span>
                  <div className="space-y-2">
                    {[
                      { val: 'manage', title: "I'd manage — I have other savings too", desc: "I have other savings or flexible timelines to cover" },
                      { val: 'setback', title: "It would genuinely set me back", desc: "It would genuinely disrupt my life or force borrowing" }
                    ].map(opt => (
                      <div 
                        key={opt.val} 
                        onClick={() => setCapacityLossTolerance(opt.val)}
                        className={`p-3 border rounded-2xl cursor-pointer transition-all duration-200 ${
                          capacityLossTolerance === opt.val 
                            ? 'border-primary bg-primary/10' 
                            : 'border-slate-800 bg-slate-950/20 hover:border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-bold text-slate-100">{opt.title}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-slate-950/30 border border-slate-855 p-3.5 rounded-2xl text-[11px] text-slate-400 leading-relaxed mt-2">
                    <span className="font-bold text-primary block mb-0.5">Why two drop questions:</span>
                    The first measures how you <i>feel</i> (attitude). This measures what you can actually <i>afford</i> (capacity) given your liabilities. Both are required for compliance.
                  </div>
                </div>
              </div>
            )}

            {/* SCREEN 5: Recap & Confirm */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <div className="quiz-digest bg-primary/10 border border-primary/20 p-5 rounded-2xl space-y-4">
                  <span className="text-[9px] font-bold tracking-widest text-primary uppercase block">Onboarding Digest</span>
                  <div className="text-slate-200 text-xs leading-relaxed space-y-4">
                    
                    {/* Item 1 */}
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        You are in the <strong className="text-slate-100">
                          {lifeStage === 'starting_career' ? 'starting career' : lifeStage === 'building_wealth' ? 'wealth building' : lifeStage === 'major_milestones' ? 'milestone planning' : 'retirement'}
                        </strong> stage of life, with <strong className="text-slate-100">
                          {dependents === 'nobody' ? 'no financial dependents' : dependents === 'spouse' ? 'spouse dependent' : dependents === 'kids' ? 'children dependents' : dependents === 'parents' ? 'parents dependents' : 'multiple dependents'}
                        </strong>.
                      </div>
                      <button onClick={() => goStep(1)} className="text-[9px] font-extrabold uppercase text-primary hover:text-primary/80 flex-shrink-0 border border-primary/30 px-2.5 py-1 rounded bg-primary/10 cursor-pointer">
                        fix
                      </button>
                    </div>

                    {/* Item 2 */}
                    <div className="flex justify-between items-start gap-4 border-t border-slate-900 pt-3">
                      <div>
                        Your emergency fund tomorrow would come from <strong className="text-slate-100">
                          {emergencySource === 'savings' ? 'cash savings' : emergencySource === 'sell_investments' ? 'selling assets' : 'borrowing/credit'}
                        </strong>, and you have <strong className="text-slate-100">
                          {healthInsurance === 'own_cover' ? 'personal custom health insurance' : healthInsurance === 'employer_only' ? 'employer corporate health cover only' : 'no secondary cover'}
                        </strong>.
                      </div>
                      <button onClick={() => goStep(2)} className="text-[9px] font-extrabold uppercase text-primary hover:text-primary/80 flex-shrink-0 border border-primary/30 px-2.5 py-1 rounded bg-primary/10 cursor-pointer">
                        fix
                      </button>
                    </div>

                    {/* Item 3 */}
                    <div className="flex justify-between items-start gap-4 border-t border-slate-900 pt-3">
                      <div>
                        You are targeting <strong className="text-slate-100">{priorities.length} specific goals</strong>: {priorities.map(p => PRIORITY_OPTIONS.find(o => o.value === p)?.label).join(', ')}.
                      </div>
                      <button onClick={() => goStep(3)} className="text-[9px] font-extrabold uppercase text-primary hover:text-primary/80 flex-shrink-0 border border-primary/30 px-2.5 py-1 rounded bg-primary/10 cursor-pointer">
                        fix
                      </button>
                    </div>

                    {/* Item 4 */}
                    <div className="flex justify-between items-start gap-4 border-t border-slate-900 pt-3">
                      <div>
                        You are <strong className="text-slate-100">{priorExperience === 'never' ? 'new to investing' : 'somewhat experienced'}</strong>. If market assets drop 15%, you would <strong className="text-slate-100">
                          {volatilityTolerance === 'panic_withdraw' ? 'panic-sell' : volatilityTolerance === 'uncomfortable_wait' ? 'wait out the dip' : volatilityTolerance === 'stay_calm' ? 'stay calm' : 'invest more'}
                        </strong>, and a loss in goal funds is a <strong className="text-slate-100">{capacityLossTolerance === 'manage' ? 'manageable risk' : 'major setback'}</strong>.
                      </div>
                      <button onClick={() => goStep(4)} className="text-[9px] font-extrabold uppercase text-primary hover:text-primary/80 flex-shrink-0 border border-primary/30 px-2.5 py-1 rounded bg-primary/10 cursor-pointer">
                        fix
                      </button>
                    </div>

                  </div>
                </div>
              </div>
            )}
          </CardContent>

          {/* Stepper Navigation Actions */}
          {currentStep > 0 && (
            <div className="quiz-actions p-4 border-t border-slate-855 flex justify-between gap-3 bg-slate-950/30">
              <Button
                onClick={prevStep}
                variant="outline"
                className="flex-1 border-slate-800 bg-slate-950 text-slate-400 hover:bg-slate-900 text-xs font-bold py-2 rounded-xl"
              >
                Previous
              </Button>

              {currentStep < 5 ? (
                <Button
                  onClick={nextStep}
                  disabled={
                    (currentStep === 3 && !canProceedFromStep3())
                  }
                  className="flex-1 bg-primary hover:bg-primary/90 text-white text-xs font-bold py-2 rounded-xl"
                >
                  Next
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="flex-1 bg-accent hover:bg-accent/90 text-accent-foreground text-xs font-bold py-2 rounded-xl"
                >
                  {submitting ? 'Submitting...' : 'Looks right — finish'}
                </Button>
              )}
            </div>
          )}

        </Card>
      </div>
    </div>
  )

  function nextStep() {
    setCurrentStep(prev => Math.min(5, prev + 1))
  }

  function goStep(idx) {
    setCurrentStep(idx)
  }

  function prevStep() {
    setCurrentStep(prev => Math.max(0, prev - 1))
  }
}
