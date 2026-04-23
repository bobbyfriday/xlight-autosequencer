import { useEffect } from 'react';
import { useKeyboardStore } from 'src/store/keyboard';

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

export function useKeyboard(scope: string = 'global') {
  const dispatch = useKeyboardStore((s) => s.dispatch);
  const suspend = useKeyboardStore((s) => s.suspend);
  const resume = useKeyboardStore((s) => s.resume);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (INPUT_TAGS.has(tag)) return;
      const key = e.key === ' ' ? 'Space' : e.key;
      const chord = `${e.shiftKey ? 'Shift+' : ''}${e.ctrlKey || e.metaKey ? 'Ctrl+' : ''}${key}`;
      if (dispatch(chord, scope) || dispatch(key, scope)) {
        e.preventDefault();
      }
    }

    function onFocusIn(e: FocusEvent) {
      if (INPUT_TAGS.has((e.target as HTMLElement)?.tagName)) suspend();
    }

    function onFocusOut(e: FocusEvent) {
      if (INPUT_TAGS.has((e.target as HTMLElement)?.tagName)) resume();
    }

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('focusin', onFocusIn);
    window.addEventListener('focusout', onFocusOut);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('focusin', onFocusIn);
      window.removeEventListener('focusout', onFocusOut);
    };
  }, [dispatch, suspend, resume, scope]);
}
