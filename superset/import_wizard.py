"""
Financial Dashboard Import — v4
Compatible with: apache/superset:latest (5.x)

Viz type map (verified for Superset 5.x):
  big_number_total          → KPI big number
  pie                       → Pie / Donut
  echarts_timeseries_line   → Time-series line
  echarts_timeseries_bar    → Time-series bar  (x_axis = datetime col, NO groupby)
  echarts_timeseries_bar    → Categorical bar  (x_axis = dimension col, NO groupby*)
  table                     → Data table
  funnel_chart              → Funnel
  echarts_radar             → Radar

* KEY RULE: echarts_timeseries_bar uses x_axis as the sole dimension.
  NEVER put the same column in both x_axis and groupby → causes duplicate label error.
  For categorical bars, set x_axis = dimension column and omit groupby entirely.
"""

import json
import os
import re
import time
import uuid

import yaml

# ─────────────────────────────────────────────────────────────
#  SCHEMA
# ─────────────────────────────────────────────────────────────

METRICS = [
    {"metric_name": "count", "expression": "COUNT(*)"},
    {"metric_name": "sum_amount", "expression": "SUM(transaction_amount)"},
    {"metric_name": "avg_amount", "expression": "AVG(transaction_amount)"},
    {"metric_name": "max_amount", "expression": "MAX(transaction_amount)"},
    {"metric_name": "min_amount", "expression": "MIN(transaction_amount)"},
    {"metric_name": "sum_fee", "expression": "SUM(fee)"},
    {"metric_name": "avg_fee", "expression": "AVG(fee)"},
    {"metric_name": "avg_risk_score", "expression": "AVG(risk_score)"},
    {"metric_name": "max_risk_score", "expression": "MAX(risk_score)"},
    {"metric_name": "count_vip", "expression": "SUM(is_vip)"},
    {
        "metric_name": "avg_balance_delta",
        "expression": "AVG(balance_after - balance_before)",
    },
    {
        "metric_name": "sum_balance_delta",
        "expression": "SUM(balance_after - balance_before)",
    },
]

COLUMNS = [
    {"column_name": "transaction_id", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "account_number", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "customer_name", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "transaction_amount", "type": "FLOAT", "is_dttm": False},
    {"column_name": "currency", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "transaction_type", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "transaction_time", "type": "TIMESTAMP", "is_dttm": True},
    {"column_name": "merchant_name", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "city", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "country", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "phone_number", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "payment_method", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "ip_address", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "is_vip", "type": "TINYINT", "is_dttm": False},
    {"column_name": "category", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "status", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "fee", "type": "FLOAT", "is_dttm": False},
    {"column_name": "balance_before", "type": "FLOAT", "is_dttm": False},
    {"column_name": "balance_after", "type": "FLOAT", "is_dttm": False},
    {"column_name": "risk_score", "type": "FLOAT", "is_dttm": False},
    {"column_name": "device_type", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "browser_agent", "type": "VARCHAR", "is_dttm": False},
    {"column_name": "source_db_updated_at", "type": "TIMESTAMP", "is_dttm": True},
]


# ─────────────────────────────────────────────────────────────
#  CHARTS — 15 charts, all verified for Superset 5.x
#
#  Categorical bar pattern (5.x):
#    viz_type = "echarts_timeseries_bar"
#    x_axis   = <dimension column>      ← the only dimension
#    metrics  = [...]
#    NO groupby key at all
#    granularity_sqla = None (empty)
#    time_range = "No filter"           ← avoids time parsing on non-time col
# ─────────────────────────────────────────────────────────────

