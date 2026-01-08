const testLatency = async () => {
  console.log("\n🔍 LATENCY DIAGNOSTICS:\n");
  
  // Test 1: CLOB API
  const start1 = Date.now();
  try {
    await fetch('https://clob.polymarket.com/markets?limit=1');
    console.log(`Test 1 - CLOB Markets: ${Date.now() - start1}ms`);
  } catch(e) {
    console.log(`Test 1 - FAILED: ${e.message}`);
  }
  
  // Test 2: Orderbook endpoint
  const start2 = Date.now();
  try {
    await fetch('https://clob.polymarket.com/book');
    console.log(`Test 2 - Orderbook: ${Date.now() - start2}ms`);
  } catch(e) {
    console.log(`Test 2 - FAILED: ${e.message}`);
  }
  
  // Test 3: Simple ping
  const start3 = Date.now();
  try {
    await fetch('https://clob.polymarket.com/ping');
    console.log(`Test 3 - Ping: ${Date.now() - start3}ms`);
  } catch(e) {
    console.log(`Test 3 - FAILED: ${e.message}`);
  }
  
  // Test 4: Direct to London (reference)
  const start4 = Date.now();
  try {
    await fetch('https://api.github.com'); // GitHub has London servers
    console.log(`Test 4 - GitHub (Reference): ${Date.now() - start4}ms`);
  } catch(e) {
    console.log(`Test 4 - FAILED: ${e.message}`);
  }
};

testLatency();
