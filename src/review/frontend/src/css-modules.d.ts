// Global declaration to allow TypeScript to import CSS module files.
declare module '*.module.css' {
  const classes: Record<string, string>;
  export default classes;
}
