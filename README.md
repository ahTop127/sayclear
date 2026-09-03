# SayClear

Mac 悬浮口述工具：说话 → 智能整理 → 填入当前任意输入框。

当前仓库版本：**[v0.1.0](./VERSION.md)**（2026-09-03）。主路径已跑通；识别与整理仍在说完后串行，所以会偏慢。加速方案已定，尚未合入。

## 这一版怎么跑

1. 复制 `.env.example` 为 `.env`，填整理密钥；语音识别用本机 Google ADC（`gcloud auth application-default login`），项目 ID 默认 `sayclear`。
2. 使用 Anaconda 的 Python 3.13（系统自带 3.9 装不了当前 PyObjC）：

```bash
/opt/anaconda3/bin/python3 -m pip install -r requirements.txt
./run_sayclear.sh
```

3. 在系统设置里允许该 Python 的**麦克风**和**辅助功能**。
4. 光标放进输入框，点一下 ⌘ 开始说话，再点 ⌘ 或胶囊上的 OK 结束。

不要把 `.env`、服务账号 JSON 或其它密钥提交进 git。

## 目录

| 路径 | 内容 |
|---|---|
| `sayclear/` | Mac 客户端（录音、热键、HUD、识别、整理、填入） |
| `docs/` | 需求、架构、语音接入、线框原型 |
| `tools/` | 早期麦克风识别连通测试 |
| `VERSION.md` | 当前版本说明 |

## 文档

- [功能需求](./docs/SayClear-功能需求文档.md)
- [后端技术架构](./docs/SayClear-后端技术架构.md)
- [语音识别接入](./docs/SayClear-语音识别接入.md)
