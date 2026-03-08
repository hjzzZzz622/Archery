#!/usr/bin/env python
import os
import sys

# 使用 pymysql 替代 mysqlclient（requirements-minimal.txt 时无需编译）
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "archery.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
