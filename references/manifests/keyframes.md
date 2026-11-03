# Manifest 分册 · 关键帧

> 由 manifests.md 物理拆分：本分册只含具体 JSON schema；设计原则、统一目录、状态失效拓扑与「不进入 JSON 的内容」保留在 [../manifests.md](../manifests.md)。
> 需要哪个 schema 读对应小节（read_reference 可按阶段/条件路由到本节），不整篇通读本分册。

### keyframe_manifest_ep_N.json

保存分镜确认后生成的剧情关键帧职责、文件与验收状态：

```json
{
  "episode_id": "ep_1",
  "revision": 1,
  "project_data_card_revision": 1,
  "script_contract": "episodes/ep_1/01_剧本/script_contract_ep_1.json",
  "storyboard_manifest": "episodes/ep_1/02_分镜/storyboard_ep_1.json",
  "project_data_card": "00_制作控制/project_data_card.json",
  "keyframes": [
    {
      "keyframe_id": "KF001", "segment_id": "SEG001", "shot_id": "E01S01-SHOT001", "role": "highlight", "highlight_index": 1, "data_card_revision": 1,
      "asset_refs": ["CHR001_v01", "SCN001_v01", "PROP001_v01"], "state_refs": ["CHR001:STATE001"], "information_triggers": ["space_anchor"],
      "narrative_state": "", "character_state": {}, "prop_state": {}, "scene_and_light": {}, "camera_and_composition": {}, "continuity_from": "",
      "prompt_path": "episodes/ep_1/03_资产/提示词/提示词_KF001_SEG001_highlight-1_v01_ep_1.md",
      "file": "episodes/ep_1/03_资产/关键帧/关键帧_KF001_SEG001_highlight-1_v01_ep_1.png",
      "tool": "image_edit", "model": "", "version": "v01", "status": "draft|reviewed|approved|rejected|superseded", "used_by_segments": ["SEG001"]
    }
  ]
}
```

- `storyboard_manifest` 必须引用当前已确认分镜；`segment_id`、`shot_id` 和 `used_by_segments` 必须与分镜中的真实片段和镜头一致。
- `role` 固定为 `highlight`，`highlight_index` 是同一 SEG 内从 `1` 开始的高光序号。关键帧只锁定剧情峰值，不承担生成式首帧或尾帧职责。
- 同一视频片段采用的高光关键帧必须与 `storyboard_ep_N.json` 的高光需求一致；片段首尾连续性由真实 FRM、连续性账本和 `SEAMxxx` 负责。
- `tool/model/version/status` 记录 `keyframes.md` 的实际生成结果；视频输入关系记录 `video.md` 的实际调用结果。
- 视频生成后的 `FRMxxx` 抽帧不能回写覆盖 `KFxxx`；偏差登记并按内容质量门处理：关键偏差阻断合格接受，非关键偏差须明确接受；只有用户主动要求修改并重新确认后才返修分镜、关键帧或视频。

