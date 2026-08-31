/**
 * i18n foundation.
 *
 * Scope for this pass: UI chrome and navigation labels only (nav, page
 * titles, buttons, legends, empty-state copy). The AI mentor's generated
 * chat responses are NOT translated yet -- that depends on a live
 * Gemini/API call and is explicitly out of scope per the brief. This
 * file is the structural seam future work plugs into: any user-facing
 * string that can be static goes through t(key) / data-i18n, so adding
 * a language later means adding a dictionary, not hunting the DOM.
 */
const I18N = (function () {
  const STORAGE_KEY = 'learnascent_lang';
  const DICT = {
  "en": {
    "nav.dna": "Learner DNA",
    "nav.journey": "Mountain Journey",
    "nav.dashboard": "Dashboard",
    "nav.assessment": "Assessment",
    "nav.home": "Home",
    "nav.logout": "Logout",
    "lang.label": "Language",
    "home.eyebrow": "LearnAscent AI",
    "home.title_pre": "You are ",
    "home.title_em": "becoming",
    "home.title_post": " what you’re learning.",
    "home.sub": "A personalized learning path powered by real O*NET data, a live skill graph, and an adaptive roadmap engine.",
    "home.cta_start": "Get started",
    "home.cta_login": "Sign in",
    "home.cta_dashboard": "Go to my dashboard",
    "dash.eyebrow": "Dashboard",
    "dash.title": "Your progress at a glance",
    "dash.readiness": "Career readiness",
    "dash.weeks": "Weeks planned",
    "dash.topics": "Active topics",
    "dash.mission": "Today's mission",
    "dash.mission_loading": "Loading roadmap…",
    "dash.mission_empty": "Take your first assessment to unlock a mission.",
    "dash.enter_dna": "Enter Learner DNA",
    "dash.enter_dna_sub": "Your living skill identity, visualized.",
    "dash.enter_journey": "Enter Mountain Journey",
    "dash.enter_journey_sub": "See exactly where you stand on the path.",
    "dash.assessment_cta_label": "Next step",
    "dash.assessment_cta_title": "Assessment not completed — your readiness, roadmap and DNA are waiting on it.",
    "dash.assessment_cta_btn": "Start assessment",
    "assessment.eyebrow": "Assessment",
    "assessment.title": "Rate your real skill level",
    "assessment.sub": "These questions are built from the actual O*NET requirements for your target career. Answer honestly — your roadmap, readiness and Learner DNA are calculated from this.",
    "assessment.back": "← Back to dashboard",
    "assessment.loading": "Loading your assessment…",
    "assessment.empty": "No assessment items are available for this career yet.",
    "assessment.load_error": "Couldn't load your assessment. Please try again.",
    "assessment.submit_error": "Couldn't submit your assessment. Please try again.",
    "assessment.submit_btn": "Submit assessment",
    "assessment.submitting": "Submitting…",
    "assessment.scale_low": "No experience",
    "assessment.scale_high": "Expert",
    "assessment.tier_none": "Not started",
    "assessment.tier_novice": "Novice",
    "assessment.tier_familiar": "Familiar",
    "assessment.tier_proficient": "Proficient",
    "assessment.tier_expert": "Expert",
    "dna.eyebrow": "Learner DNA",
    "dna.title": "Your living digital identity",
    "dna.readiness_label": "Career readiness",
    "dna.assessment_required": "Assessment required",
    "dna.dormant_note": "Your DNA is dormant until your first assessment. No progress is invented — every strand you see is earned.",
    "dna.back": "← Back to dashboard",
    "journey.eyebrow": "Mountain Journey",
    "journey.title": "Your path to the summit",
    "journey.sub": "One journey, two tracks. Hover a marker for detail.",
    "journey.legend_technical": "Technical track",
    "journey.legend_professional": "Professional track",
    "journey.you_are_here": "YOU ARE HERE",
    "journey.status_locked": "Locked",
    "journey.status_upcoming": "Upcoming",
    "journey.status_current": "Current",
    "journey.status_completed": "Completed",
    "journey.back": "← Back to dashboard",
    "journey.empty": "Your roadmap will appear here once your profile is built.",
    "journey.not_started": "Your climb hasn't started. Complete your assessment to generate a real route.",
    "tasks.today_title": "Today's tasks",
    "tasks.week_title": "This week",
    "tasks.week_label": "Week",
    "tasks.today_empty": "Nothing left for today — check back tomorrow.",
    "mentor.who": "Mentor",
    "mentor.idle_hint": "Ask the mentor",
    "mentor.default": "Hi — I'm keeping an eye on your roadmap.",
    "mentor.welcome": "Hi, I'm your LearnAscent assistant. Ask me what to learn next, why a skill matters, or how you're progressing — I'll answer using your real data.",
    "mentor.error": "Something went wrong reaching the assistant. Please try again.",
    "mentor.suggest_today": "What should I learn today?",
    "mentor.suggest_next": "What should I learn next?",
    "mentor.suggest_progress": "How am I progressing?",
    "mentor.suggest_missing": "What skills am I missing?",
    "demo.badge": "DEMO MODE"
  },
  "ta": {
    "nav.dna": "கற்றல் DNA",
    "nav.journey": "மலை பயணம்",
    "nav.dashboard": "கருவி பலகை",
    "nav.assessment": "மதிப்பீடு",
    "nav.home": "முகப்பு",
    "nav.logout": "வெளியேறு",
    "lang.label": "மொழி",
    "home.eyebrow": "LearnAscent AI",
    "home.title_pre": "நீங்கள் ",
    "home.title_em": "கற்றுக்கொண்டு",
    "home.title_post": " மாறிவருகிறீர்கள்.",
    "home.sub": "உண்மையான O*NET தரவு, ஒரு நேரடி திறன் வரைபடம், தகவமைப்பு பாதை என்ஜின் ஆகியவற்றால் இயக்கப்படும் தனிப்பயன் கற்றல் பாதை.",
    "home.cta_start": "தொடங்குங்கள்",
    "home.cta_login": "உள்நுழையவும்",
    "home.cta_dashboard": "என் கருவி பலகைக்குச் செல்லவும்",
    "dash.eyebrow": "கருவி பலகை",
    "dash.title": "உங்கள் முன்னேற்றம் ஒரே பார்வையில்",
    "dash.readiness": "தொழில் தயார்நிலை",
    "dash.weeks": "திட்டமிடப்பட்ட வாரங்கள்",
    "dash.topics": "செயலில் உள்ள தலைப்புகள்",
    "dash.mission": "இன்றைய பணி",
    "dash.mission_loading": "பாதை ஏற்றப்படுகிறது…",
    "dash.mission_empty": "ஒரு பணியைப் பெற உங்கள் முதல் மதிப்பீட்டை எடுக்கவும்.",
    "dash.enter_dna": "கற்றல் DNA-க்குள் நுழையவும்",
    "dash.enter_dna_sub": "உங்கள் திறன் அடையாளம், உயிரோட்டமாக.",
    "dash.enter_journey": "மலை பயணத்திற்குள் நுழையவும்",
    "dash.enter_journey_sub": "நீங்கள் எங்கு நிற்கிறீர்கள் என்பதைத் தெளிவாகக் காணுங்கள்.",
    "dash.assessment_cta_label": "அடுத்த படி",
    "dash.assessment_cta_title": "மதிப்பீடு முடிக்கப்படவில்லை — உங்கள் தயார்நிலை, பாதை மற்றும் DNA இதற்காகக் காத்திருக்கின்றன.",
    "dash.assessment_cta_btn": "மதிப்பீட்டைத் தொடங்கு",
    "assessment.eyebrow": "மதிப்பீடு",
    "assessment.title": "உங்கள் உண்மையான திறன் நிலையை மதிப்பிடுங்கள்",
    "assessment.sub": "இந்த கேள்விகள் உங்கள் இலக்கு தொழிலுக்கான உண்மையான O*NET தேவைகளிலிருந்து உருவாக்கப்பட்டவை. நேர்மையாக பதிலளியுங்கள் — உங்கள் பாதை, தயார்நிலை மற்றும் DNA இதிலிருந்தே கணக்கிடப்படும்.",
    "assessment.back": "← கருவி பலகைக்குத் திரும்பு",
    "assessment.loading": "உங்கள் மதிப்பீடு ஏற்றப்படுகிறது…",
    "assessment.empty": "இந்த தொழிலுக்கு மதிப்பீட்டு உருப்படிகள் இன்னும் இல்லை.",
    "assessment.load_error": "மதிப்பீட்டை ஏற்ற முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "assessment.submit_error": "மதிப்பீட்டைச் சமர்ப்பிக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "assessment.submit_btn": "மதிப்பீட்டைச் சமர்ப்பிக்கவும்",
    "assessment.submitting": "சமர்ப்பிக்கப்படுகிறது…",
    "assessment.scale_low": "அனுபவம் இல்லை",
    "assessment.scale_high": "நிபுணர்",
    "assessment.tier_none": "தொடங்கவில்லை",
    "assessment.tier_novice": "தொடக்க நிலை",
    "assessment.tier_familiar": "பரிச்சயமானது",
    "assessment.tier_proficient": "திறமையானது",
    "assessment.tier_expert": "நிபுணர்",
    "dna.eyebrow": "கற்றல் DNA",
    "dna.title": "உங்கள் உயிரோட்டமான டிஜிட்டல் அடையாளம்",
    "dna.readiness_label": "தொழில் தயார்நிலை",
    "dna.assessment_required": "மதிப்பீடு தேவை",
    "dna.dormant_note": "உங்கள் முதல் மதிப்பீடு வரை உங்கள் DNA அமைதியாக உள்ளது. போலியான முன்னேற்றம் காட்டப்படாது.",
    "dna.back": "← கருவி பலகைக்குத் திரும்பு",
    "journey.eyebrow": "மலை பயணம்",
    "journey.title": "உச்சிக்கான உங்கள் பாதை",
    "journey.sub": "ஒரே பயணம், இரண்டு பாதைகள். விவரங்களுக்கு ஒரு புள்ளியின் மேல் நகர்த்தவும்.",
    "journey.legend_technical": "தொழில்நுட்பப் பாதை",
    "journey.legend_professional": "தொழில்முறைப் பாதை",
    "journey.you_are_here": "நீங்கள் இங்கே உள்ளீர்கள்",
    "journey.status_locked": "பூட்டப்பட்டது",
    "journey.status_upcoming": "வரவிருக்கும்",
    "journey.status_current": "தற்போதைய",
    "journey.status_completed": "முடிந்தது",
    "journey.back": "← கருவி பலகைக்குத் திரும்பு",
    "journey.empty": "உங்கள் சுமை திட்டம் தயாரானதும் இங்கே தோன்றும்.",
    "journey.not_started": "உங்கள் ஏற்றம் இன்னும் தொடங்கவில்லை. உண்மையான பாதையை உருவாக்க உங்கள் மதிப்பீட்டை முடிக்கவும்.",
    "tasks.today_title": "இன்றைய பணிகள்",
    "tasks.week_title": "இந்த வாரம்",
    "tasks.week_label": "வாரம்",
    "tasks.today_empty": "இன்றைக்கு எதுவும் மீதமில்லை — நாளை பாருங்கள்.",
    "mentor.who": "மென்டார்",
    "mentor.idle_hint": "மென்டாரிடம் கேளுங்கள்",
    "mentor.default": "வணக்கம் — உங்கள் பாதையை நான் கவனித்துக் கொண்டிருக்கிறேன்.",
    "demo.badge": "டெமோ முறை"
  },
  "hi": {
    "nav.dna": "लर्नर DNA",
    "nav.journey": "पर्वत यात्रा",
    "nav.dashboard": "डैशबोर्ड",
    "nav.assessment": "आकलन",
    "nav.home": "होम",
    "nav.logout": "लॉगआउट",
    "lang.label": "भाषा",
    "home.eyebrow": "LearnAscent AI",
    "home.title_pre": "आप वही ",
    "home.title_em": "बन रहे हैं",
    "home.title_post": " जो आप सीख रहे हैं।",
    "home.sub": "वास्तविक O*NET डेटा, एक लाइव स्किल ग्राफ़ और एडेप्टिव रोडमैप इंजन से संचालित व्यक्तिगत सीखने का मार्ग।",
    "home.cta_start": "शुरू करें",
    "home.cta_login": "साइन इन",
    "home.cta_dashboard": "मेरे डैशबोर्ड पर जाएं",
    "dash.eyebrow": "डैशबोर्ड",
    "dash.title": "आपकी प्रगति एक नज़र में",
    "dash.readiness": "करियर तैयारी",
    "dash.weeks": "नियोजित सप्ताह",
    "dash.topics": "सक्रिय विषय",
    "dash.mission": "आज का मिशन",
    "dash.mission_loading": "रोडमैप लोड हो रहा है…",
    "dash.mission_empty": "मिशन पाने के लिए अपना पहला आकलन दें।",
    "dash.enter_dna": "Learner DNA में प्रवेश करें",
    "dash.enter_dna_sub": "आपकी जीवंत डिजिटल पहचान।",
    "dash.enter_journey": "पर्वत यात्रा में प्रवेश करें",
    "dash.enter_journey_sub": "देखें आप अभी कहां खड़े हैं।",
    "dash.assessment_cta_label": "अगला कदम",
    "dash.assessment_cta_title": "आकलन पूरा नहीं हुआ — आपकी तैयारी, रोडमैप और DNA इसी पर निर्भर हैं।",
    "dash.assessment_cta_btn": "आकलन शुरू करें",
    "assessment.eyebrow": "आकलन",
    "assessment.title": "अपने वास्तविक कौशल स्तर को आंकें",
    "assessment.sub": "ये प्रश्न आपके लक्षित करियर की वास्तविक O*NET आवश्यकताओं से बनाए गए हैं। ईमानदारी से उत्तर दें — आपका रोडमैप, तैयारी और DNA इसी से गणना किए जाते हैं।",
    "assessment.back": "← डैशबोर्ड पर वापस",
    "assessment.loading": "आपका आकलन लोड हो रहा है…",
    "assessment.empty": "इस करियर के लिए अभी कोई आकलन आइटम उपलब्ध नहीं है।",
    "assessment.load_error": "आकलन लोड नहीं हो सका। कृपया फिर से प्रयास करें।",
    "assessment.submit_error": "आकलन सबमिट नहीं हो सका। कृपया फिर से प्रयास करें।",
    "assessment.submit_btn": "आकलन सबमिट करें",
    "assessment.submitting": "सबमिट हो रहा है…",
    "assessment.scale_low": "कोई अनुभव नहीं",
    "assessment.scale_high": "विशेषज्ञ",
    "assessment.tier_none": "शुरू नहीं हुआ",
    "assessment.tier_novice": "नौसिखिया",
    "assessment.tier_familiar": "परिचित",
    "assessment.tier_proficient": "दक्ष",
    "assessment.tier_expert": "विशेषज्ञ",
    "dna.eyebrow": "लर्नर DNA",
    "dna.title": "आपकी जीवंत डिजिटल पहचान",
    "dna.readiness_label": "करियर तैयारी",
    "dna.assessment_required": "आकलन आवश्यक",
    "dna.dormant_note": "आपका पहला आकलन होने तक DNA निष्क्रिय रहता है। कोई भी प्रगति गढ़ी नहीं जाती।",
    "dna.back": "← डैशबोर्ड पर वापस",
    "journey.eyebrow": "पर्वत यात्रा",
    "journey.title": "शिखर तक आपका मार्ग",
    "journey.sub": "एक यात्रा, दो ट्रैक।",
    "journey.legend_technical": "तकनीकी ट्रैक",
    "journey.legend_professional": "व्यावसायिक ट्रैक",
    "journey.you_are_here": "आप यहां हैं",
    "journey.status_locked": "लॉक",
    "journey.status_upcoming": "आगामी",
    "journey.status_current": "वर्तमान",
    "journey.status_completed": "पूर्ण",
    "journey.back": "← डैशबोर्ड पर वापस",
    "journey.empty": "आपका प्रोफ़ाइल बनने के बाद यहां दिखेगा।",
    "journey.not_started": "आपकी चढ़ाई अभी शुरू नहीं हुई है। वास्तविक मार्ग बनाने के लिए अपना आकलन पूरा करें।",
    "tasks.today_title": "आज के कार्य",
    "tasks.week_title": "इस सप्ताह",
    "tasks.week_label": "सप्ताह",
    "tasks.today_empty": "आज के लिए कुछ बाकी नहीं है — कल फिर देखें।",
    "mentor.who": "मेंटर",
    "mentor.idle_hint": "मेंटर से पूछें",
    "mentor.default": "नमस्ते — मैं आपके रोडमैप पर नज़र रख रहा हूं।",
    "demo.badge": "डेमो मोड"
  }
};

  let current = localStorage.getItem(STORAGE_KEY) || 'en';
  if (!DICT[current]) current = 'en';

  function t(key) {
    return (DICT[current] && DICT[current][key]) || DICT.en[key] || key;
  }

  function apply() {
    document.documentElement.setAttribute('lang', current);
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-attr]').forEach((el) => {
      el.getAttribute('data-i18n-attr').split(';').forEach((pair) => {
        const [attr, key] = pair.split(':');
        if (attr && key) el.setAttribute(attr.trim(), t(key.trim()));
      });
    });
    document.querySelectorAll('.lang-option').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.lang === current);
    });
    window.dispatchEvent(new CustomEvent('languagechange', { detail: { lang: current } }));
  }

  function set(lang) {
    if (!DICT[lang]) return;
    current = lang;
    localStorage.setItem(STORAGE_KEY, lang);
    apply();
    // Best-effort persistence to the learner's real profile via the
    // existing PUT /api/learner/profile endpoint (preferred_language
    // already exists on the backend model). Never blocks the UI.
    if (window.auth && auth.isAuthenticated() && window.learner && learner.updatePreferredLanguage) {
      learner.updatePreferredLanguage(lang).catch(() => {});
    }
  }

  function get() { return current; }

  return { t, apply, set, get, languages: Object.keys(DICT) };
})();
