import { useRef, useState, useCallback, useEffect } from 'react';

interface UseAudioReturn {
  audioRef: React.MutableRefObject<HTMLAudioElement | null>;
  playing: boolean;
  timeMs: number;
  durationMs: number;
  play: () => void;
  pause: () => void;
  seek: (ms: number) => void;
  setSrc: (src: string) => void;
}

export function useAudio(): UseAudioReturn {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);
  const [playing, setPlaying] = useState(false);
  const [timeMs, setTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);

  // Create the audio element once
  if (audioRef.current === null) {
    audioRef.current = new Audio();
  }

  useEffect(() => {
    const audio = audioRef.current!;

    function onPlay() { setPlaying(true); }
    function onPause() { setPlaying(false); }
    function onDurationChange() {
      setDurationMs(isFinite(audio.duration) ? Math.round(audio.duration * 1000) : 0);
    }
    function onEnded() { setPlaying(false); }

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('ended', onEnded);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // RAF loop for time updates while playing
  useEffect(() => {
    function tick() {
      const audio = audioRef.current;
      if (audio && !audio.paused) {
        setTimeMs(Math.round(audio.currentTime * 1000));
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    if (playing) {
      rafRef.current = requestAnimationFrame(tick);
    } else {
      cancelAnimationFrame(rafRef.current);
    }

    return () => { cancelAnimationFrame(rafRef.current); };
  }, [playing]);

  const play = useCallback(() => {
    audioRef.current?.play().catch(() => {});
  }, []);

  const pause = useCallback(() => {
    audioRef.current?.pause();
  }, []);

  const seek = useCallback((ms: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const dur = isFinite(audio.duration) ? audio.duration * 1000 : 0;
    const clamped = Math.max(0, Math.min(ms, dur));
    audio.currentTime = clamped / 1000;
    setTimeMs(clamped);
  }, []);

  const setSrc = useCallback((src: string) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.src = src;
    audio.load();
  }, []);

  return { audioRef, playing, timeMs, durationMs, play, pause, seek, setSrc };
}
