# theNanGuos（南郭先生们）实施计划

## 1. 目标

实现一个 CLI MVP：用户输入音乐需求，系统通过 LangGraph 编排 4 agents + 3 tools，生成 `song_spec.json`、`score_plan.json`、`suno_request.json`，并调用 Suno `generate` 接口后轮询获取结果。

## 2. 实施阶段

### 阶段 1：项目骨架

产出：
- Python 包目录 `the_nanguos/`。
- CLI 入口。
- 输出目录约定。
- 基础配置读取。
- LangGraph 作为默认 agent 编排依赖。

任务：
1. 创建 `the_nanguos/__main__.py` 和 `the_nanguos/cli.py`。
2. 实现 `generate` 命令。
3. 支持参数：`--output-dir`、`--model`、`--no-submit`、`--poll-interval`、`--max-wait`。
4. 每次运行生成唯一 `request_id`。

验证：
- 运行 CLI 能创建输出目录。
- `--help` 输出可读。

### 阶段 2：Schema

产出：
- `SongSpec`
- `ScorePlan`
- `SunoRequest`
- `CollaborationLog`

任务：
1. 使用 Pydantic 定义 schema。
2. 定义 JSON 序列化和反序列化方法。
3. 为必填字段、枚举字段和默认值添加校验。

验证：
- 单元测试覆盖合法样例和缺失字段样例。
- 样例 JSON 能通过 schema 校验。

### 阶段 3：LLMClient 抽象

产出：
- `LLMClient` 接口。
- 至少一个真实或 mock 实现。

任务：
1. 定义 `generate_structured()` 风格接口。
2. Agents 只依赖 `LLMClient`。
3. 测试环境默认使用 mock client，避免测试依赖真实 LLM。

验证：
- mock client 能返回固定结构化数据。
- agents 测试不需要外部网络。

### 阶段 4：Agents

产出：
- `ConductorAgent`
- `LyricsAgent`
- `MusicPlannerAgent`
- `ArrangementAgent`

任务：
1. `ConductorAgent` 根据用户输入生成 `SongSpec`。
2. `LyricsAgent` 根据 `SongSpec` 生成分段歌词。
3. `MusicPlannerAgent` 生成结构、BPM、Key、和弦、旋律意图。
4. `ArrangementAgent` 生成配器、制作描述和 Suno style。
5. 所有 agent 输出必须通过 schema 或中间结构校验。

验证：
- 使用 mock LLM 测试四个 agents 的输入输出。
- 验证 agent 不直接写文件，不直接调用 Suno。

### 阶段 5：Tools

产出：
- `score_validator`
- `suno_request_builder`
- `suno_client`

任务：
1. `score_validator` 检查结构一致性和 Suno 请求前置条件。
2. `suno_request_builder` 从 `SongSpec` 和 `ScorePlan` 生成 `SunoRequest`。
3. `suno_client` 提交 `POST /api/v1/generate`。
4. `suno_client` 使用 `taskId` 轮询 `GET /api/v1/generate/record-info`。
5. API Key 只从 `SUNO_API_KEY` 读取。

验证：
- builder 测试覆盖歌词拼接、style 映射、negativeTags 映射。
- validator 测试覆盖缺失歌词、缺失 style、无效 instrumental/prompt 组合。
- suno_client 使用 mock HTTP 测试提交、成功轮询、失败轮询、超时。

### 阶段 6：LangGraph 编排

产出：
- `GraphState`
- `GenerateSongGraph`

任务：
1. 定义 `GraphState`，包含用户输入、输出目录、agent 结果、校验结果、Suno 状态和错误列表。
2. 实现 `init_run_node`，创建 `request_id`、输出目录和初始日志。
3. 实现 `conductor_node`、`lyrics_node`、`music_planner_node`、`arrangement_node`。
4. 实现 `build_score_plan_node`，写出 `score_plan.json`。
5. 实现 `validate_node` 和失败条件边。
6. 实现 `build_suno_request_node`，写出 `suno_request.json`。
7. 实现 `submit_or_skip_node`，根据 `--no-submit` 进入结束节点或提交节点。
8. 实现 `poll_suno_node`，轮询并更新 `collaboration_log.json`。
9. 在 `graphs/generate_song.py` 中编译 LangGraph graph，供 CLI 调用。

验证：
- `--no-submit` 端到端测试应生成 4 个 JSON 文件。
- mock Suno 端到端测试应记录 `taskId` 和最终 audio URL。
- 单元测试覆盖 `--no-submit` 条件边、校验失败条件边、轮询结束条件。

### 阶段 7：真实 Suno 联调

产出：
- 能真实提交 Suno 任务的 CLI。

任务：
1. 配置 `SUNO_API_KEY`。
2. 使用短提示词进行一次真实调用。
3. 观察轮询结果和错误格式。
4. 根据真实响应微调 `collaboration_log.json` 中的 Suno 结果结构。

验证：
- CLI 能拿到 Suno `taskId`。
- 轮询能结束于成功、失败或超时之一。
- 不在日志中出现 API Key。

## 3. 里程碑

### Milestone 1：离线 JSON 生成

完成标准：
- `--no-submit` 可运行。
- 生成 `song_spec.json`、`score_plan.json`、`suno_request.json`、`collaboration_log.json`。
- 单元测试覆盖 schema、builder、validator。

### Milestone 2：Mock API 闭环

完成标准：
- `suno_client` 使用 mock HTTP 完成提交和轮询。
- LangGraph graph 能记录任务状态和模拟音频 URL。

### Milestone 3：真实 API 闭环

完成标准：
- 配置 `SUNO_API_KEY` 后，CLI 可真实调用 Suno。
- 轮询获取最终状态。
- `collaboration_log.json` 记录最终结果或错误。

## 4. 风险与对策

- Suno `callBackUrl` 虽然不用但可能仍为必填：保留配置化占位 URL。
- Suno 响应字段可能与文档不同：真实联调阶段以响应样例更新解析逻辑。
- LLM 输出 JSON 不稳定：使用 Pydantic 校验和重试策略。
- 测试依赖外部服务不稳定：默认测试使用 mock LLM 和 mock HTTP。
- 轮询耗时较长：默认 `--max-wait 1200`，并允许 CLI 参数覆盖。

## 5. 不纳入 MVP

- Web UI。
- FastAPI callback。
- MIDI、MusicXML、ABC、demo.wav。
- 音频上传和 `upload-cover`。
- 多版本候选对比。
- 复杂人工编辑流程。
