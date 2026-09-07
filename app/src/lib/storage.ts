const IDS_KEY = 'ai_interviewer_ids_v1';
const LEGACY_STORAGE_KEY = 'ai_interviewer_sessions_v1';

// Automatically purge legacy full-session storage key if present
try {
  if (typeof window !== 'undefined' && localStorage.getItem(LEGACY_STORAGE_KEY)) {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  }
} catch {
  // Ignore in non-browser environments
}

export function getStoredInterviewIds(): string[] {
  try {
    const raw = localStorage.getItem(IDS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error('Failed to parse interview IDs from localStorage:', err);
    return [];
  }
}

export function saveInterviewId(id: string): void {
  try {
    const ids = getStoredInterviewIds();
    if (!ids.includes(id)) {
      ids.unshift(id);
      localStorage.setItem(IDS_KEY, JSON.stringify(ids));
    }
  } catch (err) {
    console.error('Failed to save interview ID to localStorage:', err);
  }
}

export function removeInterviewId(id: string): void {
  try {
    const ids = getStoredInterviewIds().filter((i) => i !== id);
    localStorage.setItem(IDS_KEY, JSON.stringify(ids));
  } catch (err) {
    console.error('Failed to remove interview ID from localStorage:', err);
  }
}
