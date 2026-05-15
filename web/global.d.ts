// Ambient declarations for side-effect imports.
// TypeScript 6 (TS2882) requires an explicit declaration for side-effect
// imports such as `import './globals.css'`; the bundler resolves these.
declare module '*.css';
