import { useEffect, useState } from "react";
import {
  API_BASE_URL,
  fetchMode,
  fetchMetrics,
  fetchOdds,
  fetchPositions,
  fetchTrades,
  submitTrade,
  updateMode
} from "../lib/api";

const refreshIntervalMs = 10000;

export default function Home() {
  const [mode, setMode] = useState("paper");
  const [odds, setOdds] = useState([]);
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState({});
  const [metrics, setMetrics] = useState({
    total_trades: 0,
    cash_balance: 0,
    open_positions: 0
  });
  const [eventId, setEventId] = useState("");
  const [stake, setStake] = useState(10);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const loadAll = async () => {
    try {
      setLoading(true);
      const [modeData, oddsData, tradesData, positionsData, metricsData] =
        await Promise.all([
          fetchMode(),
          fetchOdds(),
          fetchTrades(),
          fetchPositions(),
          fetchMetrics()
        ]);
      setMode(modeData.mode);
      setOdds(oddsData);
      setTrades(tradesData);
      setPositions(positionsData);
      setMetrics(metricsData);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    const handle = setInterval(loadAll, refreshIntervalMs);
    return () => clearInterval(handle);
  }, []);

  const handleToggle = async () => {
    const nextMode = mode === "paper" ? "live" : "paper";
    try {
      const response = await updateMode(nextMode);
      setMode(response.mode);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTrade = async (event) => {
    event.preventDefault();
    try {
      await submitTrade(eventId, Number(stake));
      await loadAll();
      setEventId("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>ArbitrageBot Dashboard</h1>
          <p>Backend: {API_BASE_URL}</p>
        </div>
        <button
          className={mode === "paper" ? "mode mode-paper" : "mode mode-live"}
          onClick={handleToggle}
        >
          Mode: {mode}
        </button>
      </header>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Refreshing data...</div>}

      <section className="grid">
        <div className="card">
          <h2>Performance</h2>
          <ul>
            <li>Total trades: {metrics.total_trades}</li>
            <li>Cash balance: {metrics.cash_balance.toFixed(2)}</li>
            <li>Open positions: {metrics.open_positions}</li>
          </ul>
        </div>
        <div className="card">
          <h2>Manual Trade</h2>
          <form onSubmit={handleTrade}>
            <label>
              Event ID
              <input
                value={eventId}
                onChange={(event) => setEventId(event.target.value)}
                required
              />
            </label>
            <label>
              Stake
              <input
                type="number"
                min="1"
                step="1"
                value={stake}
                onChange={(event) => setStake(event.target.value)}
                required
              />
            </label>
            <button type="submit">Submit Trade</button>
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Real-Time Odds</h2>
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Teams</th>
              <th>Market</th>
              <th>Selection</th>
              <th>Price</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {odds.map((row) => (
              <tr key={`${row.event_id}-${row.source}-${row.selection}`}>
                <td>{row.event_id}</td>
                <td>
                  {row.home_team} vs {row.away_team}
                </td>
                <td>{row.market_type}</td>
                <td>{row.selection || "-"}</td>
                <td>{row.price}</td>
                <td>{row.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid">
        <div className="card">
          <h2>Open Positions</h2>
          <ul>
            {Object.entries(positions).map(([marketId, size]) => (
              <li key={marketId}>
                {marketId}: {size}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>Trade History</h2>
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Mode</th>
                <th>Price</th>
                <th>Stake</th>
                <th>Status</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.trade_id}>
                  <td>{trade.event_id}</td>
                  <td>{trade.mode}</td>
                  <td>{trade.price}</td>
                  <td>{trade.stake}</td>
                  <td>{trade.status}</td>
                  <td>{new Date(trade.timestamp).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
