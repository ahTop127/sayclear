# SayClear — 语音识别接入

> 只写 **Google Cloud Speech-to-Text** 怎么接到第一期链路。  
> **不是**产品开发：没有 Mac 客户端业务代码、没有录音/填入实现、没有脚手架。  
> 产品行为以 [`SayClear-功能需求文档.md`](./SayClear-功能需求文档.md) 为准；逻辑后端以 [`SayClear-后端技术架构.md`](./SayClear-后端技术架构.md) 为准。

---

## 1. 已定

| 项 | 第一期约定 |
|---|---|
| 识别服务 | **Google Cloud Speech-to-Text**（Cloud Speech-to-Text） |
| **项目 ID** | **`sayclear`**（环境变量 `GOOGLE_CLOUD_PROJECT`）。若控制台显示的「项目名称」和「项目 ID」不同，以 **ID** 为准；用户给的是 `sayclear`。这不是密钥。 |
| 职责 | 只做 **音频 → 转写文本**。不清洗、不纠错、不分点 |
| 整理 | **DeepSeek V4 Flash**（wintoken.dev，`deepseek-v4-flash-0731`）。另一次 LLM 调用；不把音频丢给整理 |
| 调用时机 | 用户按 ⌘ 或点 OK **结束录音之后**，把**整段**音频送去识别一次 |
| 不做 | 实时流式（边说边出字）、录音中预览逐字稿、半句入框 |

---

## 2. 第一期推荐：V2 + Chirp 3 + 同步 Recognize

Google 现在主推 **Speech-to-Text API V2** 与 **Chirp 3**（`chirp_3`）。第一期选这一套，不选 V1。

| 选项 | 第一期 | 理由 |
|---|---|---|
| **V2 + Chirp 3** | **采用** | 当前多语言模型；简体中文 `cmn-Hans-CN` 与英文 `en-US` 均为 GA；适合短句口述 + 中英夹杂 |
| V1 / 旧 `default` 模型 | 不用 | 多语言与句内夹杂弱于 Chirp；不是当前推荐入口 |
| **Recognize（同步）** | **采用** | 官方说明适合 **约 1 分钟以内**的整段音频；对应「说完再出字」 |
| StreamingRecognize | 不用 | 用户流程不是边说边出字 |
| BatchRecognize | 不用 | 面向长音频，通常要先上传 Cloud Storage；第一期短口述不必 |

区域：Chirp 3 目前在 **`us`、`eu` 多区域**可用（GA）。请求要打到对应区域端点（形如 `us-speech.googleapis.com`），不要默认当成 `global`。识别器可用默认资源名 `projects/{项目ID}/locations/{区域}/recognizers/_`，第一期不必先在控制台建一个 Recognizer。

---

## 3. 控制台要开什么（你来操作）

