/* Runs the season simulator off the main thread, so the page stays responsive while 10,000 seasons play. */
importScripts("sim.js?v=1");

self.onmessage = (event) => {
  const { id, job } = event.data;
  try {
    const result = self.SeasonSim.run(job);
    self.postMessage({ id, summary: self.SeasonSim.summarise(result), n: result.n });
  } catch (error) {
    self.postMessage({ id, error: String(error) });
  }
};
