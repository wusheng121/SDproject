import { ref, watch } from 'vue';

// 主题类型
export const THEME_LIGHT = 'light';
export const THEME_DARK = 'dark';

// 从 localStorage 读取主题设置
const getStoredTheme = () => {
  return localStorage.getItem('theme') || THEME_LIGHT;
};

// 当前主题
export const currentTheme = ref(getStoredTheme());

// 切换主题
export const toggleTheme = () => {
  currentTheme.value = currentTheme.value === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
};

// 设置主题
export const setTheme = (theme) => {
  currentTheme.value = theme;
};

// 监听主题变化，应用到 DOM 和 localStorage
watch(currentTheme, (newTheme) => {
  // 保存到 localStorage
  localStorage.setItem('theme', newTheme);
  
  // 应用到 document
  document.documentElement.setAttribute('data-theme', newTheme);
  
  // 更新 body class
  if (newTheme === THEME_DARK) {
    document.body.classList.add('dark-mode');
    document.body.classList.remove('light-mode');
  } else {
    document.body.classList.add('light-mode');
    document.body.classList.remove('dark-mode');
  }
}, { immediate: true });

// 初始化主题
export const initTheme = () => {
  const theme = getStoredTheme();
  document.documentElement.setAttribute('data-theme', theme);
  if (theme === THEME_DARK) {
    document.body.classList.add('dark-mode');
  } else {
    document.body.classList.add('light-mode');
  }
};

