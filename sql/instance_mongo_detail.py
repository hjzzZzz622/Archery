# -*- coding: UTF-8 -*-
import simplejson as json
from collections import defaultdict

from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse
from pymongo.errors import OperationFailure

from common.utils.extend_json_encoder import ExtendJSONEncoder
from sql.engines import get_engine
from sql.models import Instance, MongoInstanceMeta, MongoInstanceMetricSnapshot
from sql.utils.resource_group import user_instances


def _bytes_to_mb(value):
    try:
        return round(float(value or 0) / 1024 / 1024, 2)
    except Exception:
        return 0


def _bytes_to_gb(value):
    try:
        return round(float(value or 0) / 1024 / 1024 / 1024, 2)
    except Exception:
        return 0


def _ok_response(rows):
    return HttpResponse(
        json.dumps({"status": 0, "msg": "ok", "rows": rows}, cls=ExtendJSONEncoder),
        content_type="application/json",
    )


@permission_required("sql.menu_instance", raise_exception=True)
def detail_meta(request):
    """Mongo实例详情页基础信息"""
    instance_id = request.GET.get("instance_id")
    if not instance_id:
        return JsonResponse({"status": 1, "msg": "缺少参数instance_id", "data": {}})
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "data": {}}
        )

    meta = MongoInstanceMeta.objects.filter(instance=instance).first()
    metric = MongoInstanceMetricSnapshot.objects.filter(instance=instance).first()
    data = {
        "id": instance.id,
        "instance_name": instance.instance_name,
        "db_type": instance.db_type,
        "host": instance.host,
        "port": instance.port,
        "user": instance.user,
        "service_name": meta.set_name if meta else "",
        "owner": meta.business_owner if meta else "",
        "risk_count": metric.risk_count if metric else 0,
    }
    return JsonResponse({"status": 0, "msg": "ok", "data": data})


@permission_required("sql.menu_instance", raise_exception=True)
def database_list(request):
    """Mongo数据库列表 + 分片分布"""
    instance_id = request.GET.get("instance_id")
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "rows": []}
        )

    engine = get_engine(instance=instance)
    rows = []
    try:
        conn = engine.get_connection()
        db_names = engine.get_all_databases().rows
        ignore_dbs = {"admin", "local", "config"}
        visible_db_names = [name for name in db_names if name not in ignore_dbs]
        # 部分账号没有 listDatabases 权限，engine 会回退成 instance.db_name（常见是 admin）。
        # 这种情况下避免直接显示空列表，至少尝试展示实例配置中的 db_name。
        if (
            not visible_db_names
            and instance.db_name
            and instance.db_name not in ignore_dbs
        ):
            visible_db_names = [instance.db_name]
        for db_name in visible_db_names:
            db = conn[db_name]
            db_stats = db.command("dbStats")
            collections = [
                c for c in db.list_collection_names() if not c.startswith("system.")
            ]
            shard_stats = defaultdict(
                lambda: {
                    "table_count": 0,
                    "data_size": 0,
                    "storage_size": 0,
                    "index_size": 0,
                    "objects": 0,
                }
            )
            is_sharded = False
            for coll_name in collections:
                try:
                    coll_stats = db.command("collStats", coll_name)
                except Exception:
                    continue
                shards = coll_stats.get("shards") or {}
                if shards:
                    is_sharded = True
                    for shard_name, shard_detail in shards.items():
                        shard_stats[shard_name]["table_count"] += 1
                        shard_stats[shard_name]["data_size"] += shard_detail.get(
                            "size", 0
                        )
                        shard_stats[shard_name]["storage_size"] += shard_detail.get(
                            "storageSize", 0
                        )
                        shard_stats[shard_name]["index_size"] += shard_detail.get(
                            "totalIndexSize", 0
                        )
                        shard_stats[shard_name]["objects"] += shard_detail.get(
                            "count", 0
                        )
            shard_breakdown = []
            for shard_name, stats in shard_stats.items():
                avg_size = (
                    stats["data_size"] / stats["objects"] if stats["objects"] else 0
                )
                shard_breakdown.append(
                    {
                        "shard": shard_name,
                        "table_count": stats["table_count"],
                        "data_size_mb": _bytes_to_mb(stats["data_size"]),
                        "avg_obj_size_b": round(avg_size, 2),
                        "logical_size_mb": _bytes_to_mb(stats["data_size"]),
                        "index_count": 0,
                        "index_size_mb": _bytes_to_mb(stats["index_size"]),
                        "storage_size_mb": _bytes_to_mb(stats["storage_size"]),
                    }
                )
            rows.append(
                {
                    "shard": "是" if is_sharded else "否",
                    "db_name": db_name,
                    "table_count": db_stats.get("collections", 0),
                    "data_count": db_stats.get("objects", 0),
                    "avg_obj_size_b": round(float(db_stats.get("avgObjSize", 0)), 2),
                    "logical_size_mb": _bytes_to_mb(db_stats.get("dataSize", 0)),
                    "index_count": db_stats.get("indexes", 0),
                    "index_size_mb": _bytes_to_mb(db_stats.get("indexSize", 0)),
                    "storage_size_mb": _bytes_to_mb(db_stats.get("storageSize", 0)),
                    "shard_breakdown": shard_breakdown,
                }
            )
    except Exception as e:
        return JsonResponse({"status": 1, "msg": str(e), "rows": []})
    finally:
        engine.close()
    if not rows:
        return JsonResponse(
            {
                "status": 1,
                "msg": "未获取到可展示数据库。请检查实例账号是否具备listDatabases/dbStats权限，或在实例配置中补充默认数据库。",
                "rows": [],
            }
        )
    return _ok_response(rows)


