import http from "./http";

export function apiAssistantChat({ message, sessionId, filename, imageDataUrl }) {
  return http.post(
    "/v1/assistant/chat",
    {
      message,
      session_id: sessionId,
      filename,
      image_data_url: imageDataUrl || ""
    },
    { timeout: 90000, timeoutErrorMessage: "识图和回复超过了等待时间，请再发一次" }
  );
}
