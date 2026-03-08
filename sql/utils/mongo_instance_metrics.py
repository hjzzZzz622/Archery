import logging
from datetime import datetime
from typing import Dict, Optional, Set

from django.utils import timezone

from sql.engines import get_engine
from sql.models import Instance, MongoInstanceMetricSnapshot

logger = logging.getLogger("default")


def _parse_shard_hosts(shards: list) -> Set[str]:
    hosts: Set[str] = set()
    for shard in shards:
        host_value = shard.get("host", "")
        # examples:
        # rs0/10.0.0.1:27017,10.0.0.2:27017
        # 10.0.0.3:27017
        host_part = host_value.split("/", 1)[-1]
        for host in host_part.split(","):
            host = host.strip()
            if host:
                hosts.add(host)
    return hosts


def _extract_balancer_info(conn) -> (str, Optional[datetime]):
    balancer_status = ""
    balancer_at = None

    try:
        status_result = conn.admin.command({"balancerStatus": 1})
        mode = status_result.get("mode")
        in_round = status_result.get("inBalancerRound")
        if mode:
            balancer_status = str(mode)
        elif in_round is not None:
            balancer_status = "running" if in_round else "idle"
    except Exception as exc:
        logger.debug(f"failed to query balancerStatus: {exc}")

    try:
        last_log = conn["config"]["actionlog"].find_one(
            {"what": {"$regex": "balancer", "$options": "i"}},
            sort=[("time", -1)],
        )
        if last_log and last_log.get("time"):
            balancer_at = last_log["time"]
    except Exception as exc:
        logger.debug(f"failed to query config.actionlog: {exc}")

    if not balancer_status:
        balancer_status = "unknown"
    if balancer_status != "unknown" and balancer_at is None:
        balancer_at = timezone.now()
    return balancer_status, balancer_at


def collect_mongo_instance_metrics(instance: Instance) -> Dict:
    metrics = {
        "proxy_count": 0,
        "mongod_count": 0,
        "shard_count": 0,
        "database_count": 0,
        "table_count": 0,
        "status": "error",
        "risk_count": 0,
        "balancer_status": "unknown",
        "balancer_at": None,
        "error_message": "",
    }
    try:
        snapshot, _ = MongoInstanceMetricSnapshot.objects.get_or_create(
            instance=instance
        )
    except Exception as exc:
        logger.warning(
            f"collect mongo metrics init failed for {instance.instance_name}: {exc}"
        )
        metrics["error_message"] = str(exc)
        return metrics

    metrics["risk_count"] = snapshot.risk_count
    engine = None

    try:
        engine = get_engine(instance=instance)
        conn = engine.get_connection()
        hello = conn.admin.command("hello")
        is_mongos = hello.get("msg") == "isdbgrid"
        metrics["proxy_count"] = 1 if is_mongos else 0

        shards = []
        try:
            shards = conn.admin.command({"listShards": 1}).get("shards", [])
        except Exception as exc:
            logger.debug(f"listShards failed for {instance.instance_name}: {exc}")

        metrics["shard_count"] = len(shards)
        metrics["mongod_count"] = len(_parse_shard_hosts(shards))

        db_names = conn.list_database_names()
        metrics["database_count"] = len(db_names)

        table_count = 0
        # avoid heavy scans on huge clusters
        for db_name in db_names[:200]:
            table_count += len(conn[db_name].list_collection_names())
        metrics["table_count"] = table_count

        balancer_status, balancer_at = _extract_balancer_info(conn)
        metrics["balancer_status"] = balancer_status
        metrics["balancer_at"] = balancer_at
        metrics["status"] = "ok"
    except Exception as exc:
        logger.warning(
            f"collect mongo metrics failed for {instance.instance_name}: {exc}"
        )
        metrics["error_message"] = str(exc)
    finally:
        if engine:
            engine.close()

    for field, value in metrics.items():
        setattr(snapshot, field, value)
    snapshot.save()
    return metrics
