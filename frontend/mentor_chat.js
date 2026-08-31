/**
 * AI Learner Assistant — Chat Service + UI.
 *
 * Same fetch/auth pattern as learner.js / recommendations.js: every
 * reply comes from POST /api/mentor/chat, which is grounded in the
 * authenticated learner's REAL profile/skills/assessment/roadmap data
 * on the backend. This module never fabricates a reply client-side —
 * if the learner isn't signed in or hasn't set a target career, it
 * shows a sign-in/setup prompt instead of chatting.
 */
class MentorChatService {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8000/api';
  }

  async sendMessage(message, history) {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    const response = await fetch(`${this.apiBase}/mentor/chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        history: history.map(m => ({ role: m.role, content: m.content })),
      }),
    });
    if (!response.ok) {
      const err = new Error('Failed to reach the assistant');
      err.status = response.status;
      throw err;
    }
    return await response.json();
  }
}

const mentorChatService = new MentorChatService();

const MentorChat = (function () {
  let messagesEl, suggestionsEl, inputEl, sendBtn, signinNoteEl, inputRowEl;
  let history = []; // [{role:'user'|'assistant', content:string}]
  let initialized = false;
  let sending = false;

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = `mentor-msg ${role}`;
    div.innerHTML = esc(content).replace(/\n/g, '<br>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function appendSystemNote(content) {
    const div = document.createElement('div');
    div.className = 'mentor-msg system-note';
    div.textContent = content;
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'mentor-msg assistant typing';
    div.textContent = 'Thinking…';
    div.id = 'mentor-typing';
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById('mentor-typing');
    if (el) el.remove();
  }

  function setSending(state) {
    sending = state;
    sendBtn.disabled = state || !inputEl.value.trim();
    inputEl.disabled = state;
  }

  async function send(text) {
    const message = (text != null ? text : inputEl.value).trim();
    if (!message || sending) return;

    inputEl.value = '';
    autosize();
    appendMessage('user', message);
    history.push({ role: 'user', content: message });
    setSending(true);
    showTyping();

    try {
      const data = await mentorChatService.sendMessage(message, history.slice(0, -1));
      hideTyping();
      appendMessage('assistant', data.reply);
      history.push({ role: 'assistant', content: data.reply });
    } catch (error) {
      hideTyping();
      const msg = I18N && I18N.t ? I18N.t('mentor.error') : "Something went wrong reaching the assistant. Please try again.";
      appendSystemNote(msg);
    } finally {
      setSending(false);
    }
  }

  function autosize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 90) + 'px';
  }

  function renderSuggestions() {
    const keys = ['mentor.suggest_today', 'mentor.suggest_next', 'mentor.suggest_progress', 'mentor.suggest_missing'];
    suggestionsEl.innerHTML = '';
    keys.forEach((key) => {
      const label = I18N && I18N.t ? I18N.t(key) : key;
      const chip = document.createElement('div');
      chip.className = 'mentor-suggestion';
      chip.textContent = label;
      chip.addEventListener('click', () => send(label));
      suggestionsEl.appendChild(chip);
    });
  }

  function reset() {
    // Called on logout / login so a new learner never sees the
    // previous learner's conversation.
    history = [];
    initialized = false;
    if (messagesEl) messagesEl.innerHTML = '';
  }

  function showChat() {
    signinNoteEl.style.display = 'none';
    inputRowEl.style.display = 'flex';
    suggestionsEl.style.display = 'flex';
    if (!initialized) {
      const welcome = I18N && I18N.t ? I18N.t('mentor.welcome') : "Hi, I'm your LearnAscent assistant.";
      appendMessage('assistant', welcome);
      history.push({ role: 'assistant', content: welcome });
      renderSuggestions();
      initialized = true;
    }
  }

  function showSignInRequired() {
    signinNoteEl.style.display = 'block';
    inputRowEl.style.display = 'none';
    suggestionsEl.style.display = 'none';
    messagesEl.innerHTML = '';
  }

  // Called every time the mentor panel is opened. `ready` reflects
  // whether the learner is authenticated AND has a profile with a
  // target career (i.e. whether the backend will have real context).
  function onOpen(ready) {
    if (ready) {
      showChat();
    } else {
      showSignInRequired();
    }
  }

  function init(ids) {
    messagesEl = document.getElementById(ids.messages);
    suggestionsEl = document.getElementById(ids.suggestions);
    inputEl = document.getElementById(ids.input);
    sendBtn = document.getElementById(ids.sendBtn);
    signinNoteEl = document.getElementById(ids.signinNote);
    inputRowEl = document.getElementById(ids.inputRow);
    const closeBtn = document.getElementById(ids.closeBtn);

    inputEl.addEventListener('input', () => {
      autosize();
      sendBtn.disabled = sending || !inputEl.value.trim();
    });
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
    sendBtn.addEventListener('click', () => send());
    sendBtn.disabled = true;
    if (closeBtn) closeBtn.addEventListener('click', () => Mentor.close());
  }

  return { init, onOpen, reset };
})();
