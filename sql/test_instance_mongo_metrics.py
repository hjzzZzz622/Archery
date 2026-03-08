from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from sql.models import Instance, MongoInstanceMeta, MongoInstanceMetricSnapshot
from sql.utils.mongo_instance_metrics import collect_mongo_instance_metrics

User = get_user_model()


class TestMongoInstanceListAndRefresh(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="mongo_admin",
            display="Mongo管理员",
            is_active=True,
            is_superuser=True,
            is_staff=True,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.instance = Instance.objects.create(
            instance_name="mongo_ins_1",
            type="master",
            db_type="mongo",
            mode="cluster",
            host="mongodb+srv://cluster0.example.mongodb.net/",
            port=0,
            user="u",
            password="p",
            db_name="admin",
        )
        MongoInstanceMeta.objects.create(
            instance=self.instance,
            region="ap-beijing",
            set_name="setA",
            l5="l5-x",
            vip="10.0.0.10",
            business_owner="alice",
            importance="high",
            env_type="prod",
        )
        MongoInstanceMetricSnapshot.objects.create(
            instance=self.instance,
            proxy_count=2,
            mongod_count=6,
            shard_count=3,
            database_count=10,
            table_count=200,
            status="ok",
            risk_count=1,
            balancer_status="running",
            balancer_at=timezone.now(),
        )

    def test_instance_list_contains_mongo_fields(self):
        resp = self.client.post(
            "/instance/list/",
            data={
                "limit": 20,
                "offset": 0,
                "db_type": "mongo",
                "sortName": "id",
                "sortOrder": "asc",
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["total"], 1)
        row = payload["rows"][0]
        self.assertEqual(row["region"], "ap-beijing")
        self.assertEqual(row["proxy_count"], 2)
        self.assertEqual(row["mongod_count"], 6)
        self.assertEqual(row["shard_count"], 3)
        self.assertEqual(row["database_count"], 10)
        self.assertEqual(row["table_count"], 200)
        self.assertEqual(row["status"], "ok")

    @patch("sql.instance.collect_mongo_instance_metrics")
    def test_refresh_endpoint(self, mocked_collect):
        mocked_collect.return_value = {
            "status": "ok",
            "proxy_count": 1,
            "mongod_count": 3,
            "shard_count": 1,
            "database_count": 5,
            "table_count": 20,
            "risk_count": 0,
            "balancer_status": "idle",
            "balancer_at": None,
            "error_message": "",
        }
        resp = self.client.post(
            "/instance/mongo/refresh/", data={"instance_id": self.instance.id}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], 0)
        mocked_collect.assert_called_once()


class TestCollectMongoInstanceMetrics(TestCase):
    def setUp(self):
        self.instance = Instance.objects.create(
            instance_name="mongo_ins_collect",
            type="master",
            db_type="mongo",
            mode="cluster",
            host="mongodb+srv://cluster0.example.mongodb.net/",
            port=0,
            user="u",
            password="p",
            db_name="admin",
        )

    @patch("sql.utils.mongo_instance_metrics.get_engine")
    def test_collect_metrics_failed(self, mocked_get_engine):
        mocked_get_engine.side_effect = RuntimeError("connect failed")
        metrics = collect_mongo_instance_metrics(self.instance)
        self.assertEqual(metrics["status"], "error")
        self.assertIn("connect failed", metrics["error_message"])
