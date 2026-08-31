/* LearnAscent AI — app bootstrap.
 *
 * Data-honesty contract for this file:
 *  - Anything rendered inside #view-dashboard, #view-dna, #view-journey
 *    comes from an authenticated API call (learner.*). If that call
 *    fails or returns nothing, the UI shows an empty/dormant state —
 *    it NEVER falls back to DEMO_DATA.
 *  - DEMO_DATA is used in exactly one place: the "DEMO MODE" section on
 *    the public, unauthenticated Home page. It is hidden the moment a
 *    real learner is signed in.
 */
(function main(){
  I18N.apply();

  /* ---------------- Language switcher ---------------- */
  const langSwitch = document.getElementById('lang-switch');
  const langBtn = document.getElementById('lang-btn');
  const langBtnLabel = document.getElementById('lang-btn-label');
  langBtnLabel.textContent = I18N.get().toUpperCase();
  langBtn.addEventListener('click', (e)=>{
    e.stopPropagation();
    langSwitch.classList.toggle('open');
    langBtn.setAttribute('aria-expanded', langSwitch.classList.contains('open'));
  });
  document.addEventListener('click', ()=> langSwitch.classList.remove('open'));
  document.querySelectorAll('.lang-option').forEach((btn)=>{
    btn.addEventListener('click', (e)=>{
      e.stopPropagation();
      I18N.set(btn.dataset.lang);
      langBtnLabel.textContent = btn.dataset.lang.toUpperCase();
      langSwitch.classList.remove('open');
    });
  });

  /* ---------------- Router setup ---------------- */
  ['home','dashboard','assessment','dna','journey','recommendations'].forEach((name)=>{
    Router.register(name, document.getElementById('view-' + name));
  });

  let hasProfile = false; // set once we know whether the signed-in user has a learner profile
  let assessed = false;   // real assessment_status signal — never inferred from UI state
  let currentCareerTitle = '';

  Router.addGuard((route)=>{
    const authed = auth.isAuthenticated();
    if (['dashboard','assessment','dna','journey','recommendations'].includes(route) && (!authed || !hasProfile)) {
      return 'home';
    }
    if (route === 'home' && authed && hasProfile) {
      return assessed ? 'dashboard' : 'assessment';
    }
    return null;
  });

  document.getElementById('brand-home-link').addEventListener('click', ()=> Router.go('home'));

  Assessment.init({
    list: 'assessment-list',
    empty: 'assessment-empty',
    loading: 'assessment-loading',
    form: 'assessment-form',
    submitBtn: 'assessment-submit-btn',
    error: 'assessment-error',
  });

  Tasks.init({
    container: 'journey-tasks',
    todayList: 'tasks-today-list',
    todayCount: 'tasks-today-count',
    todayEmpty: 'tasks-today-empty',
    weekList: 'tasks-week-list',
    weekCount: 'tasks-week-count',
  });
  // A task completion is real learner progress — refresh readiness/
  // Mountain/DNA from the backend's fresh numbers, without navigating
  // the learner away from the Journey page they're actively using.
  Tasks.setProgressListener(()=> refreshProgressUI());

  document.getElementById('assessment-banner-btn').addEventListener('click', ()=> Router.go('assessment'));

  document.getElementById('assessment-submit-btn').addEventListener('click', async ()=>{
    try {
      await Assessment.submit();
    } catch(e){
      return; // Assessment module already surfaced the error inline
    }
    // Real recalculation: re-run the authenticated boot so readiness,
    // roadmap, DNA and Mountain all reflect the engine's fresh output —
    // nothing here is hand-computed. bootAuthenticated() itself routes
    // to the dashboard once assessment_status comes back "completed".
    await bootAuthenticated();
  });

  window.addEventListener('routechange', (e)=>{
    if(e.detail.route === 'assessment'){
      Assessment.load();
    }
    if(e.detail.route === 'dna'){
      requestAnimationFrame(()=> DNA.resize());
    }
    if(e.detail.route === 'journey'){
      Tasks.load();
    }
    if(e.detail.route === 'recommendations'){
      RecommendationsUI.ensureLoaded(currentCareerTitle);
    }
  });

  /* ---------------- Auth wiring (unchanged behavior) ---------------- */
  const authOverlay = document.getElementById('auth-overlay');
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const showSignupBtn = document.getElementById('show-signup');
  const showLoginBtn = document.getElementById('show-login');
  const navUser = document.getElementById('nav-user');
  const navEmail = document.getElementById('nav-email');
  const navLogoutBtn = document.getElementById('nav-logout-btn');
  const navSigninBtn = document.getElementById('nav-signin-btn');

  const onboardingOverlay = document.getElementById('onboarding-overlay');
  const onboardingForm = document.getElementById('onboarding-form');
  const onboardingCareerInput = document.getElementById('onboarding-career');
  const onboardingCareerResults = document.getElementById('onboarding-career-results');

  let selectedCareer = null;

  showSignupBtn.addEventListener('click', (e)=>{
    e.preventDefault();
    loginForm.style.display = 'none';
    signupForm.style.display = 'flex';
    clearFormErrors();
  });
  showLoginBtn.addEventListener('click', (e)=>{
    e.preventDefault();
    signupForm.style.display = 'none';
    loginForm.style.display = 'flex';
    clearFormErrors();
  });

  function clearFormErrors(){
    document.querySelectorAll('.error-message').forEach(el => el.classList.remove('show'));
    document.querySelectorAll('input').forEach(el => el.classList.remove('error'));
  }
  function showFormError(fieldId, message){
    const input = document.getElementById(fieldId);
    const errorEl = document.getElementById(`${fieldId}-error`);
    input.classList.add('error');
    errorEl.textContent = message;
    errorEl.classList.add('show');
  }

  function openAuth(){
    authOverlay.classList.remove('hidden');
  }
  document.getElementById('hero-cta-primary').addEventListener('click', openAuth);
  document.getElementById('hero-cta-secondary').addEventListener('click', openAuth);
  navSigninBtn.addEventListener('click', openAuth);

  signupForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    clearFormErrors();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const confirm = document.getElementById('signup-confirm').value;
    if(!email){ showFormError('signup-email', 'Email is required'); return; }
    if(password.length < 6){ showFormError('signup-password', 'Password must be at least 6 characters'); return; }
    if(password !== confirm){ showFormError('signup-confirm', 'Passwords do not match'); return; }

    const btn = document.getElementById('signup-submit');
    btn.disabled = true; btn.textContent = 'Creating account...';
    try {
      await auth.signup(email, password);
      authOverlay.classList.add('hidden');
      await bootAuthenticated();
    } catch(error){
      if(error.message.includes('already')) showFormError('signup-email', 'Email already in use');
      else showFormError('signup-email', error.message);
      btn.disabled = false; btn.textContent = 'Create Account';
    }
  });

  loginForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    clearFormErrors();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    if(!email){ showFormError('login-email', 'Email is required'); return; }
    if(!password){ showFormError('login-password', 'Password is required'); return; }

    const btn = document.getElementById('login-submit');
    btn.disabled = true; btn.textContent = 'Signing in...';
    try {
      await auth.login(email, password);
      authOverlay.classList.add('hidden');
      await bootAuthenticated();
    } catch(error){
      showFormError('login-email', error.message);
      btn.disabled = false; btn.textContent = 'Sign In';
    }
  });

  let careerSearchTimer = null;
  onboardingCareerInput.addEventListener('input', ()=>{
    selectedCareer = null;
    const query = onboardingCareerInput.value.trim();
    clearTimeout(careerSearchTimer);
    if(query.length < 2){
      onboardingCareerResults.classList.remove('show');
      onboardingCareerResults.innerHTML = '';
      return;
    }
    careerSearchTimer = setTimeout(async ()=>{
      const matches = await learner.searchOccupations(query);
      onboardingCareerResults.innerHTML = '';
      if(!matches.length){ onboardingCareerResults.classList.remove('show'); return; }
      matches.forEach((m)=>{
        const opt = document.createElement('div');
        opt.className = 'career-option';
        opt.textContent = m.title;
        opt.addEventListener('click', ()=>{
          selectedCareer = { code: m.code, title: m.title };
          onboardingCareerInput.value = m.title;
          onboardingCareerResults.classList.remove('show');
        });
        onboardingCareerResults.appendChild(opt);
      });
      onboardingCareerResults.classList.add('show');
    }, 250);
  });

  onboardingForm.addEventListener('submit', async (e)=>{
    e.preventDefault();
    document.querySelectorAll('#onboarding-form .error-message').forEach(el => el.classList.remove('show'));

    const name = document.getElementById('onboarding-name').value.trim();
    const experienceText = document.getElementById('onboarding-experience').value.trim();
    const minutes = parseInt(document.getElementById('onboarding-minutes').value, 10) || 30;
    const weeks = parseInt(document.getElementById('onboarding-weeks').value, 10) || 12;
    const toolsRaw = document.getElementById('onboarding-tools').value.trim();
    const tools = toolsRaw ? toolsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];

    if(!selectedCareer){
      const errorEl = document.getElementById('onboarding-career-error');
      document.getElementById('onboarding-career').classList.add('error');
      errorEl.textContent = 'Pick a career from the search results';
      errorEl.classList.add('show');
      return;
    }

    const btn = document.getElementById('onboarding-submit');
    btn.disabled = true; btn.textContent = 'Building your roadmap...';
    try {
      await learner.createProfile({
        name, experience_level: 'beginner', experience_text: experienceText || null,
        target_career_code: selectedCareer.code, target_career_title: selectedCareer.title,
        available_minutes_per_day: minutes, target_duration_weeks: weeks, known_tools: tools,
        preferred_language: I18N.get(),
      });
      onboardingOverlay.classList.add('hidden');
      await bootAuthenticated();
    } catch(error){
      const errorEl = document.getElementById('onboarding-career-error');
      errorEl.textContent = error.message;
      errorEl.classList.add('show');
      btn.disabled = false; btn.textContent = 'Build my roadmap';
    }
  });

  navLogoutBtn.addEventListener('click', async (e)=>{
    e.preventDefault();
    await auth.logout();
    MentorChat.reset();
    location.hash = '#/home';
    location.reload();
  });

  /* ---------------- Data flattening helper (shared by real + demo) ---------------- */
  function flattenTrack(trackPlan){
    const out = [];
    if(!trackPlan || !trackPlan.milestones) return out;
    trackPlan.milestones.forEach((milestone)=>{
      milestone.topics.forEach((topic)=>{
        out.push({
          week: milestone.week_number,
          campsite: milestone.is_campsite || false,
          label: topic.label,
          type: topic.topic_type,
          hours: topic.estimated_hours,
          priority: topic.high_priority,
          detail: topic.detail || '',
          completed: typeof topic.completed === 'boolean' ? topic.completed : undefined,
        });
      });
    });
    return out;
  }

  /* ---------------- Authenticated boot: real data only ---------------- */
  async function bootAuthenticated(){
    navSigninBtn.style.display = 'none';
    document.getElementById('demo-section').style.display = 'none';

    let profile;
    try {
      profile = await learner.getLearnerProfile();
    } catch(error){
      if(error && error.status === 404){
        hasProfile = false;
        navUser.style.display = 'none';
        authOverlay.classList.add('hidden');
        onboardingOverlay.classList.remove('hidden');
        return;
      }
      console.error('Error loading learner profile:', error);
      hasProfile = false;
      Router.go('home');
      return;
    }

    hasProfile = !!(profile && profile.target_career_title);
    if(!hasProfile){
      authOverlay.classList.add('hidden');
      onboardingOverlay.classList.remove('hidden');
      return;
    }

    currentCareerTitle = profile.target_career_title || '';
    RecommendationsUI.reset();

    onboardingOverlay.classList.add('hidden');
    navEmail.textContent = auth.getUser();
    navUser.style.display = 'flex';

    // Real assessment signal — never inferred from UI state.
    assessed = !!(profile.assessment_status && profile.assessment_status !== 'not_started');

    const banner = document.getElementById('assessment-banner');
    banner.style.display = assessed ? 'none' : 'flex';

    await renderProgressUI(profile);

    if(assessed){
      Tasks.load();
    }

    Router.go(assessed ? 'dashboard' : 'assessment');
  }

  /**
   * Fetches real readiness/roadmap for the current learner and renders
   * the dashboard stats, Learner DNA and Mountain Journey from it. Shared
   * by bootAuthenticated() (full page load) and refreshProgressUI() (after
   * a task completion changes real progress, without navigating away).
   */
  async function renderProgressUI(profile){
    let readiness = 0;
    let technical = [], professional = [], weeksPlanned = 0;

    // Requirement: readiness, roadmap and topic counts stay at their
    // not-available/zero defaults until a real assessment exists — we
    // don't even call the engines pre-assessment, so nothing here can
    // be mistaken for a computed-but-hidden value.
    if(assessed){
      try {
        const readinessResp = await learner.getReadiness();
        readiness = readinessResp.readiness_score || 0;
      } catch(e){ console.error('readiness fetch failed', e); }

      try {
        const roadmap = await learner.getRoadmap();
        technical = flattenTrack(roadmap.technical);
        professional = flattenTrack(roadmap.professional);
        weeksPlanned = roadmap.weeks_planned || 0;
      } catch(e){ console.error('roadmap fetch failed', e); }
    }

    // Dashboard
    document.getElementById('stat-readiness').textContent = assessed ? Math.round(readiness) : '—';
    document.getElementById('stat-weeks').textContent = assessed ? (weeksPlanned || '—') : '—';
    document.getElementById('stat-topics').textContent = assessed ? (technical.length + professional.length) : 0;
    const firstTopic = technical[0] || professional[0];
    const missionEl = document.getElementById('mission-text');
    if(!assessed){
      missionEl.textContent = I18N.t('dash.mission_empty');
    } else if(firstTopic){
      missionEl.textContent = `${firstTopic.label} — ${firstTopic.hours}h focus`;
    } else {
      missionEl.textContent = I18N.t('dash.mission_empty');
    }

    // DNA page
    DNA.init('dna-stage', 'dna-canvas');
    DNA.setProgress(readiness, assessed);
    const readoutVal = document.getElementById('dna-readout-val');
    const readoutLbl = document.getElementById('dna-readout-lbl');
    if(assessed){
      readoutVal.textContent = Math.round(readiness);
      readoutVal.classList.remove('dormant');
      readoutLbl.textContent = I18N.t('dna.readiness_label');
    } else {
      readoutVal.textContent = I18N.t('dna.assessment_required');
      readoutVal.classList.add('dormant');
      readoutLbl.textContent = '';
    }

    // Mountain Journey page — stays "not started" until a real assessment
    // exists, even if a default roadmap could technically be generated.
    Mountain.init('mountain-svg', 'mountain-svg-wrap', 'tooltip');
    const journeyEmpty = document.getElementById('journey-empty');
    if(!assessed || (!technical.length && !professional.length)){
      journeyEmpty.textContent = assessed ? I18N.t('journey.empty') : I18N.t('journey.not_started');
      journeyEmpty.style.display = 'block';
      document.getElementById('mountain-svg').style.display = 'none';
    } else {
      journeyEmpty.style.display = 'none';
      document.getElementById('mountain-svg').style.display = 'block';
      Mountain.render(technical, professional, {
        completedMilestones: profile.completed_milestones || 0,
        careerTitle: profile.target_career_title,
        assessed,
      });
    }
  }

  /**
   * Called after a real task completion/uncompletion (Tasks module). Pulls
   * the freshly-persisted profile (updated completed_milestones) and
   * re-renders dashboard/DNA/Mountain from it — no navigation, so the
   * learner stays on the Journey page they're actively working from.
   */
  async function refreshProgressUI(){
    if(!hasProfile) return;
    try {
      const profile = await learner.getLearnerProfile();
      assessed = !!(profile.assessment_status && profile.assessment_status !== 'not_started');
      await renderProgressUI(profile);
    } catch(e){
      console.error('refreshProgressUI failed', e);
    }
  }

  /* ---------------- Demo Mode (unauthenticated Home only) ---------------- */
  function bootDemo(){
    navSigninBtn.style.display = 'inline-block';
    navUser.style.display = 'none';
    document.getElementById('demo-section').style.display = 'block';

    const d = DEMO_DATA;
    // Bind directly to the real engine-generated adaptation event —
    // nothing here is a hand-typed placeholder.
    document.getElementById('demo-skill-name').textContent = d.adaptation.skill_element;
    document.getElementById('demo-skill-score').innerHTML = `${Math.round(d.adaptation.score)}<span style="font-size:12px;color:var(--text-mute)">/100</span>`;

    Mountain.init('demo-mountain-svg', 'demo-mountain-wrap', 'demo-tooltip');
    Mountain.render(d.technicalBefore, d.professionalBefore, {
      completedMilestones: 0,
      careerTitle: d.occupation.title,
      assessed: false,
    });

    const btn = document.getElementById('simulate-btn');
    const diff = document.getElementById('route-diff');
    const msgEl = document.getElementById('route-msg');
    const stepsEl = document.getElementById('route-steps');
    let fired = false;

    btn.onclick = ()=>{
      if(fired) return;
      fired = true;
      btn.disabled = true;
      btn.textContent = 'Recovery route inserted';

      msgEl.textContent = d.adaptation.message;
      stepsEl.innerHTML = '';
      d.adaptation.inserted_topics.forEach((t, i)=>{
        const row = document.createElement('div');
        row.className = 'step-row';
        row.style.animationDelay = (i*0.12)+'s';
        row.innerHTML = `<span class="idx">${i+1}</span><span class="lbl">${t.label}</span><span class="hrs">${t.estimated_hours}h</span>`;
        stepsEl.appendChild(row);
      });
      diff.classList.add('show');

      setTimeout(()=>{
        Mountain.render(d.technicalAfter, d.professionalBefore, {
          completedMilestones: 1,
          careerTitle: d.occupation.title,
          assessed: true,
        });
        Mountain.flashRecovery();
      }, 500);
    };
  }

  MentorChat.init({
    messages: 'mentor-messages', suggestions: 'mentor-suggestions', input: 'mentor-input',
    sendBtn: 'mentor-send-btn', signinNote: 'mentor-signin-note',
    inputRow: 'mentor-input-row', closeBtn: 'mentor-close-btn',
  });
  Mentor.setReadyCheck(() => auth.isAuthenticated() && hasProfile);

  /* ---------------- Startup ---------------- */
  Mentor.init('mentor', 'mentor-panel');

  if(auth.isAuthenticated()){
    authOverlay.classList.add('hidden');
    bootAuthenticated().then(()=> Router.start());
  } else {
    hasProfile = false;
    bootDemo();
    Router.start();
  }
})();
