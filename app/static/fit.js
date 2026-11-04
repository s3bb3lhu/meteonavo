// Keep the complete broadcast frame visible, independently of weather/RSS loading.
(() => {
  const screen = document.querySelector('.tv');
  function fit() {
    const viewport = window.visualViewport;
    const width = viewport ? viewport.width : document.documentElement.clientWidth;
    const height = viewport ? viewport.height : document.documentElement.clientHeight;
    const controls=document.getElementById('preview-controls');
    const reserved=controls&&!controls.hidden?controls.getBoundingClientRect().height:0;
    const availableHeight=Math.max(1,height-reserved);
    const scale = Math.min(width / 1280, availableHeight / 720);
    if (!(scale > 0)) return;
    Object.assign(screen.style, {
      position: 'fixed', width: '1280px', height: '720px',
      left: '0', top: '0', transformOrigin: '0 0',
      transform: `translate(${Math.max(0, (width - 1280 * scale) / 2)}px, ${Math.max(0, (availableHeight - 720 * scale) / 2)}px) scale(${scale})`
    });
  }
  fit();
  window.addEventListener('resize', fit);
  window.addEventListener('load', fit);
  document.addEventListener('fullscreenchange', fit);
  if (window.visualViewport) window.visualViewport.addEventListener('resize', fit);
  if (window.ResizeObserver) new ResizeObserver(fit).observe(document.documentElement);
  const controls=document.getElementById('preview-controls');
  if (window.ResizeObserver&&controls) new ResizeObserver(fit).observe(controls);
})();
