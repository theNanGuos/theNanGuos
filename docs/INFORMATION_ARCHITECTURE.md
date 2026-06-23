# theNanGuos（南郭先生们）信息架构文档

## 1. 信息架构目标

信息架构的目标是明确系统中有哪些信息对象、它们由谁产生、如何流转、如何落盘，以及哪些字段属于核心业务合同。

MVP 的信息架构围绕四个输出文件：

- `song_spec.json`
- `score_plan.json`
- `suno_request.json`
- `collaboration_log.json`

## 2. 信息对象总览

```text
UserRequest
  -> SongSpec
  -> ScorePlan
  -> SunoRequest
  -> SunoTaskStatus
  -> CollaborationLog
```

## 3. 信息对象定义

### UserRequest

来源：CLI 用户输入。  
是否落盘：不单独落盘。  
用途：作为 `ConductorAgent` 的输入，并在 `collaboration_log.json` 中记录摘要。

关键字段：
- `raw_text`
- `received_at`
- `request_id`

### SongSpec

来源：`ConductorAgent`。  
落盘文件：`song_spec.json`。  
用途：标准化用户创作需求，作为后续 agents 的共享输入。

关键字段：
- `title`
- `language`
- `genre`
- `mood`
- `duration_seconds`
- `vocal`
- `tempo`
- `key`
- `structure`
- `constraints`

### ScorePlan

来源：`LyricsAgent`、`MusicPlannerAgent`、`ArrangementAgent` 的整合结果。  
落盘文件：`score_plan.json`。  
用途：描述歌曲结构、歌词、和弦、旋律意图和编曲意图。

关键字段：
- `sections`
- `sections[].name`
- `sections[].duration_seconds`
- `sections[].lyrics`
- `sections[].chords`
- `sections[].melody_intent`
- `sections[].arrangement`
- `global_arrangement`
- `global_arrangement.suno_style`

### SunoRequest

来源：`suno_request_builder`。  
落盘文件：`suno_request.json`。  
用途：作为 Suno `POST /api/v1/generate` 的请求体。

关键字段：
- `customMode`
- `instrumental`
- `model`
- `callBackUrl`
- `prompt`
- `style`
- `title`
- `vocalGender`
- `negativeTags`

### SunoTaskStatus

来源：`suno_client` 提交和轮询结果。  
是否落盘：不单独落盘，写入 `collaboration_log.json` 的 `suno` 字段。  
用途：记录真实 API 调用状态。

关键字段：
- `submitted`
- `task_id`
- `polling`
- `status`
- `audio_results`
- `error`

### CollaborationLog

来源：LangGraph 节点持续写入。  
落盘文件：`collaboration_log.json`。  
用途：调试、测试、课程展示、API 结果追踪。

关键字段：
- `request_id`
- `user_request_summary`
- `artifacts`
- `steps`
- `validation`
- `suno`

## 4. 信息流转

```text
CLI input
  -> UserRequest
  -> GenerateSongGraph
  -> ConductorAgent
  -> song_spec.json
  -> LyricsAgent
  -> MusicPlannerAgent
  -> ArrangementAgent
  -> score_plan.json
  -> score_validator
  -> suno_request_builder
  -> suno_request.json
  -> suno_client
  -> collaboration_log.json
```

## 5. 文件组织

每次运行创建一个独立输出目录：

```text
outputs/<request_id>/
  song_spec.json
  score_plan.json
  suno_request.json
  collaboration_log.json
```

`request_id` 应唯一，建议使用时间戳加短随机 ID，例如：

```text
20260623-223000-a1b2c3
```

## 6. 字段映射规则

### SongSpec 到 ScorePlan

- `structure` 决定 `score_plan.sections` 的段落集合。
- `duration_seconds` 分配为各段建议时长。
- `language` 决定歌词语言。
- `genre`、`mood`、`tempo`、`key` 影响和弦、旋律意图和编曲描述。
- `vocal.enabled=false` 时，`score_plan.sections[].lyrics` 可以为空。

### ScorePlan 到 SunoRequest

- `sections[].lyrics` 拼接为 `prompt`。
- `sections[].name` 转换为 `[Verse]`、`[Chorus]` 等段落标签。
- `global_arrangement.suno_style` 映射为 `style`。
- `song_spec.title` 映射为 `title`。
- `song_spec.vocal.gender` 映射为 `vocalGender`。
- `song_spec.constraints.avoid` 映射为 `negativeTags`。

## 7. 校验规则

### SongSpec 校验

- `title` 不为空。
- `language` 使用稳定代码，例如 `zh`、`en`。
- `duration_seconds` 大于 0。
- `tempo.bpm` 大于 0。
- `structure` 至少包含一个主要段落。

### ScorePlan 校验

- `sections` 不为空。
- `sections[].name` 不为空。
- 有人声时，主要段落必须有歌词。
- `sections[].chords` 可以为空，但如果存在必须是字符串数组。
- `global_arrangement.suno_style` 不为空。

### SunoRequest 校验

- `customMode` 固定为 `true`。
- `instrumental=false` 时，`prompt` 必须非空。
- `model` 默认 `V5`。
- `callBackUrl` 必须是合法 URL。
- `style` 和 `title` 必须非空。

## 8. 日志信息分层

`collaboration_log.json` 分为四类信息：

1. 产物索引：记录本次运行生成了哪些文件。
2. 协作步骤：记录每个 agent/tool 的动作和输出。
3. 校验结果：记录 validator 的通过状态、错误和警告。
4. Suno 状态：记录提交、taskId、轮询次数、最终结果或错误。

日志中不得包含：

- `SUNO_API_KEY`
- Authorization header
- 完整环境变量
- 用户本地敏感路径之外的无关系统信息

## 9. CLI 信息展示

CLI 输出应保持简洁：

```text
Request ID: 20260623-223000-a1b2c3
Output: outputs/20260623-223000-a1b2c3
Generated: song_spec.json, score_plan.json, suno_request.json
Suno task: task_abc123
Polling: success
Audio: https://example.com/audio.mp3
```

失败时展示：

```text
Request ID: 20260623-223000-a1b2c3
Output: outputs/20260623-223000-a1b2c3
Status: failed
Reason: Suno polling timeout after 1200 seconds
See: collaboration_log.json
```
