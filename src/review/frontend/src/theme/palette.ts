export const DARK = {
  bg0: '#111114',
  bg1: '#1a1a20',
  bg2: '#22222a',
  bg3: '#2a2a33',
  bg4: '#33333e',
  line: '#2a2a33',
  line2: '#3a3a46',
  ink: '#f5f5f0',
  ink2: '#a8a8b0',
  ink3: '#6a6a78',
  accent: '#d97757',
  accentInk: '#000',
  ok: '#4ade80',
  warn: '#f5a623',
  err: '#d43a2f',
} as const;

export const LIGHT = {
  bg0: '#f4f4ef',
  bg1: '#ffffff',
  bg2: '#ececec',
  bg3: '#dcdcd4',
  bg4: '#cac8bf',
  line: '#dcdcd4',
  line2: '#c4c4bc',
  ink: '#1a1a20',
  ink2: '#555560',
  ink3: '#8a8a90',
  accent: '#d97757',
  accentInk: '#fff',
  ok: '#2f8f3e',
  warn: '#b8881a',
  err: '#c42818',
} as const;

export type Palette = typeof DARK;

export function getPalette(mode: 'dark' | 'light'): Palette {
  return mode === 'light' ? LIGHT : DARK;
}
