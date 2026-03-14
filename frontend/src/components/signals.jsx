import { useEffect, useState } from "react";
import { getSignals } from "../api";

function Signals() {

  const [signals, setSignals] = useState([]);

  useEffect(() => {
    getSignals().then(res => {
      setSignals(res.data);
    });
  }, []);

  return (

    <div>

      <h2>Trading Signals</h2>

      <table border="1">

        <thead>
          <tr>
            <th>Date</th>
            <th>Symbol</th>
            <th>Signal</th>
          </tr>
        </thead>

        <tbody>

          {signals.map((s, i) => (

            <tr key={i}>
              <td>{s.date}</td>
              <td>{s.symbol}</td>
              <td>{s.signal}</td>
            </tr>

          ))}

        </tbody>

      </table>

    </div>

  );

}

export default Signals;