/**
 * Chart.js UMD loader script.
 * Dynamically loads Chart.js 4.4.1 UMD if not already present on page.
 */
if (typeof window.Chart === 'undefined') {
  var script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
  script.async = false;
  document.head.appendChild(script);
}