@permission_required("sql.menu_instance", raise_exception=True)
def account_list(request):
    """Mongo账号列表（账号、库名、表名、权限）"""
    instance_id = request.GET.get("instance_id")
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "rows": []}
        )

    engine = get_engine(instance=instance)
    rows = []
    try:
        query_result = engine.get_instance_users_summary()
        if query_result.error:
            return JsonResponse({"status": 1, "msg": query_result.error, "rows": []})
        for row in query_result.rows:
            rows.append(
                {
                    "user": row.get("user", ""),
                    "db_name": row.get("db_name", ""),
                    "table_name": "*",
                    "privileges": ",".join(row.get("roles", [])),
                }
            )
    finally:
        engine.close()
    return _ok_response(rows)


@permission_required("sql.menu_instance", raise_exception=True)
def tablespace_list(request):
    """Mongo表空间列表 + 分片分布"""
    instance_id = request.GET.get("instance_id")
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "rows": []}
        )

    engine = get_engine(instance=instance)
    rows = []
    try:
        conn = engine.get_connection()
        ignore_dbs = {"admin", "local", "config"}
        db_names = [n for n in engine.get_all_databases().rows if n not in ignore_dbs]
        if not db_names and instance.db_name and instance.db_name not in ignore_dbs:
            db_names = [instance.db_name]
        for db_name in db_names:
            db = conn[db_name]
            for coll_name in db.list_collection_names():
                if coll_name.startswith("system."):
                    continue
                try:
                    stats = db.command("collStats", coll_name)
                except Exception:
                    continue
                shards = stats.get("shards") or {}
                shard_breakdown = []
                shard_storage_sizes = []
                for shard_name, shard_detail in shards.items():
                    shard_storage = shard_detail.get("storageSize", 0)
                    shard_storage_sizes.append(shard_storage)
                    shard_breakdown.append(
                        {
                            "shard": shard_name,
                            "data_count": shard_detail.get("count", 0),
                            "logical_size_mb": _bytes_to_mb(
                                shard_detail.get("size", 0)
                            ),
                            "avg_obj_size_b": round(
                                float(shard_detail.get("avgObjSize", 0)), 2
                            ),
                            "storage_size_mb": _bytes_to_mb(shard_storage),
                            "index_size_mb": _bytes_to_mb(
                                shard_detail.get("totalIndexSize", 0)
                            ),
                            "index_count": shard_detail.get("nindexes", 0),
                        }
                    )
                skewed = "否"
                if len(shard_storage_sizes) > 1:
                    avg_storage = sum(shard_storage_sizes) / len(shard_storage_sizes)
                    if (
                        avg_storage > 0
                        and (max(shard_storage_sizes) / avg_storage) > 1.5
                    ):
                        skewed = "是"
                rows.append(
                    {
                        "db_name": db_name,
                        "table_name": coll_name,
                        "engine": stats.get("wiredTiger", {}) and "wiredTiger" or "",
                        "is_sharded": "是" if bool(shards) else "否",
                        "data_count": stats.get("count", 0),
                        "chunk_count": len(shards) if shards else 0,
                        "logical_size_mb": _bytes_to_mb(stats.get("size", 0)),
                        "avg_obj_size_b": round(float(stats.get("avgObjSize", 0)), 2),
                        "storage_size_mb": _bytes_to_mb(stats.get("storageSize", 0)),
                        "index_size_mb": _bytes_to_mb(stats.get("totalIndexSize", 0)),
                        "index_count": stats.get("nindexes", 0),
                        "is_skewed": skewed,
                        "shard_breakdown": shard_breakdown,
                    }
                )
    except Exception as e:
        return JsonResponse({"status": 1, "msg": str(e), "rows": []})
    finally:
        engine.close()
    if not rows:
        return JsonResponse(
            {
                "status": 1,
                "msg": "未获取到表空间数据。请检查实例账号权限（listDatabases/collStats）或默认数据库配置。",
                "rows": [],
            }
        )
    return _ok_response(rows)


