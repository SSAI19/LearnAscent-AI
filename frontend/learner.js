/**
 * Learner API Service
 * Fetches learner data from the backend
 */

class LearnerService {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8000/api';
  }

  /**
   * Get current learner's profile and related data
   */
  async getLearnerProfile() {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await fetch(`${this.apiBase}/learner`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const err = new Error('Failed to fetch learner profile');
        err.status = response.status;
        throw err;
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Create a learner profile
   */
  async createProfile(profileData) {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await fetch(`${this.apiBase}/learner/profile`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create profile');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get skill gap analysis
   */
  async getSkillGap(source = 'essential_skills') {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await fetch(`${this.apiBase}/engines/skill-gap`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ source }),
      });

      if (!response.ok) {
        throw new Error('Failed to get skill gap');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get readiness score
   */
  async getReadiness() {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await fetch(`${this.apiBase}/engines/readiness`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get readiness');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Search O*NET occupations by free-text query (no auth required).
   */
  async searchOccupations(query){
    if(!query || query.length < 2) return [];
    try {
      const response = await fetch(`${this.apiBase}/engines/occupation-search?query=${encodeURIComponent(query)}`);
      if(!response.ok) return [];
      return await response.json();
    } catch (error) {
      return [];
    }
  }

  /**
   * Get roadmap
   */
  async getRoadmap() {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await fetch(`${this.apiBase}/engines/roadmap`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get roadmap');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Submit one real assessment answer to the existing adaptive-engine
   * endpoint (POST /api/engines/assessment). This is the ONLY place an
   * assessment result is created — nothing here is fabricated; score and
   * weak_concepts come directly from what the learner answered on the
   * Assessment page. Returns the engine's real adaptation result.
   */
  async submitAssessmentAnswer({ skill_element, score, weak_concepts = [] }) {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    try {
      const response = await fetch(`${this.apiBase}/engines/assessment`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ skill_element, score, weak_concepts }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to submit assessment');
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Persist a learner's skill level (existing POST /api/learner/skills/{element}
   * endpoint) so the skill-gap and readiness engines see the assessed level
   * on their next run, not just an isolated assessment record.
   * level is on O*NET's 0-7 scale, matching SkillRecord.level.
   */
  async updateSkillLevel(element, level, source = 'assessment') {
    const token = auth.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    try {
      const qs = new URLSearchParams({ level: String(level), source }).toString();
      const response = await fetch(`${this.apiBase}/learner/skills/${encodeURIComponent(element)}?${qs}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to update skill');
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get the learner's real daily/weekly tasks (each task is a real
   * roadmap topic, with real persisted completion state).
   */
  async getTasks() {
    const token = auth.getToken();
    if (!token) throw new Error('Not authenticated');
    const response = await fetch(`${this.apiBase}/engines/tasks`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to load tasks');
    return await response.json();
  }

  /**
   * Mark one real roadmap topic complete. Returns the refreshed task list.
   */
  async completeTask(topicId) {
    const token = auth.getToken();
    if (!token) throw new Error('Not authenticated');
    const response = await fetch(`${this.apiBase}/engines/tasks/complete`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_id: topicId }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to complete task');
    }
    return await response.json();
  }

  /**
   * Undo a task completion (correcting a mis-click).
   */
  async uncompleteTask(topicId) {
    const token = auth.getToken();
    if (!token) throw new Error('Not authenticated');
    const response = await fetch(`${this.apiBase}/engines/tasks/uncomplete`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic_id: topicId }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to update task');
    }
    return await response.json();
  }

  /**
   * Persist the learner's language preference using the existing
   * PUT /api/learner/profile endpoint (preferred_language already exists
   * on the backend model). Best-effort — callers should not block the UI
   * on this, since it is a UI-foundation feature, not a hard requirement.
   */
  async updatePreferredLanguage(lang) {
    const token = auth.getToken();
    if (!token) return null;
    try {
      const response = await fetch(`${this.apiBase}/learner/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preferred_language: lang }),
      });
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      return null;
    }
  }
}

// Export as global
const learner = new LearnerService();
