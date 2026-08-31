/**
 * Assessment page module.
 *
 * Data-honesty contract:
 *  - Questions come from the real skill-gap engine (POST /api/engines/skill-gap),
 *    which reads the learner's target occupation's actual O*NET essential
 *    skills. Nothing here is a hand-typed quiz bank.
 *  - Answers are self-rated proficiency (0-100) against each real skill.
 *  - Submitting calls the existing assessment engine endpoint
 *    (POST /api/engines/assessment) for each answered skill, and persists
 *    the raw level via the existing skill endpoint
 *    (POST /api/learner/skills/{element}) so skill-gap/readiness see it
 *    on their next run. No fake scores, no invented results.
 */
const Assessment = (function () {
  let els = {};
  let items = []; // [{element, importance, required_level, why_it_matters}]
  let loaded = false;

  const TIERS = [
    { max: 15, key: 'assessment.tier_none' },
    { max: 40, key: 'assessment.tier_novice' },
    { max: 65, key: 'assessment.tier_familiar' },
    { max: 90, key: 'assessment.tier_proficient' },
    { max: 101, key: 'assessment.tier_expert' },
  ];

  function tierLabel(score) {
    const tier = TIERS.find((t) => score < t.max) || TIERS[TIERS.length - 1];
    return I18N.t(tier.key);
  }

  function init(ids) {
    els = {
      list: document.getElementById(ids.list),
      empty: document.getElementById(ids.empty),
      loading: document.getElementById(ids.loading),
      form: document.getElementById(ids.form),
      submitBtn: document.getElementById(ids.submitBtn),
      error: document.getElementById(ids.error),
      intro: document.getElementById(ids.intro),
    };
  }

  function questionCard(item, idx) {
    const card = document.createElement('div');
    card.className = 'aq-card';
    card.innerHTML = `
      <div class="aq-head">
        <div class="aq-skill">${escapeHtml(item.element)}</div>
        <div class="aq-score" id="aq-score-label-${idx}">${I18N.t('assessment.tier_none')}</div>
      </div>
      <div class="aq-why">${escapeHtml(item.why_it_matters)}</div>
      <input type="range" min="0" max="100" step="1" value="0" class="aq-slider" id="aq-score-${idx}" data-idx="${idx}">
      <div class="aq-scale">
        <span>${I18N.t('assessment.scale_low')}</span>
        <span>${I18N.t('assessment.scale_high')}</span>
      </div>
    `;
    const slider = card.querySelector(`#aq-score-${idx}`);
    const label = card.querySelector(`#aq-score-label-${idx}`);
    slider.addEventListener('input', () => {
      label.textContent = tierLabel(Number(slider.value));
    });
    return card;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  /**
   * Load real assessment items from the skill-gap engine for the learner's
   * target career. Re-fetches every time the page is entered so the list
   * always reflects the learner's current target career / skill state.
   */
  async function load() {
    loaded = false;
    els.error.textContent = '';
    els.error.style.display = 'none';
    els.list.innerHTML = '';
    els.list.style.display = 'none';
    els.empty.style.display = 'none';
    els.form.style.display = 'none';
    els.loading.style.display = 'block';

    try {
      // ROOT CAUSE FIX: 'essential_skills' is O*NET's "Basic Skills" domain
      // (Reading Comprehension, Active Listening, Writing, Speaking,
      // Mathematics, Science, Critical Thinking, Active Learning, Learning
      // Strategies, Monitoring) — this exact 10-item list is IDENTICAL for
      // every one of the 1016 occupations in occupations.json; only the
      // importance/level numbers differ. Pooling it in here is what made
      // the assessment show "Maths / Science / Reading" for every career,
      // since those items are consistently rated important across nearly
      // all occupations and crowd out real career-specific ones.
      // 'knowledge' and 'transferable_skills' are also fixed-name O*NET
      // taxonomies, but their importance scores vary sharply by occupation
      // (e.g. Programming: 1.5 for Chef vs 4.0 for Software Developer;
      // Food Production: 4.12 for Chef vs near-zero for Software Developer),
      // so filtering/sorting on them yields genuinely career-specific
      // results — that's the real differentiator, not the source list length.
      const sources = ['knowledge', 'transferable_skills'];
      const groups = await Promise.all(sources.map((source) => learner.getSkillGap(source)));
      items = groups.flat().sort((a, b) =>
        Number(b.high_priority) - Number(a.high_priority) || b.importance - a.importance || b.gap - a.gap
      ).slice(0, 8);
    } catch (e) {
      console.error('assessment: failed to load skill gap', e);
      items = [];
      els.error.textContent = I18N.t('assessment.load_error');
      els.error.style.display = 'block';
    }

    els.loading.style.display = 'none';

    if (!items.length) {
      els.empty.style.display = 'block';
      loaded = true;
      return;
    }

    items.forEach((item, idx) => els.list.appendChild(questionCard(item, idx)));
    els.list.style.display = 'flex';
    els.form.style.display = 'block';
    loaded = true;
  }

  /**
   * Submit every answered question as a real assessment result, sequentially
   * (each call recalculates the roadmap/adaptation server-side, so we avoid
   * racing concurrent writes to the same learner profile).
   */
  async function submit() {
    if (!loaded || !items.length) return { submitted: 0 };
    els.error.textContent = '';
    els.error.style.display = 'none';
    els.submitBtn.disabled = true;
    const originalLabel = els.submitBtn.textContent;
    els.submitBtn.textContent = I18N.t('assessment.submitting');

    let submitted = 0;
    try {
      for (let idx = 0; idx < items.length; idx++) {
        const item = items[idx];
        const slider = document.getElementById(`aq-score-${idx}`);
        const score = slider ? Number(slider.value) : 0;
        const level07 = Math.round((score / 100) * 7 * 100) / 100; // O*NET 0-7 scale
        const weakConcepts = score < 50 ? [item.element] : [];

        // Persist the raw self-reported level first (so skill-gap sees it),
        // then submit the real assessment result (so the adaptive engine
        // reacts and assessment_status flips to "completed").
        await learner.updateSkillLevel(item.element, level07, 'assessment');
        await learner.submitAssessmentAnswer({
          skill_element: item.element,
          score,
          weak_concepts: weakConcepts,
        });
        submitted++;
      }
      return { submitted };
    } catch (e) {
      console.error('assessment: submit failed', e);
      els.error.textContent = I18N.t('assessment.submit_error');
      els.error.style.display = 'block';
      throw e;
    } finally {
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = originalLabel;
    }
  }

  return { init, load, submit };
})();
