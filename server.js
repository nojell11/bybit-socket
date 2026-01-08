// Test latency to Polymarket
const testLatency = async () => {
  const start = Date.now();
  await fetch('https://clob.polymarket.com/markets');
  const latency = Date.now() - start;
  console.log(`🚀 Latency to Polymarket: ${latency}ms`);
  return latency;
};

// Run on startup
testLatency();
