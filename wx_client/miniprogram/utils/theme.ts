export type Theme = "light" | "dark";

const THEME_KEY = "cm_theme";

export function getTheme(): Theme {
  return wx.getStorageSync(THEME_KEY) === "dark" ? "dark" : "light";
}

export function setTheme(theme: Theme): void {
  wx.setStorageSync(THEME_KEY, theme);
  applyThemeChrome(theme);
}

export function applyThemeChrome(theme: Theme): void {
  const dark = theme === "dark";
  wx.setNavigationBarColor({
    frontColor: dark ? "#ffffff" : "#000000",
    backgroundColor: dark ? "#202923" : "#ffffff",
    animation: { duration: 0 }
  });
  wx.setBackgroundColor({
    backgroundColor: dark ? "#171d19" : "#f5f6f3",
    backgroundColorTop: dark ? "#202923" : "#ffffff",
    backgroundColorBottom: dark ? "#171d19" : "#f5f6f3"
  });
  wx.setTabBarStyle({
    color: dark ? "#aab8ae" : "#748078",
    selectedColor: dark ? "#91b7a0" : "#47785f",
    backgroundColor: dark ? "#202923" : "#ffffff",
    borderStyle: dark ? "white" : "black",
    fail: () => undefined
  });
}

export function applyPageTheme(page: any): Theme {
  const theme = getTheme();
  page.setData({ theme });
  applyThemeChrome(theme);
  return theme;
}
