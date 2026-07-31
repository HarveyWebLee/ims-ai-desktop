#!/usr/bin/env node
/**
 * 代码编辑后提醒影响面（不阻断）。
 */
const message = [
  "提醒：本次改动请确认影响面是否覆盖：",
  "1) chat / resume / reject / abort 对称路径",
  "2) Store / checkpoint / session_store 生命周期",
  "3) packages 契约与桌面 AgentController 一致",
  "4) 达梦只读；桌面 M1 无 BPMN 抽屉回归",
].join("\n");

process.stdout.write(
  JSON.stringify({
    additional_context: message,
  }),
);
