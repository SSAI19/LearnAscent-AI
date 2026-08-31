/* Mountain Journey — one climbing path, two flanking tracks.
 *
 * Redesign goals (per brief):
 *  - ONE spine the learner climbs, not two competing colored lines.
 *  - Technical (gold) and professional (teal) items are beads that flank
 *    the spine at their week position, connected to it by a short stem —
 *    two dimensions of the same climb, not two separate paths.
 *  - Exactly one node is ever marked "current" and it is unmistakable
 *    (bigger, pulsing ring, YOU ARE HERE label).
 *  - Status (locked/upcoming/current/completed) is derived ONLY from the
 *    real `completed_milestones` count on the learner's profile — never
 *    invented client-side.
 */
const Mountain = (function () {
  const NS = 'http://www.w3.org/2000/svg';
  let svg, wrap, tooltip;
  let careerLabelEl;

  function el(tag, attrs) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  function init(svgId, wrapId, tooltipId) {
    svg = document.getElementById(svgId);
    wrap = document.getElementById(wrapId);
    tooltip = document.getElementById(tooltipId);
  }

  // Spine: an ascending path left -> right, climbing toward a summit.
  const W = 1200, H = 560;
  function spineD() {
    return `M 60 490
            C 220 470, 300 430, 380 400
            S 520 330, 560 300
            S 700 230, 760 200
            S 900 120, 980 90
            S 1100 40, 1150 30`;
  }

  function terrainSVG() {
    return `
      <defs>
        <linearGradient id="skyfade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0d0c10"/>
          <stop offset="100%" stop-color="#08070a"/>
        </linearGradient>
        <radialGradient id="summitGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="rgba(217,169,78,0.55)"/>
          <stop offset="100%" stop-color="rgba(217,169,78,0)"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="${W}" height="${H}" fill="url(#skyfade)"/>
      <path d="M -20 560 L -20 380 L 140 300 L 300 400 L 480 250 L 640 360
               L 820 180 L 980 300 L 1160 100 L 1220 260 L 1220 560 Z"
            fill="#100e13" opacity="0.9"/>
      <path d="M -20 560 L -20 440 L 200 380 L 420 460 L 620 340 L 860 430
               L 1080 260 L 1220 380 L 1220 560 Z"
            fill="#151319" opacity="0.85"/>
      <circle cx="1150" cy="30" r="70" fill="url(#summitGlow)"/>
    `;
  }

  function laneStatus(index, completed, current) {
    if (index < completed) return 'completed';
    if (index === current) return 'current';
    if (index === current + 1 || index === current + 2) return 'upcoming';
    return 'locked';
  }

  /**
   * Real per-node completion (node.completed, from the backend's
   * TaskCompletion-backed roadmap) takes priority over the old
   * contiguous-frontier-index approach. Completion doesn't have to be
   * sequential — a learner can complete task #5 before #2 — so "current"
   * is the first NOT-completed node in week order, and status is derived
   * per-node from its own real completed flag, not just an index cutoff.
   * Falls back to the legacy frontier-count behavior (meta.completedMilestones)
   * when nodes carry no real completed flag at all (e.g. Demo Mode).
   */
  function computeStatuses(merged, completedFallbackCount) {
    const hasReal = merged.some((n) => typeof n.completed === 'boolean');
    if (hasReal) {
      let currentIdx = merged.findIndex((n) => !n.completed);
      if (currentIdx === -1) currentIdx = Math.max(0, merged.length - 1);
      return merged.map((n, i) => {
        if (n.completed) return 'completed';
        if (i === currentIdx) return 'current';
        if (i === currentIdx + 1 || i === currentIdx + 2) return 'upcoming';
        return 'locked';
      });
    }
    const completed = Math.max(0, completedFallbackCount || 0);
    const current = completed >= merged.length ? Math.max(0, merged.length - 1) : completed;
    return merged.map((_, i) => laneStatus(i, completed, current));
  }

  function statusColor(status) {
    switch (status) {
      case 'completed': return { opacity: 1, ring: false };
      case 'current': return { opacity: 1, ring: true };
      case 'upcoming': return { opacity: 0.55, ring: false };
      default: return { opacity: 0.22, ring: false };
    }
  }

  /**
   * technical / professional: real flattened arrays from the roadmap
   * engine (week, label, type, hours, priority, detail).
   * meta: { completedMilestones, careerTitle, assessed }
   */
  function render(technical, professional, meta) {
    meta = meta || {};
    const completed = Math.max(0, meta.completedMilestones || 0);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = terrainSVG();

    const spinePath = el('path', { d: spineD(), fill: 'none', stroke: 'rgba(217,169,78,0.28)', 'stroke-width': 3 });
    svg.appendChild(spinePath);
    const len = spinePath.getTotalLength();

    // Merge both tracks into one ordered climb (by week; technical first
    // on ties) — this ordering is what "current position" is measured
    // against, since the brief frames this as ONE journey.
    const merged = [
      ...technical.map((t) => ({ ...t, track: 'technical' })),
      ...professional.map((t) => ({ ...t, track: 'professional' })),
    ].sort((a, b) => (a.week - b.week) || (a.track === 'technical' ? -1 : 1));

    const startPt = spinePath.getPointAtLength(0);
    const endPt = spinePath.getPointAtLength(len);

    // START marker
    const startG = el('g', {});
    startG.appendChild(el('circle', { cx: startPt.x, cy: startPt.y, r: 7, fill: '#6b6656' }));
    const startLbl = el('text', { x: startPt.x, y: startPt.y + 26, 'text-anchor': 'middle', class: 'peak-label' });
    startLbl.textContent = 'START';
    svg.appendChild(startG);
    svg.appendChild(startLbl);

    if (!merged.length) {
      svg.appendChild(spinePath);
    }

    const statuses = computeStatuses(merged, completed);

    merged.forEach((node, i) => {
      const t = merged.length <= 1 ? 1 : (i + 1) / (merged.length + 1);
      const pt = spinePath.getPointAtLength(t * len);
      const isTech = node.track === 'technical';
      const side = isTech ? -1 : 1;
      const stemLen = 26;
      const bx = pt.x, by = pt.y + side * stemLen;

      const status = statuses[i];
      const vis = statusColor(status);
      const baseColor = isTech ? 'var(--gold)' : 'var(--teal)';
      const r = status === 'current' ? 11 : (node.priority ? 7 : 5.5);

      const g = el('g', { class: `mnode track-${node.track} status-${status}`, style: 'cursor:pointer' });

      // stem connecting bead to spine
      g.appendChild(el('line', { x1: pt.x, y1: pt.y, x2: bx, y2: by, stroke: baseColor, 'stroke-width': 1.4, opacity: vis.opacity * 0.6 }));

      if (status === 'current') {
        const ring = el('circle', { cx: bx, cy: by, r: r + 8, fill: 'none', stroke: baseColor, 'stroke-width': 1.6, opacity: 0.75, class: 'pulse-ring' });
        g.appendChild(ring);
        const label = el('text', { x: bx, y: by - (side < 0 ? 22 : -30), 'text-anchor': 'middle', class: 'here-label' });
        label.textContent = 'YOU ARE HERE';
        g.appendChild(label);
      }

      const circle = el('circle', { cx: bx, cy: by, r, fill: baseColor, opacity: vis.opacity });
      circle.style.transition = 'r 0.2s ease';
      g.appendChild(circle);

      if (status === 'completed') {
        const check = el('path', {
          d: `M ${bx - r * 0.45} ${by} l ${r * 0.35} ${r * 0.4} l ${r * 0.6} -${r * 0.7}`,
          stroke: '#08070a', 'stroke-width': 1.4, fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        });
        g.appendChild(check);
      }

      g.addEventListener('mouseenter', () => circle.setAttribute('r', r + 2));
      g.addEventListener('mouseleave', () => circle.setAttribute('r', r));
      g.addEventListener('mousemove', (e) => showTooltip(e, node, status));
      g.addEventListener('mouseleave', () => hideTooltip());
      g.addEventListener('focus', (e) => showTooltip(e, node, status));

      svg.appendChild(g);
    });

    // SUMMIT / career goal marker
    const summitG = el('g', {});
    summitG.appendChild(el('path', {
      d: `M ${endPt.x - 22} ${endPt.y + 26} L ${endPt.x} ${endPt.y - 18} L ${endPt.x + 22} ${endPt.y + 26} Z`,
      fill: 'none', stroke: 'var(--gold)', 'stroke-width': 1.6, opacity: 0.85,
    }));
    svg.appendChild(summitG);
    const summitLbl = el('text', { x: endPt.x, y: endPt.y - 32, 'text-anchor': 'middle', class: 'peak-label peak-label-gold' });
    summitLbl.textContent = (meta.careerTitle || 'Career goal').toUpperCase();
    svg.appendChild(summitLbl);
  }

  function showTooltip(e, node, status) {
    if (!tooltip) return;
    const statusLabel = I18N.t(`journey.status_${status}`);
    const trackLabel = node.track === 'technical' ? I18N.t('journey.legend_technical') : I18N.t('journey.legend_professional');
    tooltip.innerHTML = `<div class="t-label">Week ${node.week} — ${escapeHtml(node.label)}</div>
      <div class="t-track">${trackLabel}</div>
      <div class="t-detail">${escapeHtml(node.detail || '')}</div>
      <div class="t-status status-${status}">${statusLabel}${node.hours ? ` · ${node.hours}h` : ''}</div>`;
    tooltip.style.opacity = 1;
    const rect = wrap.getBoundingClientRect();
    tooltip.style.left = Math.min(rect.width - 240, Math.max(0, e.clientX - rect.left + 14)) + 'px';
    tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
  }
  function hideTooltip() { if (tooltip) tooltip.style.opacity = 0; }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function flashRecovery() {
    document.querySelectorAll('.mnode.track-technical circle').forEach((c) => {
      c.animate([{ filter: 'brightness(1)' }, { filter: 'brightness(1.8)' }, { filter: 'brightness(1)' }], { duration: 900, easing: 'ease-in-out' });
    });
  }

  return { init, render, flashRecovery };
})();
