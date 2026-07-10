import { useState } from 'react'
import { format } from 'date-fns'
import { ArrowUpRight, ArrowDownLeft } from '@phosphor-icons/react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export default function Transactions({ transactions, fullView = false }) {
  const [filter, setFilter] = useState('all')
  const displayCount = fullView ? transactions.length : 10

  const filteredTransactions = transactions
    .filter(t => filter === 'all' || t.type === filter)
    .slice(0, displayCount)

  const getCategoryColor = (category) => {
    const colors = {
      income: 'bg-green-100 text-green-800',
      rent: 'bg-red-100 text-red-800',
      food: 'bg-amber-100 text-amber-800',
      transportation: 'bg-cyan-100 text-cyan-800',
      entertainment: 'bg-purple-100 text-purple-800',
      shopping: 'bg-pink-100 text-pink-800',
      utilities: 'bg-gray-100 text-gray-800',
      investment: 'bg-blue-100 text-blue-800'
    }
    return colors[category] || 'bg-gray-100 text-gray-800'
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Recent Transactions</CardTitle>
          <div className="flex gap-2">
            <Button
              variant={filter === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              All
            </Button>
            <Button
              variant={filter === 'credit' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('credit')}
            >
              Income
            </Button>
            <Button
              variant={filter === 'debit' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('debit')}
            >
              <span className="text-black">Expenses</span>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {filteredTransactions.map((transaction, index) => (
            <div
              key={index}
              className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted transition-colors"
            >
              <div className={`p-2 rounded-full ${transaction.type === 'credit' ? 'bg-green-100' : 'bg-red-100'}`}>
                {transaction.type === 'credit' ? (
                  <ArrowDownLeft className="w-5 h-5 text-green-600" />
                ) : (
                  <ArrowUpRight className="w-5 h-5 text-red-600" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{transaction.description}</p>
                <p className="text-sm text-muted-foreground">
                  {format(new Date(transaction.date), 'MMM dd, yyyy')}
                </p>
              </div>

              <div className="text-right space-y-1">
                <p className={`font-bold ${transaction.type === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                  {transaction.type === 'credit' ? '+' : ''}₹{Math.abs(transaction.amount).toLocaleString('en-IN')}
                </p>
                <Badge variant="secondary" className={`text-xs ${getCategoryColor(transaction.category)}`}>
                  {transaction.category}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
