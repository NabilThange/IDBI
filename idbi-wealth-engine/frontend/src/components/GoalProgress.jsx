import { useState, useEffect } from 'react'
import { useSession } from '../context/SessionContext'
import axios from 'axios'
import { ArrowClockwise as RefreshCw, Target, WarningCircle as AlertCircle, CheckCircle as CheckCircle2, TrendUp as TrendingUp, Calendar } from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export default function GoalProgress() {
  const { sessionId } = useSession()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const fetchGoalProgress = async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    setError(null)

    try {
      const response = await axios.get(`/api/goal-progress?session_id=${sessionId}&refresh=${refresh}`)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching goal progress:', err)
      setError('Failed to load goal progress. Please check if the backend is running.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchGoalProgress()
    }, 0)
    return () => clearTimeout(timer)
  }, [sessionId])

  const getStatusConfig = (status) => {
    const configs = {
      completed: {
        label: 'Completed',
        color: 'bg-purple-500 text-white',
        bgColor: 'bg-purple-50 dark:bg-purple-950/10',
        borderColor: 'border-purple-200 dark:border-purple-900/30',
        progressBarColor: 'bg-purple-600',
        icon: CheckCircle2,
      },
      on_track: {
        label: 'On Track',
        color: 'bg-green-500 text-white',
        bgColor: 'bg-green-50 dark:bg-green-950/10',
        borderColor: 'border-green-200 dark:border-green-900/30',
        progressBarColor: 'bg-green-600',
        icon: CheckCircle2,
      },
      ahead_schedule: {
        label: 'Ahead of Schedule',
        color: 'bg-blue-500 text-white',
        bgColor: 'bg-blue-50 dark:bg-blue-950/10',
        borderColor: 'border-blue-200 dark:border-blue-900/30',
        progressBarColor: 'bg-blue-600',
        icon: TrendingUp,
      },
      behind_schedule: {
        label: 'Behind Schedule',
        color: 'bg-amber-500 text-white',
        bgColor: 'bg-amber-50 dark:bg-amber-950/10',
        borderColor: 'border-amber-200 dark:border-amber-900/30',
        progressBarColor: 'bg-amber-500',
        icon: AlertCircle,
      },
      no_contribution: {
        label: 'No Contribution',
        color: 'bg-red-500 text-white',
        bgColor: 'bg-red-50 dark:bg-red-950/10',
        borderColor: 'border-red-200 dark:border-red-900/30',
        progressBarColor: 'bg-red-500',
        icon: AlertCircle,
      }
    }
    return configs[status] || {
      label: status.replace('_', ' '),
      color: 'bg-gray-500 text-white',
      bgColor: 'bg-gray-50',
      borderColor: 'border-gray-200',
      progressBarColor: 'bg-gray-600',
      icon: AlertCircle,
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-IN', { year: 'numeric', month: 'short' })
    } catch {
      return dateStr
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground text-sm">Calculating projections...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/10">
        <CardContent className="pt-6 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
          <p className="text-destructive font-medium">{error}</p>
          <Button onClick={() => fetchGoalProgress()}>Retry</Button>
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header and Summary */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Goal Progress & Projections</h2>
          <p className="text-muted-foreground mt-1">AI-powered tracking for your financial milestones</p>
        </div>
        <div className="flex items-center gap-3">
          {data.cached && (
            <Badge variant="secondary" className="bg-muted text-muted-foreground text-xs">
              Cached Projections
            </Badge>
          )}
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchGoalProgress(true)}
            disabled={refreshing}
            className="hover:rotate-180 transition-transform duration-500"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Goal overall analysis card */}
      <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20 dark:from-primary/10 dark:to-primary/20 dark:border-primary/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            AI Goal Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">{data.summary}</p>
        </CardContent>
      </Card>

      {/* Goal Cards Grid */}
      <div className="grid grid-cols-1 gap-8">
        {data.goals.map((goal) => {
          const config = getStatusConfig(goal.status)
          const StatusIcon = config.icon
          const needsAdjustment = goal.recommended_contribution > goal.monthly_contribution

          return (
            <Card key={goal.goal_id} className={`border border-l-4 border-l-primary hover:shadow-md transition-shadow`}>
              <CardHeader className="pb-4">
                <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                  <div>
                    <CardTitle className="text-2xl font-bold">{goal.name || goal.goal_name}</CardTitle>
                    <CardDescription className="mt-1">
                      Target of ₹{goal.target_amount.toLocaleString('en-IN')} by {formatDate(goal.target_date)}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 self-start md:self-auto">
                    <Badge className={`${config.color} border-0 flex items-center gap-1 py-1 px-2.5 text-xs font-semibold`}>
                      <StatusIcon className="w-3.5 h-3.5" />
                      {config.label}
                    </Badge>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm font-semibold">
                    <span className="text-muted-foreground">Progress</span>
                    <span>{goal.progress_percent}% ({`₹${goal.current_savings.toLocaleString('en-IN')}`} saved)</span>
                  </div>
                  <div className="w-full bg-muted h-3.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-1000 ${config.progressBarColor}`}
                      style={{ width: `${Math.min(100, goal.progress_percent)}%` }}
                    />
                  </div>
                </div>

                {/* Info Fields Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
                  {/* Timeline */}
                  <div className="space-y-1.5 p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border">
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                      <Calendar className="w-4 h-4 text-slate-500" />
                      Milestone Dates
                    </div>
                    <div className="space-y-1 mt-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Target Date:</span>
                        <span className="font-semibold">{formatDate(goal.target_date)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Projected:</span>
                        <span className="font-semibold">{formatDate(goal.projected_completion)}</span>
                      </div>
                      {goal.gap_months > 0 && (
                        <div className="flex justify-between text-red-500 font-medium">
                          <span>Delay Gap:</span>
                          <span>{goal.gap_months} months behind</span>
                        </div>
                      )}
                      {goal.gap_months === 0 && (
                        <div className="flex justify-between text-green-500 font-medium">
                          <span>Timeline:</span>
                          <span>Exactly on time</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Contribution Details */}
                  <div className={`space-y-1.5 p-4 rounded-lg border ${needsAdjustment ? 'bg-amber-50/50 border-amber-100 dark:bg-amber-950/10 dark:border-amber-900/30' : 'bg-slate-50 dark:bg-slate-900'}`}>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                      <TrendingUp className="w-4 h-4 text-slate-500" />
                      Contributions
                    </div>
                    <div className="space-y-1 mt-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Current SIP:</span>
                        <span className="font-semibold">₹{goal.monthly_contribution.toLocaleString('en-IN')}/mo</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Recommended:</span>
                        <span className={`font-semibold ${needsAdjustment ? 'text-amber-600 dark:text-amber-400 font-bold' : ''}`}>
                          ₹{goal.recommended_contribution.toLocaleString('en-IN')}/mo
                        </span>
                      </div>
                      {needsAdjustment && (
                        <div className="text-[11px] text-amber-600 dark:text-amber-500 font-semibold mt-1 bg-amber-100/30 p-1.5 rounded border border-amber-200/50">
                          Increase by ₹{(goal.recommended_contribution - goal.monthly_contribution).toLocaleString('en-IN')}/month to meet target
                        </div>
                      )}
                    </div>
                  </div>

                  {/* AI Action Plan */}
                  <div className="space-y-1.5 p-4 rounded-lg bg-blue-50/40 border border-blue-100 dark:bg-blue-950/10 dark:border-blue-900/30">
                    <div className="text-xs text-blue-800 dark:text-blue-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      AI Action Plan
                    </div>
                    <p className="text-xs text-blue-900 dark:text-blue-300 leading-relaxed mt-2">
                      {goal.recommendation}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
