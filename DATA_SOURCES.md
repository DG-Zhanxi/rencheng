# 数据来源与许可

代码按根目录MIT许可证发布。第三方数据与依赖分别遵循原许可，MIT不覆盖它们。

## OpenStreetMap

`data/roads.geojson`、`buildings.geojson`、`pois.json`及`data/raw/shenzhen.osm`来自OpenStreetMap贡献者。© OpenStreetMap contributors，数据库采用[ODbL 1.0](https://www.openstreetmap.org/copyright)。派生地理数据库继续适用ODbL署名与相应共享义务。

采集范围、日期、坐标系、原始文件摘要见`data/geography_manifest.json`。956条道路、758个建筑轮廓；计算子图4861个节点、6876条有向边。建筑展示使用高度/楼层属性，缺少属性时采用展示默认高度。

## 国内灾情资料

公开资料来源及链接见`data/sources.json`，涵盖深圳交通运输局、市政府、水务局和部门回应。`events.json`保留结构化事实与简短引句；公开仓库不包含抓取的完整网页、长篇原文摘录或私人业务数据库。原始政府及媒体内容的权利归原发布者，按来源链接阅读。

## 实验数据

`experiment_runs.json`与`experiment_summary.json`为本项目运行产生的指标，按CC BY 4.0开放，署名RenCheng contributors。许可：https://creativecommons.org/licenses/by/4.0/

实验使用真实现状道路几何，需求、车辆、阻断按固定种子生成。30个种子×3种扰动×5种策略，共450次。历史灾情资料与现状路网的时间属性分别保留。

## 第三方软件与模型

依赖清单见requirements.txt和frontend/package-lock.json，各包保留其原许可。Kimi模型通过在线API调用，仓库不包含模型权重及密钥。CodeArts辅助开发的证据状态模块位于vendor/codearts，集成后经过边界测试和未来事件过滤回归验证。
