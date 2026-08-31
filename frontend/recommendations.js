/**
 * Recommendations API Service
 * Fetches Smart Resource Recommendations for the authenticated learner.
 * Same fetch/auth pattern as learner.js — no demo/fake data, ever.
 */
class RecommendationsService {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8000/api';
  }

  async getRecommendations() {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    try {
      const response = await fetch(`${this.apiBase}/recommendations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        const err = new Error('Failed to fetch recommendations');
        err.status = response.status;
        throw err;
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  }
}

// Export as global
const recommendationsService = new RecommendationsService();

/**
 * RecommendationsUI — renders the recommendations view into the DOM.
 * Same module shape as Mountain/DNA (init once, render on demand).
 * Shows a loading state, then either real cards or an empty state —
 * never demo/placeholder content.
 */
const RecommendationsUI = (function () {
  const TYPE_LABEL = {
    course: 'Course', video: 'Video', project: 'Project', free_resource: 'Free Resource',
  };

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function cardHTML(item) {
    const linkHTML = item.url
      ? `<a class="reco-link" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">Open resource →</a>`
      : `<span class="reco-link disabled">No link available</span>`;
    return `
      <div class="reco-card">
        <div class="reco-top">
          <span class="reco-type">${esc(TYPE_LABEL[item.resource_type] || item.resource_type)}</span>
          <span class="reco-difficulty">${esc(item.difficulty)}</span>
        </div>
        <h4>${esc(item.title)}</h4>
        <div class="reco-meta">
          <span>🎯 ${esc(item.related_skill)}</span>
          <span>⏱ ${esc(item.estimated_time_hours)}h</span>
          <span>${esc(item.source)}</span>
        </div>
        <div class="reco-why">${esc(item.why_recommended)}</div>
        ${linkHTML}
      </div>`;
  }

  function fillGrid(elId, items) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = `<div class="reco-empty">Nothing here yet.</div>`;
      return;
    }
    el.innerHTML = items.map(cardHTML).join('');
  }

  let loaded = false;

  async function load(careerTitle) {
    const loadingEl = document.getElementById('reco-loading');
    const emptyEl = document.getElementById('reco-empty');
    const contentEl = document.getElementById('reco-content');
    const titleEl = document.getElementById('reco-title');

    loadingEl.style.display = 'block';
    emptyEl.style.display = 'none';
    contentEl.style.display = 'none';

    try {
      const data = await recommendationsService.getRecommendations();
      loadingEl.style.display = 'none';

      if (!data || (!data.recommended_for_you || !data.recommended_for_you.length)
          && (!data.courses || !data.courses.length)
          && (!data.videos || !data.videos.length)
          && (!data.projects || !data.projects.length)
          && (!data.free_resources || !data.free_resources.length)) {
        emptyEl.style.display = 'block';
        return;
      }

      titleEl.textContent = `Resources picked for ${data.target_career_title || careerTitle || 'your path'}`;

      fillGrid('reco-grid-featured', data.recommended_for_you);
      fillGrid('reco-grid-courses', data.courses);
      fillGrid('reco-grid-videos', data.videos);
      fillGrid('reco-grid-projects', data.projects);
      fillGrid('reco-grid-free', data.free_resources);

      contentEl.style.display = 'block';
      loaded = true;
    } catch (error) {
      loadingEl.style.display = 'none';
      emptyEl.textContent = (error && error.status === 400)
        ? 'Set a target career to unlock personalized resource recommendations.'
        : (error && error.status === 404)
          ? 'Complete your learner profile to unlock personalized resource recommendations.'
          : 'Could not load recommendations right now. Please try again shortly.';
      emptyEl.style.display = 'block';
    }
  }

  // Lazy-load: fetch the first time this view is entered, then cache
  // for the rest of the session (matches other views' one-shot boot).
  function ensureLoaded(careerTitle) {
    if (loaded) return;
    load(careerTitle);
  }

  function reset() {
    loaded = false;
  }

  return { ensureLoaded, reset };
})();
