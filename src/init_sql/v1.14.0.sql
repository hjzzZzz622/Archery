-- Mongo实例静态扩展信息
CREATE TABLE IF NOT EXISTS `sql_mongo_instance_meta` (
  `id` int NOT NULL AUTO_INCREMENT,
  `instance_id` int NOT NULL,
  `region` varchar(64) NOT NULL DEFAULT '' COMMENT 'region名称',
  `set_name` varchar(64) NOT NULL DEFAULT '' COMMENT 'set名称',
  `l5` varchar(64) NOT NULL DEFAULT '' COMMENT 'L5',
  `vip` varchar(128) NOT NULL DEFAULT '' COMMENT 'vip',
  `business_owner` varchar(64) NOT NULL DEFAULT '' COMMENT '业务责任人',
  `importance` varchar(32) NOT NULL DEFAULT '' COMMENT '重要性',
  `env_type` varchar(32) NOT NULL DEFAULT '' COMMENT '环境类型',
  `proxy_version` varchar(64) NOT NULL DEFAULT '' COMMENT 'proxy版本',
  `mongod_version` varchar(64) NOT NULL DEFAULT '' COMMENT 'mongod版本',
  `cpu_cores` int DEFAULT NULL COMMENT 'CPU/核',
  `memory_gb` int DEFAULT NULL COMMENT '内存/GB',
  `disk_gb` int DEFAULT NULL COMMENT '磁盘/GB',
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uidx_mongo_meta_instance` (`instance_id`),
  CONSTRAINT `fk_mongo_meta_instance` FOREIGN KEY (`instance_id`) REFERENCES `sql_instance` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mongo实例静态信息';

-- Mongo实例动态指标快照
CREATE TABLE IF NOT EXISTS `sql_mongo_instance_metric_snapshot` (
  `id` int NOT NULL AUTO_INCREMENT,
  `instance_id` int NOT NULL,
  `proxy_count` int NOT NULL DEFAULT 0 COMMENT 'proxy数量',
  `mongod_count` int NOT NULL DEFAULT 0 COMMENT 'mongod数量',
  `shard_count` int NOT NULL DEFAULT 0 COMMENT '分片数',
  `database_count` int NOT NULL DEFAULT 0 COMMENT '库数量',
  `table_count` int NOT NULL DEFAULT 0 COMMENT '表数量',
  `status` varchar(20) NOT NULL DEFAULT 'unknown' COMMENT '状态',
  `risk_count` int NOT NULL DEFAULT 0 COMMENT '隐患个数',
  `balancer_status` varchar(64) NOT NULL DEFAULT '' COMMENT '调匀器状态',
  `balancer_at` datetime(6) DEFAULT NULL COMMENT '调匀时间点',
  `collected_at` datetime(6) NOT NULL COMMENT '采集时间',
  `error_message` longtext COMMENT '错误信息',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uidx_mongo_metric_instance` (`instance_id`),
  CONSTRAINT `fk_mongo_metric_instance` FOREIGN KEY (`instance_id`) REFERENCES `sql_instance` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mongo实例动态指标快照';
