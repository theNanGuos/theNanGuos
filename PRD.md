# theNanGuos（南郭先生们）需求设计文档

## 1. 项目定位

theNanGuos，中文名“南郭先生们”，是一个面向音乐生成的多智能体 CLI 系统。用户用自然语言描述想要的歌曲后，系统由 4 个智能体协作生成结构化创作计划，并把计划转换成可直接调用 Suno `generate` 接口的请求。

项目重点不是自研音频渲染、MIDI 编曲或完整 DAW 流程，而是展示多智能体如何把模糊音乐需求拆解为可校验、可追踪、可提交给外部音乐生成 API 的结构化产物。

## 2. 核心目标

- 支持用户通过 CLI 输入自然语言音乐需求。
- 使用 4 个 agents 完成需求解析、歌词生成、音乐规划和编曲风格生成。
- 使用 3 个 tools 完成结构校验、Suno 请求构造和 Suno API 调用。
- 输出 3 个核心 JSON 产物：`song_spec.json`、`score_plan.json`、`suno_request.json`。
- 输出 `collaboration_log.json` 作为协作、调试和运行状态日志。
- 真实调用 Suno `POST /api/v1/generate` 接口，并通过轮询获取生成结果。

## 3. 非目标

- MVP 不做 Web UI。
- MVP 不实现公网 callback 服务。
- MVP 不生成 MIDI、MusicXML、ABC notation 或 demo 音频。
- MVP 不走 Suno `upload-cover`、参考音频上传或音频改编接口。
- MVP 不追求严格逐音符乐谱表达。
- MVP 不实现 DAW、混音、母带或音频轨道编辑功能。

## 4. 主要用户流程

1. 用户在 CLI 输入需求，例如：
   “生成一首 90 秒中文 lo-fi pop，温暖、适合夜晚学习，有女声。”
2. `ConductorAgent` 解析用户需求，生成标准化 `song_spec.json`。
3. `LyricsAgent` 根据主题、语言、情绪和曲式生成分段歌词。
4. `MusicPlannerAgent` 生成曲式、BPM、Key、和弦、旋律意图。
5. `ArrangementAgent` 生成配器、制作风格和 Suno `style` 描述。
6. 系统整合生成 `score_plan.json`。
7. `score_validator` 校验结构完整性和 Suno 请求前置条件。
8. `suno_request_builder` 生成可直接提交的 `suno_request.json`。
9. `suno_client` 读取 `suno_request.json`，调用 Suno `generate` 接口。
10. 系统从返回结果中记录 `taskId`，并轮询 `record-info` 获取任务状态。
11. `collaboration_log.json` 记录 agent 协作步骤、校验结果、Suno 提交状态、轮询状态和最终音频 URL 或错误。

## 5. Agent 与 Tool 设计

### 5.1 Agents

#### ConductorAgent

负责理解用户输入、标准化创作需求、调度其他 agents，并整合最终结果。

输入：用户自然语言需求、默认配置。  
输出：`SongSpec`、任务计划、整合后的协作记录。

#### LyricsAgent

负责生成歌词和段落文本，不直接处理 Suno API 字段。

输入：`SongSpec` 中的主题、语言、情绪、曲式、人声设定。  
输出：按段落组织的歌词内容。

#### MusicPlannerAgent

负责生成音乐结构，不追求严格逐音符乐谱。

输入：`SongSpec`、歌词段落。  
输出：曲式、BPM、Key、和弦进行、旋律意图、段落时长建议。

#### ArrangementAgent

负责生成编曲和制作层描述，并为 Suno `style` 字段提供主要内容。

输入：`SongSpec`、歌词、音乐结构。  
输出：乐器配置、段落编曲策略、整体制作风格、Suno style 描述。

### 5.2 Tools

#### score_validator

确定性校验工具，负责检查 JSON 结构和关键业务规则，不调用 LLM。

检查范围：
- `song_spec.structure` 与 `score_plan.sections` 是否一致。
- 有人声时，主要段落是否包含歌词。
- `suno_request.customMode=true` 时，`prompt`、`style`、`title` 是否存在。
- `instrumental=false` 时，`prompt` 是否非空。
- `duration_seconds`、`bpm`、`model` 等字段是否落在可接受范围内。

#### suno_request_builder

