export interface UserProfile {
  id: number;
  username: string;
  email?: string;
  user_type?: string;
  roles?: string[];
  must_change_password?: boolean;
}

export interface LoginData {
  access_token: string;
  refresh_token: string;
  user: UserProfile;
}

const ACCESS_KEY = "cm_access_token";
const REFRESH_KEY = "cm_refresh_token";
const USER_KEY = "cm_user";

export function getAccessToken(): string {
  return wx.getStorageSync(ACCESS_KEY) || "";
}

export function getRefreshToken(): string {
  return wx.getStorageSync(REFRESH_KEY) || "";
}

export function getUser(): UserProfile | null {
  return wx.getStorageSync(USER_KEY) || null;
}

export function setSession(data: LoginData): void {
  wx.setStorageSync(ACCESS_KEY, data.access_token || "");
  wx.setStorageSync(REFRESH_KEY, data.refresh_token || "");
  wx.setStorageSync(USER_KEY, data.user || null);
}

export function updateAccessToken(token: string): void {
  wx.setStorageSync(ACCESS_KEY, token || "");
}

export function clearSession(): void {
  wx.removeStorageSync(ACCESS_KEY);
  wx.removeStorageSync(REFRESH_KEY);
  wx.removeStorageSync(USER_KEY);
}

export function isLoggedIn(): boolean {
  return Boolean(getAccessToken());
}
