# SayClear

Mac 桌面悬浮工具，不是浏览器插件、也不是输入法。

对着电脑说话 → 整理成可直接用的正文 → 填进**当前任意输入框**。不代发、不弹成功提示。录音过程中不会把半句字打进输入框。

当前版本：**[v0.2.0](./VERSION.md)**（2026-09-04）

---

## 怎么用

第一次在 Mac 上跑这个项目，按下面做。

### 1. 环境

- macOS
- [Anaconda](https://www.anaconda.com/) 的 **Python 3.13**（系统自带 3.9 装不了当前 PyObjC）
- [ffmpeg](https://ffmpeg.org/)（Anaconda 里通常已有：`/opt/anaconda3/bin/ffmpeg`）
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)（语音识别用本机登录，不用把密钥写进代码）
- 一把 [DeepSeek 官方 API](https://platform.deepseek.com/) 密钥（整理文本用）

克隆仓库：

```bash
git clone https://github.com/ahTop127/sayclear.git
cd sayclear
```

安装依赖（必须用 Anaconda 的 Python）：

```bash
/opt/anaconda3/bin/python3 -m pip install -r requirements.txt
```

### 2. 配置密钥（不要提交 git）

```bash
cp .env.example .env
```

用编辑器打开 `.env`：

| 项 | 填什么 |
|---|---|
| `CUN_AI_API_KEY` | DeepSeek 控制台里的 API Key |
| `CUN_AI_BASE_URL` | 保持 `https://api.deepseek.com/v1` |
| `CUN_AI_MODEL` | 保持 `deepseek-v4-flash` |
| `GOOGLE_CLOUD_PROJECT` | 你的 Google Cloud 项目 ID（本仓库默认 `sayclear`） |

语音识别**不要**把服务账号 JSON 或 API key 写进仓库。本机执行一次：

```bash
gcloud auth application-default login
gcloud config set project sayclear
```

浏览器登录有权访问该项目的 Google 账号即可。项目需已开通 **Cloud Speech-to-Text API** 和结算。

### 3. 系统权限（第一次必做）

打开 **系统设置 → 隐私与安全性**：

1. **麦克风**：允许 `/opt/anaconda3/bin/python3`（以及如有提示，允许 ffmpeg）
2. **辅助功能**：同样允许这个 Python。没有这项，⌘ 全局热键和往输入框粘贴都不会生效

权限改完后，完全退出 SayClear 再启动一次。

### 4. 启动

在项目目录：

```bash
./run_sayclear.sh
```

菜单栏右侧出现 **SC** 即表示已运行。终端会打印当前用的 Python 路径，方便对照权限里勾的是不是同一个。不要用系统自带的 `python3` 启动。

退出：点菜单栏 **SC → 退出 SayClear**，或在终端 `Ctrl+C`。

配过 `.env` 和系统权限之后，以后每次在项目目录再执行 `./run_sayclear.sh` 即可。如果 ⌘ 没反应，多半是辅助功能里勾的不是 `/opt/anaconda3/bin/python3`。

### 5. 日常怎么口述

1. 把光标放进要填字的输入框（备忘录、浏览器、ChatGPT、邮件都可以）。
2. **点一下 ⌘**（不要按住）：听到短提示音，屏幕底部出现暗黑胶囊，开始说话。
3. 说完再 **点一下 ⌘**，或点胶囊右侧 **OK**。再响一次提示音，胶囊变成居中的 **Thinking** 和从左到右的进度条。
4. 正文出现在当前输入框。自己检查、改几个字，**自己**按回车或点发送。SayClear 不会代发。
5. 说错了、不想要了：录音时点胶囊左侧 **X**，这次作废，输入框不变。

「好的」「是的」「可以」「收到」这类短确认语是用户要填进输入框的正文，会保留。只有「嗯」「那个」这类没有信息量的垫话才会被丢掉。

---

## 这一版相对 v0.1.0 的主要修改

详见 [VERSION.md](./VERSION.md)。摘要：

- 整理从 wintoken 网关换成 **DeepSeek 官方 API**，等待从十多秒降到大约 1 秒内
- 去掉本机不可用的 Google gRPC 流式（它曾把识别拖慢）；仍是说完后 REST 识别
- 内存 PCM 录音，去掉写文件和 ffmpeg 长等待
- Thinking 居中，并加从左到右进度条；⌘ 开始/结束有提示音
- 短确认语（好的、是的、可以、收到等）会填入输入框；无意义垫话仍会丢掉
- 整理关闭深度思考，走快速回答
- 补充自动测试用例 `tests/run_sayclear_cases.py`

不要把 `.env`、服务账号 JSON 提交进 git。

## 目录

| 路径 | 内容 |
|---|---|
| `sayclear/` | Mac 客户端 |
| `docs/` | 需求、架构、语音接入、测试用例、线框原型 |
| `tests/` | 整理与校验的自动用例 |
| `tools/` | 早期麦克风识别连通测试 |
| `run_sayclear.sh` | 本机启动脚本（Anaconda Python 3.13） |
| `VERSION.md` | 当前版本与修改点 |

## 文档

- [功能需求](./docs/SayClear-功能需求文档.md)
- [后端技术架构](./docs/SayClear-后端技术架构.md)
- [语音识别接入](./docs/SayClear-语音识别接入.md)
- [测试用例](./docs/SayClear-测试用例.md)