确定性转换工具，负责把 `song_spec.json` 和 `score_plan.json` 转换成 Suno `generate` 请求体。

约束：
- 不重新生成音乐创意。
- 不覆盖 agents 已经生成的歌词、曲式和风格设定。
- 只做字段映射、格式拼接、默认值填充和请求体校验。

#### suno_client

负责真实调用 Suno API，并通过轮询获取结果。

约束：
- API Key 只从环境变量 `SUNO_API_KEY` 读取。
- 提交接口为 `POST /api/v1/generate`。
- 查询接口为 `GET /api/v1/generate/record-info?taskId=...`。
- 默认每 30 秒轮询一次。
- 默认最长等待 20 分钟。
- 不依赖公网 callback。

## 6. 核心实体

### UserRequest

用户原始输入。MVP 不单独落盘，但在 `collaboration_log.json` 中记录摘要。

### SongSpec

创意需求层实体，描述用户想要什么。

### ScorePlan

音乐结构层实体，描述歌曲如何组织。它不是严格乐谱，而是能支撑 Suno 请求构造的结构化创作计划。

### SunoRequest

外部 API 请求层实体，必须能直接作为 Suno `generate` 请求体提交。

### CollaborationLog

运行日志实体，用于测试、调试、课程展示和追踪 Suno 任务状态。

## 7. 数据结构

### 7.1 song_spec.json

```json
{
  "title": "Night Study",
  "language": "zh",
  "genre": "lo-fi pop",
  "mood": ["warm", "calm", "focused"],
  "duration_seconds": 90,
  "vocal": {
    "enabled": true,
    "gender": "female"
  },
  "tempo": {
    "bpm": 78,
    "feel": "laid-back"
  },
  "key": "C major",
  "structure": ["intro", "verse", "chorus", "outro"],
  "constraints": {
    "explicit": false,
    "avoid": ["heavy metal", "aggressive drums", "harsh vocal"]
  }
}
```

### 7.2 score_plan.json

```json
{
  "sections": [
    {
      "name": "verse",
      "duration_seconds": 28,
      "lyrics": [
        "夜色落在书页旁",
        "微光陪我慢慢想"
      ],
      "chords": ["Cmaj7", "Am7", "Dm7", "G7"],
      "melody_intent": "gentle descending phrases, narrow vocal range",
      "arrangement": "soft electric piano, light vinyl texture, minimal drums"
    }
  ],
  "global_arrangement": {
    "instruments": ["soft female vocal", "electric piano", "subtle drums", "warm bass"],
    "mix_style": "intimate, mellow, soft reverb",
    "dynamic_curve": "quiet intro, fuller chorus, gentle outro",
    "suno_style": "Chinese lo-fi pop, warm soft female vocal, mellow electric piano, gentle drums, warm bass, intimate room reverb, calm night study mood"
  }
}
```

### 7.3 suno_request.json

```json
{
  "customMode": true,
  "instrumental": false,
  "model": "V5",
  "callBackUrl": "https://example.com/suno/callback",
  "prompt": "[Verse]\n夜色落在书页旁\n微光陪我慢慢想\n\n[Chorus]\n...",
  "style": "Chinese lo-fi pop, warm soft female vocal, mellow electric piano, gentle drums, warm bass, intimate room reverb, calm night study mood",
  "title": "Night Study",
  "vocalGender": "f",
  "negativeTags": "heavy metal, aggressive drums, harsh vocal"
}
```

说明：
- `callBackUrl` 是 Suno API 的兼容字段。MVP 不依赖 callback，但仍保留合法 URL。
- `prompt` 承载歌词和段落标签。
- `style` 承载风格、配器、唱法和制作描述。
- `duration_seconds` 只作为创作约束，不保证 Suno 严格生成指定时长。

### 7.4 collaboration_log.json

```json
{
  "request_id": "uuid",
  "user_request_summary": "90秒中文lo-fi pop，温暖，夜晚学习，女声",
  "artifacts": {
    "song_spec": "song_spec.json",
    "score_plan": "score_plan.json",
    "suno_request": "suno_request.json"
  },
  "steps": [
    {
      "actor": "ConductorAgent",
      "action": "parse_user_request",
      "output": "song_spec.json"
    }
  ],
  "validation": {
    "passed": true,
    "warnings": []
  },
  "suno": {
    "submitted": true,
    "task_id": "task_abc123",
    "polling": {
      "interval_seconds": 30,
      "max_wait_seconds": 1200,
      "attempts": 6
    },
    "status": "success",
    "audio_results": [
      {
        "audio_id": "audio_001",
        "title": "Night Study",
        "audio_url": "https://example.com/audio.mp3",
        "duration_seconds": 92
      }
    ],
    "error": null
  }
}
```

