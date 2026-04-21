import { useEffect } from 'react';
import { usePreferencesStore } from 'src/store/preferences';

export function useDesignTokens() {
  const mode = usePreferencesStore((s) => s.mode);
  const density = usePreferencesStore((s) => s.density);

  useEffect(() => {
    document.body.dataset.mode = mode;
  }, [mode]);

  useEffect(() => {
    document.body.dataset.density = density;
  }, [density]);
}
