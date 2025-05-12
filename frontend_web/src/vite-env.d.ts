/// <reference types="vite/client" />

// 告诉 TypeScript 如何处理 .module.scss 文件
declare module '*.module.scss' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// （可选）如果项目中还会用到非模块化的 .scss 文件
// declare module '*.scss' {
//   const content: string;
//   export default content;
// } 