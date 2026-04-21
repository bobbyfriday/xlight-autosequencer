import React from 'react';
import styles from './Inspector.module.css';

interface InspectorProps {
  title?: string;
  children?: React.ReactNode;
}

export function Inspector({ title = 'Inspector', children }: InspectorProps) {
  return (
    <div data-testid="inspector" className={styles.root}>
      <div className={styles.header}>{title}</div>
      <div className={styles.content}>{children}</div>
    </div>
  );
}
