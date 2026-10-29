let accessToken = "";

export function setAccessToken(value) {
  accessToken = value || "";
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = "";
}
