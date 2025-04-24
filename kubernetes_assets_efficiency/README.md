# Kubernetes Assets Efficiency

### 快速开始

程序需要配置查询的 Prometheus 端口，执行完成后，将生成 `cluster_report.csv` 的文件，生成内容如[cluster_report.csv](./cluster_report.csv)。

如果用户使用 KSE 3.3.x 及以上版本，并启用了可观测中心，那么所有集群的监控数据都会进入 Prometheus 长期存储 `whizard` 中，且指标会增加 **cluster** 标签。此时配置地址将是 `whizard` Gateway 地址，在生成结果中，**cluster** 将为对应注册到 KSE 的集群名称。

如果客户仅使用是 Prometheus，那么监控数据将存储在各自集群，且指标将会不携带 **cluster** 标签。此时配置地址将是 `prometheus-k8s` 地址，且仅能查询单个集群数据，在生成结果中，**cluster** 字段将默认为 `default`。 

> 注: 为避免环境差异，查询使用原始 Metrics 进行级联查询，如果速度较慢，可以使用 Recording Rules 优化。

```
if __name__ == "__main__":
    # 使用示例
    reporter = ClusterReporter("http://172.31.19.4:30990")
    reporter.execute_queries()
    reporter.generate_report("cluster_report.csv")
```

### 环境及依赖

Python 版本(python -V): `Python 3.11.11`

依赖： `pip3 install prometheus-api-client`