SLICES = [
    # ── Row 1: 5 KPI big numbers ──────────────────────────────
    {
        "slice_name": "💰 Total Transaction Volume",
        "viz_type": "big_number_total",
        "params": json.dumps(
            {
                "metric": "sum_amount",
                "subheader": "EGP · Last 24h",
                "y_axis_format": ",.0f",
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
            }
        ),
    },
    {
        "slice_name": "📊 Total Operations Count",
        "viz_type": "big_number_total",
        "params": json.dumps(
            {
                "metric": "count",
                "subheader": "Transactions · Last 24h",
                "y_axis_format": ",.0f",
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
            }
        ),
    },
    {
        "slice_name": "💳 Average Transaction Amount",
        "viz_type": "big_number_total",
        "params": json.dumps(
            {
                "metric": "avg_amount",
                "subheader": "EGP per Operation",
                "y_axis_format": ",.2f",
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
            }
        ),
    },
    {
        "slice_name": "⚠️ Average Risk Score",
        "viz_type": "big_number_total",
        "params": json.dumps(
            {
                "metric": "avg_risk_score",
                "subheader": "Range: 0 → 1",
                "y_axis_format": ".3f",
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
            }
        ),
    },
    {
        "slice_name": "💸 Total Fees Collected",
        "viz_type": "big_number_total",
        "params": json.dumps(
            {
                "metric": "sum_fee",
                "subheader": "EGP · Last 24h",
                "y_axis_format": ",.0f",
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
            }
        ),
    },
    # ── Row 2: Donuts ─────────────────────────────────────────
    {
        "slice_name": "Transaction Type Distribution",
        "viz_type": "pie",
        "params": json.dumps(
            {
                "metric": "count",
                "groupby": ["transaction_type"],
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
                "donut": True,
                "show_labels": True,
                "show_legend": True,
                "label_type": "key_percent",
                "innerRadius": 40,
                "outerRadius": 70,
            }
        ),
    },
    {
        "slice_name": "Transaction Status Distribution",
        "viz_type": "pie",
        "params": json.dumps(
            {
                "metric": "count",
                "groupby": ["status"],
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
                "donut": True,
                "show_labels": True,
                "show_legend": True,
                "label_type": "key_percent",
                "innerRadius": 40,
                "outerRadius": 70,
            }
        ),
    },
    # ── Row 3: Time-series lines ──────────────────────────────
    {
        "slice_name": "Transaction Amount Over Time",
        "viz_type": "echarts_timeseries_line",
        "params": json.dumps(
            {
                "metrics": ["sum_amount"],
                "groupby": [],
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
                "x_axis": "transaction_time",
                "series_type": "line",
                "smooth": True,
                "area": False,
                "show_value": False,
                "zoomable": True,
                "rich_tooltip": True,
                "y_axis_format": ",.0f",
            }
        ),
    },
    {
        "slice_name": "Cumulative Volume Growth",
        "viz_type": "echarts_timeseries_line",
        "params": json.dumps(
            {
                "metrics": ["sum_amount"],
                "groupby": [],
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
                "x_axis": "transaction_time",
                "series_type": "line",
                "area": True,
                "smooth": True,
                "rolling_type": "sum",
                "zoomable": True,
                "show_value": False,
                "y_axis_format": ",.0f",
            }
        ),
    },
    # ── Row 4: Categorical bars ───────────────────────────────
    #  PATTERN: x_axis = dimension, metrics = [...], NO groupby
    #  granularity_sqla = None, time_range = "No filter"
    {
        "slice_name": "Top 10 Merchants by Volume",
        "viz_type": "echarts_timeseries_bar",
        "params": json.dumps(
            {
                "metrics": ["sum_amount"],
                "x_axis": "merchant_name",
                "granularity_sqla": None,
                "time_range": "No filter",
                "row_limit": 10,
                "order_desc": True,
                "show_legend": False,
                "show_value": True,
                "y_axis_format": ",.0f",
                "xAxisTitle": "Merchant",
                "yAxisTitle": "Total EGP",
                "orientation": "horizontal",
            }
        ),
    },
    {
        "slice_name": "Transactions by Category",
        "viz_type": "echarts_timeseries_bar",
        "params": json.dumps(
            {
                "metrics": ["count"],
                "x_axis": "category",
                "granularity_sqla": None,
                "time_range": "No filter",
                "row_limit": 15,
                "order_desc": True,
                "show_legend": False,
                "show_value": True,
                "xAxisTitle": "Category",
                "yAxisTitle": "Count",
            }
        ),
    },
    # ── Row 5: Time-series bar + payment categorical ──────────
    {
        "slice_name": "Daily Transaction Count",
        "viz_type": "echarts_timeseries_bar",
        "params": json.dumps(
            {
                "metrics": ["count"],
                "granularity_sqla": "transaction_time",
                "time_range": "Last 7 days",
                "x_axis": "transaction_time",
                "show_legend": False,
                "zoomable": True,
                "show_value": False,
                "rich_tooltip": True,
            }
        ),
    },
    {
        "slice_name": "Payment Method Breakdown",
        "viz_type": "echarts_timeseries_bar",
        "params": json.dumps(
            {
                "metrics": ["count", "sum_amount"],
                "x_axis": "payment_method",
                "granularity_sqla": None,
                "time_range": "No filter",
                "row_limit": 10,
                "order_desc": True,
                "show_legend": True,
                "show_value": False,
                "xAxisTitle": "Payment Method",
            }
        ),
    },
    # ── Row 6: Risk bar + High-risk table ─────────────────────
    {
        "slice_name": "Avg Risk Score by Category",
        "viz_type": "echarts_timeseries_bar",
        "params": json.dumps(
            {
                "metrics": ["avg_risk_score"],
                "x_axis": "category",
                "granularity_sqla": None,
                "time_range": "No filter",
                "row_limit": 15,
                "order_desc": True,
                "show_legend": False,
                "show_value": True,
                "y_axis_format": ".3f",
                "xAxisTitle": "Category",
                "yAxisTitle": "Avg Risk Score",
            }
        ),
    },
    {
        "slice_name": "🚨 High Risk Transactions",
        "viz_type": "table",
        "params": json.dumps(
            {
                "query_mode": "aggregate",
                "groupby": [
                    "transaction_id",
                    "customer_name",
                    "category",
                    "status",
                    "merchant_name",
                    "city",
                    "payment_method",
                    "device_type",
                ],
                "metrics": ["sum_amount", "avg_risk_score", "count"],
                "time_range": "Last day",
                "granularity_sqla": "transaction_time",
                "row_limit": 200,
                "order_desc": True,
                "adhoc_filters": [
                    {
                        "expressionType": "SIMPLE",
                        "subject": "risk_score",
                        "operator": ">=",
                        "comparator": "0.7",
                        "clause": "WHERE",
                    }
                ],
                "include_search": True,
                "page_length": 25,
                "show_cell_bars": True,
                "align_pn": True,
                "color_pn": True,
                "column_config": {
                    "avg_risk_score": {
                        "colorPositiveNegative": True,
                        "d3NumberFormat": ".3f",
                    },
                    "sum_amount": {
                        "d3NumberFormat": ",.0f",
                    },
                },
            }
        ),
    },
]


