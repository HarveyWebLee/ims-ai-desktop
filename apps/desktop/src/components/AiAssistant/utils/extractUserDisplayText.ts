/**
 * 从 Checkpoint 还原的用户消息中提取使用者可见的原始输入。
 * 与 platform-agent-service prompt_assembly.extract_user_display_message 格式一致。
 */
const USER_TURN_SECTION_HEADER = "## 使用者本轮消息";

export function extractUserDisplayText(text: string): string {
  const raw = text.trim();
  if (!raw) return raw;

  const markerIndex = raw.indexOf(USER_TURN_SECTION_HEADER);
  if (markerIndex >= 0) {
    const body = raw.slice(markerIndex + USER_TURN_SECTION_HEADER.length).trim();
    return body || raw;
  }

  return raw;
}
