export default function How() {
  return (
    <section className="how wrap" id="how">
      <div className="glass">
        <h3>How the numbers work</h3>
        <dl>
          <div><dt>Price</dt><dd>Your average fill for the amount you typed, buying from the live asks cheapest-first. Bigger amounts reach worse prices.</dd></div>
          <div><dt>Fees</dt><dd>Polymarket US and Polymarket: <code>shares × rate × p × (1−p)</code> with each market's own rate. Kalshi: <code>0.07 × C × P × (1−P)</code>, rounded up to the cent.</dd></div>
          <div><dt>You make</dt><dd>$1 per share minus what you paid, if the outcome happens.</dd></div>
          <div><dt>Annualized</dt><dd>Return × 365 ÷ days until it resolves. Simple, not compounded.</dd></div>
          <div><dt>vs T-bill</dt><dd>Your profit minus what the same money earns in the Treasury bill closest in maturity, over the same days. Yields come from FRED.</dd></div>
        </dl>
      </div>
      <div className="glass">
        <h3>Why it isn't really a bond</h3>
        <dl>
          <div><dt>The downside is lopsided</dt><dd>Win about 3%, lose about 100%. At 96¢ one miss erases roughly 25 wins.</dd></div>
          <div><dt>The edge is the whole bet</dt><dd>You only come out ahead if outcomes priced at 96% happen more than 96% of the time.</dd></div>
          <div><dt>Short markets inflate annualized numbers</dt><dd>They assume you can roll the full amount into an equally good bet every few days.</dd></div>
          <div><dt>Ending isn't paying</dt><dd>Resolutions can be disputed or settle late, and your money is locked until they do.</dd></div>
          <div><dt>Prices move</dt><dd>Data refreshes about every 30 minutes. Check the price on the venue before you trade. Not financial advice.</dd></div>
        </dl>
      </div>
    </section>
  );
}
