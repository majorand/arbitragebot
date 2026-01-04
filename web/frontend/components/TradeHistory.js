import { CheckCircle, AlertCircle, Clock, XCircle } from 'lucide-react';

export default function TradeHistory({ trades = [] }) {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'filled':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-400" />;
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="card-dark p-6">
      <h2 className="text-xl font-bold text-white mb-4">Trade History</h2>

      {trades.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400">No trades yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {trades.map((trade, idx) => (
            <div key={idx} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors">
              <div className="flex items-start gap-4">
                <div className="pt-1">
                  {getStatusIcon(trade.status)}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-white">{trade.event || 'Market'}</h4>
                      <p className="text-sm text-gray-400">{trade.market || 'Market Type'}</p>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold text-lg ${(trade.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {(trade.pnl || 0) >= 0 ? '+' : ''}{(trade.pnl || 0).toFixed(2)}%
                      </p>
                      <p className="text-xs text-gray-400">{trade.timestamp}</p>
                    </div>
                  </div>
                  <div className="flex gap-6 mt-3">
                    <div>
                      <p className="text-xs text-gray-400">Venue</p>
                      <p className="text-sm text-gray-300">{trade.venue || 'Kalshi'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Stake</p>
                      <p className="text-sm text-gray-300">${(trade.stake || 0).toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Edge</p>
                      <p className="text-sm text-blue-400 font-semibold">{(trade.edge || 0).toFixed(2)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Status</p>
                      <p className="text-sm capitalize font-semibold">
                        <span className={`${
                          trade.status === 'filled' ? 'text-green-400' :
                          trade.status === 'pending' ? 'text-yellow-400' :
                          'text-red-400'
                        }`}>
                          {trade.status}
                        </span>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