我这边登不了你的 Google 账号。请在 [Google Cloud 控制台](https://console.cloud.google.com/) 自己完成：

1. **建或选一个项目**，并**开通结算**（Speech-to-Text 要绑定账单；未超额免费额度前通常不收费，但仍须开通）。
2. **启用 API**：搜索并启用 **Cloud Speech-to-Text API**（服务名 `speech.googleapis.com`）。V1 / V2 共用这一条，不必另开「V2 API」。
3. **建服务账号**：IAM → 服务账号 → 创建。角色给 **Cloud Speech Client**（`roles/speech.client`），够调用识别即可，不要给 Owner。
4. **下载 JSON 密钥**：该服务账号 → 密钥 → 添加密钥 → JSON。文件只放本机，**不要提交进 git、不要贴进文档或聊天**。
5. **项目 ID 已定为 `sayclear`。** 还要记住选用的区域（建议先用 `us`）。以后客户端用它们拼识别器路径。

---

## 3.1 对照官方 Client Libraries 教程（你贴的那页）

官方 [Client libraries](https://docs.cloud.google.com/speech-to-text/docs/client-libraries) 这条路**可以当本地试调用用**，和第一期「走 Speech-to-Text **V2**」是同一条 API。但有几处**不要原样照抄示例代码**：

| 教程示例 | SayClear 第一期 |
|---|---|
| `google-cloud-speech` + `SpeechClient()`（V2） | 可以：这是 V2 的正规客户端，不是 API key 那种 raw HTTP |
| 鉴权：`gcloud auth application-default login`（ADC） | **本地试调可以用。** 以后桌面产品仍建议服务账号 JSON，不要依赖你的个人 Google 登录 |
| `GOOGLE_CLOUD_PROJECT` | **需要**（拼 `projects/{ID}/locations/.../recognizers/_`） |
| `locations/global` + `model="long"` + `language_codes=["en-US"]` | **不要照抄。** 第一期用区域 `us`、模型 `chirp_3`、语言 `cmn-Hans-CN` + `en-US` |
| API key | **这条教程用不上。** Client library 走 ADC，不会读你控制台里的 API key |

结论：按「V2 客户端 + ADC」来，**是**；按示例里的 `long` / 纯英文 / `global` / 只用 API key，**不是**。

本地若要按教程试通一次，你手头需要的是下面第 3.2 节，**不是**再发一把 API key。

### 3.2 你现在手头还缺什么

**已经有、但这条路用不上：** 控制台 API key。V2 `SpeechClient` 不会用它。不要再发 API key。

**已经有：** 项目 ID **`sayclear`**（不是密钥）。本地会话里可 `export GOOGLE_CLOUD_PROJECT=sayclear`。

**必须有（控制台，尚未确认本机已完成）：**

1. 该项目已 **开通结算**
2. 该项目已启用 **Cloud Speech-to-Text API**

**本地试调（按官方教程走 ADC 时）还要（本机此前检查：没有 gcloud、没有 ADC、没有 `google-cloud-speech`）：**

3. 安装 [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)，执行 `gcloud init`
4. 执行 `gcloud auth application-default login`，用浏览器登录**有权访问该项目**的 Google 账号
5. Python 环境里 `pip install --upgrade google-cloud-speech`
6. 一段本地音频文件（教程是读文件字节再 `recognize`）

**做 SayClear 产品时再备（现在可以还没有）：** 服务账号 + JSON 密钥（角色 Cloud Speech Client）。个人 `gcloud login` 只适合你自己电脑上试 API，不能当安装给别人的 App 的鉴权。

**现在不必有：** Mac 客户端、录音功能、整理用的 LLM key。未开始产品开发。

---

## 4. 凭据：服务账号 JSON，不要 API key

| 形态 | 第一期桌面 |
|---|---|
| **服务账号 JSON** | **采用。** V2 走 OAuth / Application Default Credentials（ADC），官方也按 ADC 鉴权，不是浏览器那种 API key。JSON 放本机（钥匙串或本地配置路径），用完由客户端换短期 access token 再调 HTTPS。 |
| API key | **不适合。** Cloud STT 文档按 ADC，不把 API key 当正路；权限也粗。 |
| 装进安装包的公司密钥 | 第一期不要。架构已写：本机自备密钥；若以后产品方统一付费，再考虑薄转发。 |

仓库已加 `.gitignore`，忽略常见密钥文件名。本地请至少保证：

- `*service-account*.json`、`*-credentials.json`、`secrets/`、`.env` 不会被 `git add`
- 失败短句、日志、悬浮层里都不出现密钥或项目号以外的敏感内容

---

## 5. 识别形态：整段结束后一次性识别

对应需求：再按 ⌘ 或点 OK → 只显示 Thinking → 整段完成后再填入。

- 录音过程中音频**只留在本机内存**，不边录边推流。
- **结束录音且未点 X** 之后，才把这一整段发给 `Recognize`。
- 点 X：不发识别。
- 不要用 StreamingRecognize 做「边说边出字」；需求不要求预览逐字稿，也禁止半句入框。

同步 Recognize 适合大约一分钟内的口述。需求里「极长口述是否截断」仍待确认——未拍板前，过长按失败或请用户分段说，不要默默截成成功。

---

## 6. 音频（待客户端录音时再对齐）

官方建议：能选采样率时用 **16000 Hz**；无文件头的 PCM 用 **LINEAR16**（16-bit 小端 PCM）。第一期建议按下面对齐，**实现录音时再核一次**，这里不写客户端代码。

| 项 | 建议 |
|---|---|
| 采样率 | 16 kHz（麦克风若已是别的速率，优先原样送，不要随便重采样） |
| 编码 | LINEAR16；单声道 |
| 送法 | 请求里内联整段 `content`（不必先传到 Cloud Storage） |
| 无文件头 PCM | 配置里显式写编码 / 采样率 / 声道；有 WAV/FLAC 头时也可用自动探测编码 |

---

## 7. 中英混合（建议，须真实口述验收）

产品要同一段里中文 + 英文术语 / 代码词（如「把这个 button 改小」）。

**建议配置（Chirp 3 / V2）：**

| 项 | 建议值 |
|---|---|
| 模型 | `chirp_3` |
| 语言 | `language_codes`: `["cmn-Hans-CN", "en-US"]` |
| 备选 | 若夹杂明显变差，再试 `["auto"]`（语言无关转写，官方说偏「主导语言」） |
| 不要默认用 | V1 的 `languageCode` + `alternativeLanguageCodes`：那是从候选里**选一种主导语言**，不是为句内中英夹杂设计的 |

说明：

- Chirp 3 文档写的是：可 `language_codes=["auto"]` 做语言无关转写；也可列出预期 locale（如中英），把模型资源收窄到这几种，一般比全自动更稳。
- 官方「多语言识别」（最多三种、选最佳拟合）主要针对 `latest_long` / `short` / `telephony`，且偏**整段选一种语言**。第一期中英夹杂不要靠那套当主方案。
- Chirp 3 文案也常说转写「主导语言」。句内中英夹杂（代码词、专有名词）**没有单独的产品级 SLA**。

**须用真实中英口述验收**，例如需求场景 C：「把这个 button 改小一点，再把 padding 调一下，那个 hover 状态的颜色太暗了。」通过标准：转写里 `button` / `padding` / `hover` 仍在，且中文句子可读。若英文词被吃掉、译成中文、或整段被判成纯英文，再在 `["cmn-Hans-CN", "en-US"]` 与 `["auto"]` 之间改，而不是改整理模型来「猜」识别。

识别只保证尽量听成字；专有词原样保留、改口、分点仍由**整理那一次 LLM** 负责。

---

## 8. 失败：不要把半成品交给整理

Google 这一步要么交出**非空转写**，要么当本次识别失败。对不上需求里的两类：

| 情况 | 产品失败类（需求 §8.4） | 整理模块 |
|---|---|---|
| 空结果、过短、无语音、几乎静音 | **没录到声音** | **不调用** |
| API 错误、鉴权失败、超时、区域/配额错误、无法解析的响应 | **整理失败**（需求把识别失败也归在这类；用户文案不要写接口名） | **不调用** |
| 转写有字 | — | **才**发起一次整理 |

不要：把空串、错误 JSON、半截转写送给整理；不要在识别失败时用「猜测正文」填入。Thinking 期间超时：中止识别请求，丢弃迟到响应。

---

## 9. 和文本整理的边界

```
录音结束 → Google：音频 → 转写 →（仅成功）→ 一次 LLM 整理 → 锁定意图正文 → 填入
```

- Google **只**负责语音转文本。
- 整理 **只**吃转写文本，不吃音频；厂商已定为 DeepSeek V4 Flash（wintoken.dev）。
- 识别成功但整理失败：转写也不得填入。

---

## 10. 当前接入状态（已实测）

1. 项目 ID **`sayclear`**，ADC 已登录，Speech-to-Text REST Recognize 已通；麦克风测试通过。  
2. 产品配置仍用 Chirp 3 + `us` + 中英 locale（连通测试曾用过 `global` / `long` 英文样例）。  
3. 整理已在 wintoken.dev 上通；密钥在 `.env`。  
4. **未开始把识别和整理串进 SayClear 产品。**

本地试调用 ADC + REST；发给别人安装的 App 再改服务账号 JSON。
