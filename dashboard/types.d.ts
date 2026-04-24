// CSS Module declarations to satisfy TypeScript type checker
declare module '*.css' {
  const content: { [className: string]: string };
  export default content;
}
