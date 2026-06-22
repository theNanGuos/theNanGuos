# theNanGuos（南郭先生们）架构文档

## 1. 架构目标

theNanGuos 是一个 CLI first 的多智能体音乐生成系统。架构目标是用清晰、可测试、可追踪的流程，把用户自然语言音乐需求转换为 Suno `generate` API 请求，并轮询获取生成结果。

MVP 使用 LangGraph 搭建固定生成图。CLI 只负责接收参数和展示结果，核心流程由 `GenerateSongGraph` 编排：

```text
CLI
  -> GenerateSongGraph
  -> conductor_node
  -> lyrics_node
  -> music_planner_node
  -> arrangement_node
  -> validate_node
  -> build_suno_request_node
  -> submit_or_skip_node
  -> poll_suno_node
  -> outputs/<request_id>/
```

## 2. 模块划分

```text
the_nanguos/
  __main__.py
  cli.py

  agents/
    conductor.py
    lyrics.py
    music_planner.py
    arrangement.py

  tools/
    score_validator.py
    suno_request_builder.py
    suno_client.py

  schemas/
    song_spec.py
    score_plan.py
    suno_request.py
    collaboration_log.py

  graphs/
    generate_song.py
    state.py

  llm/
    client.py

outputs/
  <request_id>/
    song_spec.json
    score_plan.json
    suno_request.json
    collaboration_log.json
```

## 3. 核心组件职责

### CLI 层

`cli.py` 负责解析命令行参数，并调用 `GenerateSongGraph`。CLI 不直接调用 agents、tools 或 Suno API。

建议命令：

```bash
python -m the_nanguos generate "生成一首90秒中文lo-fi pop，温暖，适合夜晚学习，女声"
```

### LangGraph 编排层

`GenerateSongGraph` 是 MVP 的业务编排入口，负责定义 graph state、节点和边。CLI 调用 graph，不直接串联 agents。

Graph 节点：

1. `init_run_node`：创建 `request_id`、输出目录和初始 `CollaborationLog`。
2. `conductor_node`：调用 `ConductorAgent` 生成 `SongSpec`。
3. `lyrics_node`：调用 `LyricsAgent` 生成歌词。
4. `music_planner_node`：调用 `MusicPlannerAgent` 生成音乐结构。
5. `arrangement_node`：调用 `ArrangementAgent` 生成编曲和 Suno style。
6. `build_score_plan_node`：整合 agent 输出并写出 `score_plan.json`。
7. `validate_node`：运行 `score_validator`。
8. `build_suno_request_node`：运行 `suno_request_builder` 并写出 `suno_request.json`。
9. `submit_or_skip_node`：根据 `--no-submit` 决定结束或调用 Suno。
10. `poll_suno_node`：轮询 Suno `record-info` 并更新 `collaboration_log.json`。

Graph 条件边：

- `validate_node` 失败时直接进入 `fail_node`。
- `submit_or_skip_node` 在 `--no-submit=true` 时进入 `end_node`。
- `poll_suno_node` 在成功、失败或超时后进入 `end_node`。

Graph state 至少包含：

- `request_id`
- `user_request`
- `output_dir`
- `song_spec`
- `lyrics_result`
- `music_plan_result`
- `arrangement_result`
- `score_plan`
- `suno_request`
- `validation_result`
- `suno_task_id`
- `suno_result`
- `errors`
- `collaboration_log`

### Agents 层

Agents 可以调用 LLM，但必须输出符合 schema 的结构化结果。

- `ConductorAgent`：解析用户需求，生成 `SongSpec`。
- `LyricsAgent`：生成分段歌词。
- `MusicPlannerAgent`：生成曲式、BPM、Key、和弦、旋律意图。
- `ArrangementAgent`：生成配器、制作描述和 Suno style。

### Tools 层

Tools 不调用 LLM，负责确定性操作。

- `score_validator`：校验结构和业务规则。
- `suno_request_builder`：构造 Suno 请求体。
- `suno_client`：提交请求、轮询状态、解析结果。

### Schemas 层

Schemas 使用 Pydantic 表达 JSON 合同，避免字段漂移。

核心 schema：

- `SongSpec`
- `ScorePlan`
- `SunoRequest`
- `CollaborationLog`

### LLM 层

`LLMClient` 是供应商抽象层。Agents 只依赖 `LLMClient` 接口，不直接依赖具体模型供应商。

## 4. 数据流

```text
UserRequest
  -> SongSpec
  -> Lyrics + MusicPlan + Arrangement
  -> ScorePlan
  -> SunoRequest
  -> Suno taskId
  -> Suno record-info result
  -> CollaborationLog
```

LangGraph 状态流：

```text
GraphState
  -> init_run_node
  -> conductor_node
  -> lyrics_node
  -> music_planner_node
  -> arrangement_node
  -> build_score_plan_node
  -> validate_node
  -> build_suno_request_node
  -> submit_or_skip_node
  -> poll_suno_node
```

文件输出：

```text
outputs/<request_id>/song_spec.json
outputs/<request_id>/score_plan.json
outputs/<request_id>/suno_request.json
outputs/<request_id>/collaboration_log.json
```

## 5. Suno 集成

MVP 只使用 Suno 普通音乐生成流程：

- 提交：`POST /api/v1/generate`
- 查询：`GET /api/v1/generate/record-info?taskId=...`

不使用：

- `upload-cover`
- 音频上传
- MIDI 生成
- callback server

虽然 `callBackUrl` 是请求字段，MVP 不依赖它。系统通过轮询拿结果。

## 6. 错误处理

错误必须写入 `collaboration_log.json`：

- LLM 输出无法解析。
- schema 校验失败。
- `score_validator` 发现缺失字段。
- `SUNO_API_KEY` 未配置。
- Suno 提交失败。
- 轮询超时。
- Suno 返回失败状态。

CLI 应返回非零退出码，方便测试和脚本集成。

## 7. 安全约束

- 不把 `SUNO_API_KEY` 写入源码、JSON 文件或日志。
- 不记录 Authorization header。
- 不在错误信息中泄露环境变量值。
- 用户输入只作为 LLM prompt 和结构化字段来源，不拼接执行 shell 命令。

## 8. 扩展方向

MVP 稳定后可以扩展：

- Web UI。
- FastAPI 后端。
- 多候选版本生成。
- 用户中途编辑歌词或风格。
- Agent 协作流程可视化。
- 使用 LangGraph 条件边增加自动返工流程。
