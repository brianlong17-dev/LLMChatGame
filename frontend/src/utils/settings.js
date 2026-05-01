export const MAX_INPUT_CHARS = 5000

export const SETTINGS_KEY = 'game_settings'
export const DEFAULT_SETTINGS = { showPrivate: true, autoRun: true, animateText: true }

export function loadSettings() {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY)) } }
  catch { return DEFAULT_SETTINGS }
}

export function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
}