# ─────────────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────────────


def build_position(ids: dict) -> dict:
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"children": ["GRID_ID"], "id": "ROOT_ID", "type": "ROOT"},
        "GRID_ID": {
            "children": ["ROW-1", "ROW-2", "ROW-3", "ROW-4", "ROW-5", "ROW-6"],
            "id": "GRID_ID",
            "type": "GRID",
        },
    }

    def add(idx, width, height):
        cid = ids[idx]
        key = f"CHART-{cid}"
        pos[key] = {
            "id": key,
            "meta": {"chartId": cid, "width": width, "height": height},
            "type": "CHART",
        }
        return key

    # Row 1 — 5 KPIs  (4 × 5 = 20 cols; last one gets 4)
    r1 = [add(i, 4, 22) for i in range(1, 6)]
    pos["ROW-1"] = {
        "children": r1,
        "id": "ROW-1",
        "type": "ROW",
        "meta": {"background": "BACKGROUND_TRANSPARENT"},
    }

    # Rows 2-6 — 2 × 12
    rows = [
        (6, 7, 50, 50),
        (8, 9, 55, 55),
        (10, 11, 55, 55),
        (12, 13, 55, 55),
        (14, 15, 55, 80),
    ]
    for row_num, (a, b, ha, hb) in enumerate(rows, start=2):
        ca, cb = add(a, 12, ha), add(b, 12, hb)
        pos[f"ROW-{row_num}"] = {
            "children": [ca, cb],
            "id": f"ROW-{row_num}",
            "type": "ROW",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
    return pos


# ─────────────────────────────────────────────────────────────
#  DASHBOARD METADATA  (colors + 6 native filters)
# ─────────────────────────────────────────────────────────────


def build_metadata(dataset_id: int) -> str:
    meta = {
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "refresh_frequency": 5,
        "default_filters": "{}",
        "color_scheme": "supersetColors",
        "label_colors": {
            "completed": "#4CAF50",
            "COMPLETED": "#4CAF50",
            "pending": "#FF9800",
            "PENDING": "#FF9800",
            "failed": "#F44336",
            "FAILED": "#F44336",
            "purchase": "#2196F3",
            "transfer": "#00BCD4",
            "withdrawal": "#FF5722",
            "refund": "#9C27B0",
        },
        "native_filter_configuration": [
            {
                "id": "NATIVE_FILTER-time",
                "name": "📅 Time Range",
                "filterType": "filter_time",
                "targets": [{"datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": "Last day"}},
                "controlValues": {},
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
            {
                "id": "NATIVE_FILTER-status",
                "name": "🔵 Status",
                "filterType": "filter_select",
                "targets": [{"column": {"name": "status"}, "datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": []}},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": True,
                    "searchAllOptions": True,
                    "defaultToFirstItem": False,
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
            {
                "id": "NATIVE_FILTER-type",
                "name": "💳 Transaction Type",
                "filterType": "filter_select",
                "targets": [{"column": {"name": "transaction_type"}, "datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": []}},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": True,
                    "searchAllOptions": True,
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
            {
                "id": "NATIVE_FILTER-category",
                "name": "🏷️ Category",
                "filterType": "filter_select",
                "targets": [{"column": {"name": "category"}, "datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": []}},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": True,
                    "searchAllOptions": True,
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
            {
                "id": "NATIVE_FILTER-city",
                "name": "🏙️ City",
                "filterType": "filter_select",
                "targets": [{"column": {"name": "city"}, "datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": []}},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": True,
                    "searchAllOptions": True,
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
            {
                "id": "NATIVE_FILTER-vip",
                "name": "⭐ VIP Only",
                "filterType": "filter_select",
                "targets": [{"column": {"name": "is_vip"}, "datasetId": dataset_id}],
                "defaultDataMask": {"filterState": {"value": []}},
                "controlValues": {
                    "enableEmptyFilter": False,
                    "multiSelect": False,
                    "defaultToFirstItem": False,
                },
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            },
        ],
    }
    return json.dumps(meta)


# ─────────────────────────────────────────────────────────────
#  UPSERT HELPERS
# ─────────────────────────────────────────────────────────────


def upsert_metrics(session, table_obj, SqlMetric):
    existing = {m.metric_name for m in table_obj.metrics}
    added = 0
    for met in METRICS:
        if met["metric_name"] not in existing:
            table_obj.metrics.append(
                SqlMetric(
                    metric_name=met["metric_name"],
                    expression=met["expression"],
                )
            )
            added += 1
    if added:
        session.commit()
        print(f"  ✅ Added {added} missing metrics.")
    else:
        print("  ℹ️  All metrics already present.")


def upsert_columns(session, table_obj, TableColumn):
    existing = {c.column_name for c in table_obj.columns}
    added = 0
    for col in COLUMNS:
        if col["column_name"] not in existing:
            table_obj.columns.append(
                TableColumn(
                    column_name=col["column_name"],
                    type=col["type"],
                    is_dttm=col.get("is_dttm", False),
                )
            )
            added += 1
    if added:
        session.commit()
        print(f"  ✅ Added {added} missing columns.")


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────


def import_all():
    print("🚀 Financial Dashboard Import — v4 (Superset 5.x compatible)")
    print("=" * 60)

    from superset import db
    from superset.app import create_app

    app = None
    for i in range(10):
        try:
            app = create_app()
            app.app_context().push()
            db.session.execute("SELECT 1")
            print("✅ Connected to Superset Metadata DB.")
            break
        except Exception as e:
            print(f"⏳ Waiting for DB... ({i+1}/10) — {e}")
            time.sleep(5)

    if not app:
        print("❌ Could not connect. Aborting.")
        return

    from superset.connectors.sqla.models import SqlaTable, SqlMetric, TableColumn
    from superset.models.core import Database
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    # ── Load YAML ─────────────────────────────────────────────
    config_path = "/app/SUPERSET_DASHBOARD_PRO.yaml"
    if not os.path.exists(config_path):
        print(f"❌ Config not found: {config_path}")
        return

    with open(config_path, "r") as f:
        raw = f.read()

    def _env(m):
        return os.getenv(m.group(1), m.group(0))

    data = yaml.safe_load(re.sub(r"\$\{([^}]+)\}", _env, raw))

    for db_data in data.get("databases", []):

        # ── Database ──────────────────────────────────────────
        print(f"\n📦 Database: {db_data['database_name']}")
        target_db = db.session.query(Database).filter_by(database_name=db_data["database_name"]).first()

        if not target_db:
            try:
                target_db = Database(
                    database_name=db_data["database_name"],
                    sqlalchemy_uri=db_data["sqlalchemy_uri"],
                )
                db.session.add(target_db)
                db.session.commit()
                print(f"  ✅ Created.")
            except Exception as e:
                db.session.rollback()
                print(f"  ❌ {e}")
                continue
        else:
            print(f"  ℹ️  Exists — syncing URI.")
            target_db.sqlalchemy_uri = db_data["sqlalchemy_uri"]
            db.session.commit()

        # ── Dataset ───────────────────────────────────────────
        target_table = None
        for tbl_data in db_data.get("tables", []):
            print(f"\n📋 Dataset: {tbl_data['table_name']}")
            target_table = db.session.query(SqlaTable).filter_by(table_name=tbl_data["table_name"]).first()

            if not target_table:
                try:
                    target_table = SqlaTable(
                        table_name=tbl_data["table_name"],
                        database=target_db,
                        main_dttm_col="transaction_time",
                        schema="financial_dw",
                    )
                    db.session.add(target_table)
                    db.session.flush()
                    for col in COLUMNS:
                        target_table.columns.append(
                            TableColumn(
                                column_name=col["column_name"],
                                type=col["type"],
                                is_dttm=col.get("is_dttm", False),
                            )
                        )
                    for met in METRICS:
                        target_table.metrics.append(
                            SqlMetric(
                                metric_name=met["metric_name"],
                                expression=met["expression"],
                            )
                        )
                    db.session.commit()
                    print(f"  ✅ Created with {len(COLUMNS)} columns & {len(METRICS)} metrics.")
                except Exception as e:
                    db.session.rollback()
                    print(f"  ❌ {e}")
                    continue
            else:
                print(f"  ℹ️  Exists — upserting metrics & columns...")
                upsert_metrics(db.session, target_table, SqlMetric)
                upsert_columns(db.session, target_table, TableColumn)

        if not target_table:
            print("❌ No valid dataset — skipping.")
            continue

        # ── Charts ────────────────────────────────────────────
        print(f"\n📊 Creating {len(SLICES)} charts...")
        created_slices = {}

        for idx, s_def in enumerate(SLICES, start=1):
            try:
                existing = db.session.query(Slice).filter_by(slice_name=s_def["slice_name"]).first()
                if existing:
                    db.session.delete(existing)
                    db.session.commit()

                sl = Slice(
                    slice_name=s_def["slice_name"],
                    viz_type=s_def["viz_type"],
                    datasource_type="table",
                    datasource_id=target_table.id,
                    params=s_def["params"],
                )
                db.session.add(sl)
                db.session.flush()
                created_slices[idx] = sl.id
                print(f"  ✅ [{idx:02d}/{len(SLICES)}] {s_def['slice_name']}")
            except Exception as e:
                db.session.rollback()
                print(f"  ❌ [{idx:02d}/{len(SLICES)}] {s_def['slice_name']}: {e}")

        db.session.commit()
        ok = len(created_slices)
        print(f"\n  → {ok}/{len(SLICES)} charts created successfully.")

        if not created_slices:
            print("❌ No charts — skipping dashboard creation.")
            continue

        # ── Dashboard ─────────────────────────────────────────
        print("\n🎨 Creating dashboard...")
        position = build_position(created_slices)
        meta_json = build_metadata(target_table.id)

        for dash_data in data.get("dashboards", []):
            try:
                existing_dash = db.session.query(Dashboard).filter_by(dashboard_title=dash_data["dashboard_title"]).first()
                if existing_dash:
                    db.session.delete(existing_dash)
                    db.session.commit()
                    print("  🗑️  Removed old dashboard.")

                all_slices = db.session.query(Slice).filter(Slice.id.in_(list(created_slices.values()))).all()

                dash = Dashboard(
                    dashboard_title=dash_data["dashboard_title"],
                    slug=dash_data.get("slug"),
                    uuid=dash_data.get("uuid", str(uuid.uuid4())),
                    position_json=json.dumps(position),
                    json_metadata=meta_json,
                )
                dash.slices = all_slices
                db.session.add(dash)
                db.session.commit()

                print(f"\n  🎉 Dashboard '{dash_data['dashboard_title']}' created!")
                print(f"     Charts  : {len(all_slices)}")
                print(f"     Filters : 6 native filters (time, status, type, category, city, vip)")
                print(f"     Refresh : every 5 seconds")

            except Exception as e:
                db.session.rollback()
                print(f"  ❌ Dashboard failed: {e}")

    print("\n" + "=" * 60)
    print("✨ Done! Go to Superset → Dashboards")
    print("   Tip: In the filter bar, set Time Range = 'Last 7 days'")
    print("        to see more data across all charts.")


if __name__ == "__main__":
    import_all()
