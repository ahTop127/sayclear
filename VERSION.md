# SayClear v0.2.0

- **版本号：** `v0.2.0`
- **日期：** 2026-09-04
- **状态：** 可日常使用的第二版 Mac 客户端
- **仓库：** https://github.com/ahTop127/sayclear

## 相对 v0.1.0 的主要修改

1. **整理通道：** 从 wintoken.dev 换为 DeepSeek 官方 `api.deepseek.com`，模型 `deepseek-v4-flash`。短句整理大约 0.6–1 秒，不再是 6–17 秒。
2. **识别：** 本机 Google gRPC 流式握手失败，已关闭。说完后走 REST `chirp_3`，避免失败流式再空等 8 秒。录音改为内存 PCM，不再写 wav、不再等 ffmpeg 最多 3 秒。
3. **短确认语：** 「好的」「是的」等是要填进输入框的正文，不再当垃圾词输出空结果。
4. **悬浮层：** Thinking 居中；Thinking 时底部从左到右进度条。⌘ 开始 / 结束（或点 OK）各响一次系统短提示音；点 X 取消不响。
5. **测试：** `docs/SayClear-测试用例.md` 与 `tests/run_sayclear_cases.py`。

## 产品行为（未改）

- 全局 ⌘ 单击切换开始/结束；胶囊左 X 取消、右 OK 结束
- 录音中不把半句填进输入框
- 成功后正文直接进当前输入框；不代发、无成功 toast

## 运行

见仓库 [README](./README.md)。本机日常：

```bash
cd /Users/kimberly/project/voice/未命名
./run_sayclear.sh
```
