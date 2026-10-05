# 002 CRM Integration 回滚说明

本迁移只对 `crm_data` 做增量变更，不修改 `market_source`。部署前必须先用
`mysqldump --single-transaction --routines --triggers crm_data` 生成完整备份。

应用回滚优先切回部署前的 FastAPI 代码和 Nginx 配置。新增表和可空列保留，旧版本会忽略它们，
避免在故障窗口内执行破坏性 DDL。只有确认不再需要迁移后，才可在维护窗口从备份恢复完整
`crm_data`；恢复前先停止写流量，并再次备份当前状态。

回滚核验：主应用 `/health/live` 正常、旧 CRM 入口恢复、`crm_data` 核心公司/联系人/Deal 数量与
备份记录一致。迁移标识为 `002_crm_integration`。
