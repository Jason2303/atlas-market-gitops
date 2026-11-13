#!/usr/bin/env python3
"""Dashboards as code: generates the Grafana dashboard JSON in platform/monitoring-config/dashboards/.

    python3 scripts/build_dashboards.py

Datasource UIDs: prometheus (kube-prometheus-stack default) and loki
(platform/monitoring/kube-prometheus-stack.yaml).
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "platform" / "monitoring-config" / "dashboards"
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}

_id = 0


def _next_id():
    global _id
    _id += 1
    return _id


def target(expr, legend="", ds=PROM, ref="A", **extra):
    t = {"datasource": ds, "expr": expr, "refId": ref, "legendFormat": legend}
    t.update(extra)
    return t


def panel(kind, title, targets, x, y, w, h, ds=PROM, unit=None, desc="", thresholds=None,
          options=None, overrides=None, min_=None, max_=None, decimals=None):
    defaults = {"custom": {}}
    if unit:
        defaults["unit"] = unit
    if min_ is not None:
        defaults["min"] = min_
    if max_ is not None:
        defaults["max"] = max_
    if decimals is not None:
        defaults["decimals"] = decimals
    if thresholds:
        defaults["thresholds"] = {
            "mode": "absolute",
            "steps": [{"color": c, "value": v} for v, c in thresholds],
        }
        if kind == "timeseries":
            defaults["custom"]["thresholdsStyle"] = {"mode": "line+area"}
    if kind == "timeseries":
        defaults["custom"].update({"lineWidth": 2, "fillOpacity": 10, "showPoints": "never"})
    p = {
        "id": _next_id(),
        "type": kind,
        "title": title,
        "description": desc,
        "datasource": ds,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
        "options": options or {},
    }
    if kind == "stat":
        p["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": "background", "graphMode": "area", "textMode": "auto", **(options or {})}
    if kind == "timeseries":
        p["options"] = {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max", "lastNotNull"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}, **(options or {})}
    return p


def row(title, y):
    return {"id": _next_id(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def dashboard(uid, title, panels, templating=None, tags=None, desc="", refresh="30s", time_from="now-1h"):
    return {
        "uid": uid,
        "title": title,
        "description": desc,
        "tags": tags or [],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "editable": True,
        "graphTooltip": 1,
        "refresh": refresh,
        "time": {"from": time_from, "to": "now"},
        "templating": {"list": templating or []},
        "annotations": {"list": [{
            "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts", "type": "dashboard"}]},
        "links": [{"title": "Atlas dashboards", "type": "dashboards", "tags": ["atlas"], "asDropdown": True}],
        "panels": panels,
    }


def prom_var(name, query, label, multi=True):
    return {
        "name": name, "label": label, "type": "query", "datasource": PROM,
        "query": {"query": query, "refId": "PrometheusVariableQueryEditor-VariableQuery"},
        "definition": query, "refresh": 2, "includeAll": multi, "multi": multi,
        "allValue": ".*", "current": {"selected": True, "text": "All", "value": "$__all"} if multi else {},
        "sort": 1,
    }


NS_VAR = {
    "name": "namespace", "label": "Environment", "type": "custom",
    "query": "atlas-production,atlas-staging", "includeAll": False, "multi": False,
    "current": {"selected": True, "text": "atlas-production", "value": "atlas-production"},
    "options": [],
}


# ====================================================== 1. Service overview (RED)
def service_overview():
    global _id
    _id = 0
    sel = 'namespace="$namespace", service=~"$service"'
    ns = 'namespace="$namespace"'
    p = [row("RED: rate, errors, duration", 0)]
    p += [
        panel("stat", "Request rate", [target(f'sum(rate(http_requests_total{{{sel}}}[5m]))')],
              0, 1, 6, 4, unit="reqps", decimals=1, thresholds=[(None, "blue")]),
        panel("stat", "Error rate (5xx)", [target(
            f'sum(rate(http_requests_total{{{sel}, status=~"5.."}}[5m])) / sum(rate(http_requests_total{{{sel}}}[5m]))')],
            6, 1, 6, 4, unit="percentunit", decimals=2, thresholds=[(None, "green"), (0.01, "orange"), (0.05, "red")],
            desc="HighErrorRate alert fires above 5% for 5 minutes"),
        panel("stat", "p99 latency", [target(
            f'histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))')],
            12, 1, 6, 4, unit="s", decimals=3, thresholds=[(None, "green"), (0.5, "orange"), (1, "red")],
            desc="HighLatencyP99 alert fires above 1s for 5 minutes"),
        panel("stat", "Scrape targets up", [target(f'sum(up{{{sel}}}) / count(up{{{sel}}})')],
              18, 1, 6, 4, unit="percentunit", decimals=0, thresholds=[(None, "red"), (1, "green")]),
        panel("timeseries", "Rate: requests/s by service",
              [target(f'sum by (service) (rate(http_requests_total{{{sel}}}[5m]))', "{{service}}")],
              0, 5, 8, 8, unit="reqps"),
        panel("timeseries", "Errors: 5xx ratio by service",
              [target(f'sum by (service) (rate(http_requests_total{{{sel}, status=~"5.."}}[5m])) / sum by (service) (rate(http_requests_total{{{sel}}}[5m]))', "{{service}}")],
              8, 5, 8, 8, unit="percentunit", min_=0, thresholds=[(None, "transparent"), (0.05, "red")]),
        panel("timeseries", "Duration: p50 / p95 / p99",
              [target(f'histogram_quantile(0.50, sum by (service, le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "p50 {{service}}", ref="A"),
               target(f'histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "p95 {{service}}", ref="B"),
               target(f'histogram_quantile(0.99, sum by (service, le) (rate(http_request_duration_seconds_bucket{{{sel}}}[5m])))', "p99 {{service}}", ref="C")],
              16, 5, 8, 8, unit="s", thresholds=[(None, "transparent"), (1, "red")]),
        panel("table", "Requests by route and status (req/s, last 5m)",
              [target(f'sum by (service, route, method, status) (rate(http_requests_total{{{sel}}}[5m]))', format="table", instant=True)],
              0, 13, 12, 8, unit="reqps", decimals=2),
        panel("logs", "Error logs for this environment (expand a line to see trace_id)",
              [target(f'{{namespace="$namespace", level="error"}}', ds=LOKI)],
              12, 13, 12, 8, ds=LOKI,
              options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}),
    ]
    p.append(row("Business", 21))
    p += [
        panel("stat", "Orders placed / min", [target(f'sum(rate(shop_orders_total{{{ns}, result="placed"}}[5m])) * 60')],
              0, 22, 5, 4, decimals=1, thresholds=[(None, "blue")]),
        panel("stat", "Revenue / hour", [target(f'sum(rate(shop_revenue_cents_total{{{ns}}}[5m])) * 3600 / 100')],
              5, 22, 5, 4, unit="currencyUSD", decimals=0, thresholds=[(None, "green")]),
        panel("stat", "Checkout success (our side)", [target(
            f'sum(rate(shop_orders_total{{{ns}, result="placed"}}[10m])) / sum(rate(shop_orders_total{{{ns}, result=~"placed|failed"}}[10m]))')],
            10, 22, 5, 4, unit="percentunit", decimals=1, thresholds=[(None, "red"), (0.95, "orange"), (0.99, "green")],
            desc="Excludes out-of-stock and invalid input; OrderFailuresHigh alert below 95%"),
        panel("stat", "Catalogue cache hit ratio", [target(
            f'sum(rate(product_cache_requests_total{{{ns}, result="hit"}}[10m])) / sum(rate(product_cache_requests_total{{{ns}}}[10m]))')],
            15, 22, 5, 4, unit="percentunit", decimals=0, thresholds=[(None, "orange"), (0.5, "green")]),
        panel("stat", "Avg order value", [target(
            f'sum(rate(shop_order_value_cents_sum{{{ns}}}[30m])) / sum(rate(shop_order_value_cents_count{{{ns}}}[30m])) / 100')],
            20, 22, 4, 4, unit="currencyUSD", decimals=2, thresholds=[(None, "purple")]),
        panel("timeseries", "Order outcomes (per min)",
              [target(f'sum by (result) (rate(shop_orders_total{{{ns}}}[5m])) * 60', "{{result}}")],
              0, 26, 8, 8, desc="placed / rejected (out of stock) / invalid / failed (our fault)"),
        panel("timeseries", "Gateway protection: rate-limited + upstream errors (per min)",
              [target(f'sum(rate(gateway_rate_limited_requests_total{{{ns}}}[5m])) * 60', "rate limited", ref="A"),
               target(f'sum by (target, kind) (rate(gateway_upstream_errors_total{{{ns}}}[5m])) * 60', "upstream {{target}} {{kind}}", ref="B")],
              8, 26, 8, 8),
        panel("table", "Stock levels (lowest first)",
              [target(f'sort(min by (sku, category) (product_stock_units{{{ns}}}))', format="table", instant=True)],
              16, 26, 8, 8, decimals=0, thresholds=[(None, "red"), (5, "orange"), (10, "green")],
              desc="LowStock (info) alert below 5 units"),
    ]
    tmpl = [NS_VAR, prom_var("service", 'label_values(http_requests_total{namespace="$namespace"}, service)', "Service")]
    return dashboard("atlas-service-overview", "Atlas / Service overview (RED + business)", p, templating=tmpl,
                     tags=["atlas", "red"], desc="RED metrics per service, business KPIs and error logs")


# ============================================================ 2. Infrastructure
def infrastructure():
    global _id
    _id = 0
    inst = 'instance=~"$instance"'
    fs = 'fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs"'
    p = [row("Cluster and nodes", 0)]
    p += [
        panel("stat", "Nodes Ready", [target('sum(kube_node_status_condition{condition="Ready", status="true"})')],
              0, 1, 4, 4, thresholds=[(None, "red"), (1, "green")]),
        panel("stat", "CPU used", [target(f'1 - avg(rate(node_cpu_seconds_total{{mode="idle", {inst}}}[5m]))')],
              4, 1, 5, 4, unit="percentunit", decimals=1, thresholds=[(None, "green"), (0.7, "orange"), (0.9, "red")]),
        panel("stat", "Memory used", [target(f'1 - sum(node_memory_MemAvailable_bytes{{{inst}}}) / sum(node_memory_MemTotal_bytes{{{inst}}})')],
              9, 1, 5, 4, unit="percentunit", decimals=1, thresholds=[(None, "green"), (0.75, "orange"), (0.9, "red")]),
        panel("stat", "Fullest filesystem", [target(f'max(1 - node_filesystem_avail_bytes{{{fs}, {inst}}} / node_filesystem_size_bytes{{{fs}, {inst}}})')],
              14, 1, 5, 4, unit="percentunit", decimals=1, thresholds=[(None, "green"), (0.8, "orange"), (0.9, "red")]),
        panel("stat", "Pod restarts (1h)", [target('sum(increase(kube_pod_container_status_restarts_total[1h]))')],
              19, 1, 5, 4, decimals=0, thresholds=[(None, "green"), (1, "orange"), (4, "red")]),
        panel("timeseries", "CPU by node", [target(f'1 - avg by (instance) (rate(node_cpu_seconds_total{{mode="idle", {inst}}}[5m]))', "{{instance}}")],
              0, 5, 8, 8, unit="percentunit", min_=0, max_=1),
        panel("timeseries", "Memory by node", [target(f'1 - node_memory_MemAvailable_bytes{{{inst}}} / node_memory_MemTotal_bytes{{{inst}}}', "{{instance}}")],
              8, 5, 8, 8, unit="percentunit", min_=0, max_=1),
        panel("timeseries", "Disk used by mountpoint",
              [target(f'1 - node_filesystem_avail_bytes{{{fs}, {inst}}} / node_filesystem_size_bytes{{{fs}, {inst}}}', "{{instance}} {{mountpoint}}")],
              16, 5, 8, 8, unit="percentunit", min_=0, max_=1, thresholds=[(None, "transparent"), (0.9, "red")]),
        panel("timeseries", "Network throughput (tx negative)",
              [target(f'sum by (instance) (rate(node_network_receive_bytes_total{{device!~"lo|veth.*|cni.*", {inst}}}[5m]))', "rx {{instance}}", ref="A"),
               target(f'-sum by (instance) (rate(node_network_transmit_bytes_total{{device!~"lo|veth.*|cni.*", {inst}}}[5m]))', "tx {{instance}}", ref="B")],
              0, 13, 12, 8, unit="Bps"),
        panel("timeseries", "Disk I/O (write negative)",
              [target(f'sum by (instance) (rate(node_disk_read_bytes_total{{{inst}}}[5m]))', "read {{instance}}", ref="A"),
               target(f'-sum by (instance) (rate(node_disk_written_bytes_total{{{inst}}}[5m]))', "write {{instance}}", ref="B")],
              12, 13, 12, 8, unit="Bps"),
    ]
    p.append(row("Atlas workloads", 21))
    p += [
        panel("stat", "Postgres ready (prod / staging)",
              [target('kube_statefulset_status_replicas_ready{namespace=~"atlas-.*", statefulset="postgres"}', "{{namespace}}")],
              0, 22, 6, 4, thresholds=[(None, "red"), (1, "green")]),
        panel("stat", "Redis available (prod / staging)",
              [target('kube_deployment_status_replicas_available{namespace=~"atlas-.*", deployment="redis"}', "{{namespace}}")],
              6, 22, 6, 4, thresholds=[(None, "red"), (1, "green")]),
        panel("stat", "Pods not ready (atlas)",
              [target('sum(kube_pod_status_ready{namespace=~"atlas-.*", condition="false"}) or vector(0)')],
              12, 22, 6, 4, decimals=0, thresholds=[(None, "green"), (1, "red")]),
        panel("stat", "Containers restarting (1h, atlas)",
              [target('count(increase(kube_pod_container_status_restarts_total{namespace=~"atlas-.*"}[1h]) > 0) or vector(0)')],
              18, 22, 6, 4, decimals=0, thresholds=[(None, "green"), (1, "orange")]),
        panel("timeseries", "CPU by namespace (cores)",
              [target('sum by (namespace) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))', "{{namespace}}")],
              0, 26, 12, 8),
        panel("timeseries", "Memory (working set) by namespace",
              [target('sum by (namespace) (container_memory_working_set_bytes{container!=""})', "{{namespace}}")],
              12, 26, 12, 8, unit="bytes"),
    ]
    p.append(row("GitOps (ArgoCD)", 34))
    p += [
        panel("table", "ArgoCD applications: sync and health",
              [target('argocd_app_info', format="table", instant=True)],
              0, 35, 24, 7,
              desc="atlas-production OutOfSync is expected until a release manager syncs a promotion",
              overrides=[{"matcher": {"id": "byRegexp", "options": "^(Time|Value|__name__|instance|job|endpoint|pod|service|container|namespace|repo|autosync_enabled|dest_server)$"},
                          "properties": [{"id": "custom.hidden", "value": True}]}]),
    ]
    tmpl = [prom_var("instance", "label_values(node_uname_info, instance)", "Node")]
    return dashboard("atlas-infrastructure", "Atlas / Infrastructure + GitOps", p, templating=tmpl,
                     tags=["atlas", "infrastructure"], desc="Nodes, workloads, data tier and ArgoCD app status")


# ======================================================================= 3. Logs
def logs():
    global _id
    _id = 0
    sel = '{namespace="$namespace", service=~"$service"}'
    errs = '{namespace="$namespace", service=~"$service", level="error"}'
    p = [
        panel("stat", "Error logs (15m)", [target(f'sum(count_over_time({errs}[15m])) or vector(0)', ds=LOKI)],
              0, 0, 6, 4, ds=LOKI, decimals=0, thresholds=[(None, "green"), (1, "orange"), (50, "red")]),
        panel("stat", "Warnings (15m)", [target(f'sum(count_over_time({{namespace="$namespace", service=~"$service", level="warn"}}[15m])) or vector(0)', ds=LOKI)],
              6, 0, 6, 4, ds=LOKI, decimals=0, thresholds=[(None, "green"), (10, "orange")]),
        panel("stat", "Log lines / s", [target(f'sum(rate({sel}[5m]))', ds=LOKI)],
              12, 0, 6, 4, ds=LOKI, decimals=1, thresholds=[(None, "blue")]),
        panel("stat", "Alert notifications (1h)", [target('sum(count_over_time({namespace="monitoring", app="alert-sink"} |= "alert notification" [1h])) or vector(0)', ds=LOKI)],
              18, 0, 6, 4, ds=LOKI, decimals=0, thresholds=[(None, "green"), (1, "orange")],
              desc="Notifications delivered by Alertmanager to the alert-sink receiver"),
        panel("timeseries", "Log volume by service", [target(f'sum by (service) (count_over_time({sel}[1m]))', "{{service}}", ds=LOKI)],
              0, 4, 12, 8, ds=LOKI),
        panel("timeseries", "Errors by service", [target(f'sum by (service) (count_over_time({errs}[1m]))', "{{service}}", ds=LOKI)],
              12, 4, 12, 8, ds=LOKI),
        panel("table", "Top error messages (1h)",
              [target(f'topk(10, sum by (service, msg) (count_over_time({errs} | json [1h])))', ds=LOKI, queryType="instant")],
              0, 12, 10, 9, ds=LOKI, decimals=0),
        panel("logs", "Recent errors and warnings",
              [target(f'{{namespace="$namespace", service=~"$service", level=~"error|warn"}} |= "$search"', ds=LOKI)],
              10, 12, 14, 9, ds=LOKI,
              options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}),
        panel("logs", "Follow one request: every log line with this trace_id, across all services",
              [target('{namespace=~"atlas-.*"} |= "$trace_id"', ds=LOKI)],
              0, 21, 24, 9, ds=LOKI,
              desc="Paste a trace_id (from the X-Trace-Id response header or any log line) into the trace_id box",
              options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Ascending", "enableLogDetails": True}),
        panel("logs", "Alert notifications delivered (alert-sink)",
              [target('{namespace="monitoring", app="alert-sink"} |= "alert notification"', ds=LOKI)],
              0, 30, 24, 8, ds=LOKI,
              options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}),
    ]
    tmpl = [
        NS_VAR,
        {"name": "service", "label": "Service", "type": "custom", "query": "gateway,product-service,order-service",
         "includeAll": True, "multi": True, "allValue": ".*",
         "current": {"selected": True, "text": "All", "value": "$__all"}, "options": []},
        {"name": "trace_id", "label": "trace_id", "type": "textbox", "query": "", "current": {"text": "", "value": ""}},
        {"name": "search", "label": "Search", "type": "textbox", "query": "", "current": {"text": "", "value": ""}},
    ]
    return dashboard("atlas-logs", "Atlas / Logs + trace lookup", p, templating=tmpl,
                     tags=["atlas", "logs"], desc="Loki: errors, volume, trace_id lookup across services, alert delivery log")


# ======================================================================== 4. SLO
def slo():
    global _id
    _id = 0
    budget = 0.005
    err = 'sum by (service) (increase(http_requests_total{namespace="$namespace", status=~"5.."}[30d]))'
    tot = 'sum by (service) (increase(http_requests_total{namespace="$namespace"}[30d]))'
    p = [
        panel("stat", "Availability (30d) vs 99.5% objective", [target(f'1 - ({err} / {tot})', "{{service}}")],
              0, 0, 12, 5, unit="percentunit", decimals=3, thresholds=[(None, "red"), (0.995, "green")]),
        panel("gauge", "Error budget remaining (30d)", [target(f'1 - (({err} / {tot}) / {budget})', "{{service}}")],
              12, 0, 12, 5, unit="percentunit", min_=0, max_=1, decimals=1,
              thresholds=[(None, "red"), (0.25, "orange"), (0.5, "green")]),
        panel("timeseries", "Burn rate, 1h window (page above 14.4x)",
              [target(f'slo:sli_error:ratio_rate1h{{namespace="$namespace"}} / {budget}', "{{service}}")],
              0, 5, 12, 8, thresholds=[(None, "transparent"), (14.4, "red")]),
        panel("timeseries", "Burn rate, 6h window (ticket above 6x)",
              [target(f'slo:sli_error:ratio_rate6h{{namespace="$namespace"}} / {budget}', "{{service}}")],
              12, 5, 12, 8, thresholds=[(None, "transparent"), (6, "orange")]),
    ]
    return dashboard("atlas-slo", "Atlas / SLO 99.5%", p, templating=[NS_VAR], tags=["atlas", "slo"],
                     desc="Error budget and multi-window burn rates", time_from="now-6h")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("service-overview", service_overview), ("infrastructure", infrastructure),
                     ("logs", logs), ("slo", slo)]:
        d = fn()
        (OUT / f"{name}.json").write_text(json.dumps(d, indent=2) + "\n")
        print(f"wrote {name}.json ({len(d['panels'])} panels)")
