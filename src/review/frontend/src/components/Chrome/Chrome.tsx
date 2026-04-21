import React from 'react';
import type { Screen } from 'src/store/app';
import styles from './Chrome.module.css';

const TABS: { id: Screen; label: string; key: string }[] = [
  { id: 'library', label: 'Library', key: '1' },
  { id: 'drop', label: 'Drop', key: '2' },
  { id: 'analyze', label: 'Analyze', key: '3' },
  { id: 'timeline', label: 'Timeline', key: '4' },
  { id: 'theme', label: 'Theme', key: '5' },
  { id: 'export', label: 'Export', key: '6' },
];

interface Props {
  activeScreen: Screen;
  onNavigate?: (screen: Screen) => void;
  children: React.ReactNode;
}

export function Chrome({ activeScreen, onNavigate, children }: Props) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.wordmark}>xOnset</span>
        <nav role="tablist" className={styles.toolStrip}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-label={tab.label}
              data-active={String(activeScreen === tab.id)}
              className={styles.tab}
              onClick={() => onNavigate?.(tab.id)}
            >
              <span className={styles.tabKey}>{tab.key}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main className={styles.content}>{children}</main>
      <footer className={styles.statusBar} />
    </div>
  );
}
