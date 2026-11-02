# lint 检查合同 · planning 阶段

> 由 build_lint_contract.py 从实际 STAGE_CHECKS 与共享调用图生成；按需读取。
> 只证明结构、来源、算术、依赖与技术合同；内容须按观看顺序独立审校。

运行：`python scripts/drama_lint.py <skill-root> --project-root <project> --stage planning`。

| 检查码 | 级别 | 查什么 | 来源 |
|---|---|---|---|
| `combined_story_outline_reference_invalid` | error | project_script_manifest.global_story_and_episode_outline 必须指向 01_剧本/剧本_全局设定与分集总纲.md。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 149） |
| `combined_story_outline_section_missing` | error | 合并剧本文档缺少“{heading}”章节。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 143） |
| `combined_story_outline_unreadable` | error | 合并剧本文档无法读取：{exc} | `lint_checks.stages.check_stage_artifacts`（64–173，触发 139） |
| `file_missing` | error | 缺少流程所需文件。 | `lint_checks.common.load_json`（22–30，触发 27） |
| `highlight_ledger_invalid` | error | script_contract.highlight_ledger 必须是数组。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 165） |
| `json_invalid` | error | JSON 无法读取或解析，后续关系无法确认：{exc} | `lint_checks.common.load_json`（22–30，触发 29） |
| `required_artifact_missing` | error | 缺少当前阶段所需产物。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 132） |
| `source_event_uncovered` | error | {eid} 缺必要事实摘要 | `content_first.source_index_from_contract`（33–91，触发 73） |
| `source_event_uncovered` | error | {scene.get('scene_id')} 需 events 源索引（不设数量） | `content_first.source_index_from_contract`（33–91，触发 59） |
| `source_event_uncovered` | error | 事件索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 63） |
| `source_line_uncovered` | error | speech_lines 必须是数组，可空 | `content_first.source_index_from_contract`（33–91，触发 77） |
| `source_line_uncovered` | error | 台词索引必须是对象 | `content_first.source_index_from_contract`（33–91，触发 81） |
| `source_revision_mismatch` | error | script contract 缺 scenes | `content_first.source_index_from_contract`（33–91，触发 37） |
| `source_revision_mismatch` | error | {eid} source_excerpt 不在对应场次原文 | `content_first.source_index_from_contract`（33–91，触发 71） |
| `source_revision_mismatch` | error | {lid} 台词不在对应源场次 | `content_first.source_index_from_contract`（33–91，触发 89） |
| `source_revision_mismatch` | error | {sid} 需唯一场次标题以定位源原文 | `content_first.source_index_from_contract`（33–91，触发 49） |
| `source_revision_mismatch` | error | 源剧本正文 SHA 不符。 | `lint_checks.stages.check_stage_artifacts`（64–173，触发 169） |
| `source_revision_mismatch` | error | 源场次 ID 必须唯一且非空 | `content_first.source_index_from_contract`（33–91，触发 44） |
| `timeline_id_duplicate` | error | 无效/重复 line_id {lid} | `content_first.source_index_from_contract`（33–91，触发 87） |
| `timeline_id_duplicate` | error | 无效/重复源事件 {eid} | `content_first.source_index_from_contract`（33–91，触发 69） |
