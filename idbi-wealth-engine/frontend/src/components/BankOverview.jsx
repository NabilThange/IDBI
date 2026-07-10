import { Wallet, TrendUp as TrendingUp, TrendDown as TrendingDown, PiggyBank, Shield, Bank as Landmark } from '@phosphor-icons/react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
 
export default function BankOverview({ profile }) {
  const { financial_summary } = profile
  const savingsRate = ((financial_summary.monthly_savings / financial_summary.monthly_income) * 100).toFixed(1)
 
  const stats = [
    {
      icon: Wallet,
      label: 'Current Balance',
      value: `₹${financial_summary.current_balance.toLocaleString('en-IN')}`,
      color: 'text-primary',
      bgColor: 'bg-primary/10'
    },
    {
      icon: TrendingUp,
      label: 'Monthly Income',
      value: `₹${financial_summary.monthly_income.toLocaleString('en-IN')}`,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      icon: TrendingDown,
      label: 'Monthly Expenses',
      value: `₹${financial_summary.monthly_expenses.toLocaleString('en-IN')}`,
      color: 'text-red-600',
      bgColor: 'bg-red-50'
    },
    {
      icon: PiggyBank,
      label: 'Monthly Savings',
      value: `₹${financial_summary.monthly_savings.toLocaleString('en-IN')}`,
      subtitle: `${savingsRate}% savings rate`,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50'
    },
    {
      icon: Shield,
      label: 'Emergency Fund',
      value: `₹${financial_summary.emergency_fund.toLocaleString('en-IN')}`,
      color: 'text-primary',
      bgColor: 'bg-primary/10'
    },
    {
      icon: Landmark,
      label: 'Total Investments',
      value: `₹${financial_summary.total_investments.toLocaleString('en-IN')}`,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-50'
    }
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Financial Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.label}
                </CardTitle>
                <div className={`${stat.bgColor} p-2 rounded-lg`}>
                  <Icon className={`w-5 h-5 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                {stat.subtitle && (
                  <p className="text-xs text-green-600 font-medium mt-1">{stat.subtitle}</p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