`collaboration_log.json` 不属于核心创作产物，但属于 MVP 必要运行产物。它用于调试、测试、作业展示和追踪真实 API 调用结果。

## 8. 核心业务规则

1. 每次生成任务必须产出 `song_spec.json`、`score_plan.json`、`suno_request.json` 和 `collaboration_log.json`。
2. `ConductorAgent` 不直接生成最终 Suno 请求，必须先生成 `SongSpec` 并调用其他 agents。
3. `LyricsAgent` 只负责歌词和段落，不负责 Suno API 请求字段。
4. `MusicPlannerAgent` 只生成曲式、BPM、Key、和弦、旋律意图，不生成 MIDI 或逐音符乐谱。
5. `ArrangementAgent` 负责将音乐计划转换成制作层描述，并提供 Suno `style` 内容。
6. `score_validator` 是确定性工具，不调用 LLM。
7. `suno_request_builder` 只能基于 `song_spec.json` 和 `score_plan.json` 构造请求。
8. `suno_client` 调用 API 前必须读取 `suno_request.json`。
9. `SUNO_API_KEY` 不得写入任何 JSON 文件、日志或源码。
10. Suno 提交成功后必须把 `taskId` 写入 `collaboration_log.json`。
11. 结果获取方式固定为轮询，不实现公网 callback。
12. 轮询超时或 API 失败时，必须把错误状态写入 `collaboration_log.json`。

## 9. CLI MVP 范围

### 必做

- CLI 接收用户自然语言需求。
- 使用 4 agents + 3 tools 的固定协作结构。
- 生成三个核心 JSON 文件。
- 生成协作和运行日志。
- 真实调用 Suno `generate` 接口。
- 使用 `taskId` 轮询查询结果。
- 支持 `--no-submit` 只生成 JSON，不调用 Suno，便于测试。

### 推荐做

- 支持 `--output-dir` 指定输出目录。
- 支持 `--model` 指定 Suno 模型，默认 `V5`。
- 支持 `--poll-interval`，默认 30 秒。
- 支持 `--max-wait`，默认 1200 秒。

### 可选扩展

- Web UI。
- FastAPI 服务。
- 多版本候选方案对比。
- 人类在中途修改歌词、风格或配器。
- 可视化 agent 协作流程图。

## 10. 默认技术假设

- 语言：Python 3.11+。
- 交互方式：CLI first。
- Agent 编排：LangGraph first，使用固定生成图承载 agents、tools 和条件边。
- Schema：Pydantic。
- 存储：文件系统，每次请求一个 `outputs/<request_id>/`。
- LLM 访问：通过 `LLMClient` 抽象，避免把供应商逻辑写进 agents。
- Suno API Key：通过 `SUNO_API_KEY` 环境变量读取。
- Suno 结果获取：通过 `record-info` 轮询，不依赖 callback。
- 网络超时、API 错误和轮询超时必须显式记录。

## 11. 推荐 CLI

```bash
python -m the_nanguos generate "生成一首90秒中文lo-fi pop，温暖，适合夜晚学习，女声"
```

可选参数：

```bash
--output-dir outputs/demo-001
--model V5
--no-submit
--poll-interval 30
--max-wait 1200
```

## 12. 项目亮点

- 用固定的 4 agents + 3 tools 展示多智能体分工协作。
- 用结构化 JSON 保留创意、歌词、曲式、和弦、编曲和 API 请求之间的映射。
- 通过 `score_validator` 把 LLM 输出转成可校验产物。
- 真实调用 Suno API，形成从用户需求到生成结果的闭环。
- 使用 `collaboration_log.json` 记录协作过程、调试信息和轮询状态，便于课程展示。

## 13. 一句话介绍

theNanGuos（南郭先生们）是一个 CLI 多智能体音乐生成系统：它让 4 个 agents 协作把自然语言音乐需求转成结构化创作计划，再生成可直接调用 Suno `generate` 接口的请求，并通过轮询拿到生成结果。