@permission_required("sql.menu_instance", raise_exception=True)
def risk_list(request):
    """Mongo隐患列表"""
    instance_id = request.GET.get("instance_id")
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "rows": []}
        )

    meta = MongoInstanceMeta.objects.filter(instance=instance).first()
    metric = MongoInstanceMetricSnapshot.objects.filter(instance=instance).first()
    rows = [
        {
            "service_name": meta.set_name if meta else instance.instance_name,
            "risk_type": "综合巡检",
            "owner": meta.business_owner if meta else "",
            "count": metric.risk_count if metric else 0,
        }
    ]
    return _ok_response(rows)


@permission_required("sql.menu_instance", raise_exception=True)
def connection_list(request):
    """Mongo连接信息"""
    instance_id = request.GET.get("instance_id")
    try:
        instance = user_instances(request.user, db_type=["mongo"]).get(id=instance_id)
    except Instance.DoesNotExist:
        return JsonResponse(
            {"status": 1, "msg": "你所在组未关联该Mongo实例", "data": {}}
        )

    engine = get_engine(instance=instance)
    try:
        conn = engine.get_connection()
        server_status = conn.admin.command("serverStatus")
        conn_info = server_status.get("connections", {})
        current = conn_info.get("current", 0)
        available = conn_info.get("available", 0)
        idle = max(available, 0)
        usage = 0
        total_capacity = current + available
        if total_capacity > 0:
            usage = round(current * 100.0 / total_capacity, 2)

        ip_counter = defaultdict(int)
        warning_msg = ""
        # Atlas 部分规格不支持 $currentOp allUsers 参数，先尝试全量，失败再降级为当前用户视角。
        try:
            with conn.admin.aggregate(
                [{"$currentOp": {"allUsers": True, "idleConnections": True}}]
            ) as cursor:
                for op in cursor:
                    client = op.get("client", "")
                    if not client:
                        continue
                    ip = client.split(":")[0]
                    ip_counter[ip] += 1
        except OperationFailure:
            try:
                with conn.admin.aggregate(
                    [{"$currentOp": {"idleConnections": True}}]
                ) as cursor:
                    for op in cursor:
                        client = op.get("client", "")
                        if not client:
                            continue
                        ip = client.split(":")[0]
                        ip_counter[ip] += 1
                warning_msg = (
                    "当前Atlas规格限制allUsers参数，客户端IP为当前账号可见范围。"
                )
            except Exception:
                warning_msg = "当前Atlas规格限制$currentOp，无法获取客户端IP明细。"

        data = {
            "summary": {
                "current_connections": current,
                "idle_connections": idle,
                "usage_rate": usage,
            },
            "rows": [
                {"client_ip": ip, "connections": cnt}
                for ip, cnt in sorted(
                    ip_counter.items(), key=lambda item: item[1], reverse=True
                )
            ],
            "warning_msg": warning_msg,
        }
        return JsonResponse({"status": 0, "msg": "ok", "data": data})
    except Exception as e:
        return JsonResponse({"status": 1, "msg": str(e), "data": {}})
    finally:
        engine.close()
