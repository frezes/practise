import csv
from datetime import datetime, timedelta
from collections import defaultdict
from prometheus_api_client import PrometheusConnect

class ClusterReporter:
    def __init__(self, prom_url):
        self.prom = PrometheusConnect(url=prom_url)
        self.nodes = defaultdict(lambda: {
            'cluster': '', 'node': '', 'internal_ip': '',
            'cpu_avg': 0.0, 'cpu_peak': 0.0,
            'mem_avg': 0.0, 'mem_peak': 0.0,
            'cpu_alloc': 0.0, 'mem_alloc': 0.0
        })

    def execute_queries(self):
        """执行所有优化后的查询"""
        queries = [
            # CPU 使用率指标
            ('cpu_avg', '''
                label_replace(
                  avg_over_time(
                    sum by (cluster, instance) (
                      rate(node_cpu_seconds_total{job="node-exporter",mode!="idle",mode!="iowait",mode!="steal"}[5m])
                    )[1w:]
                  ),
                  "node",
                  "$1",
                  "instance",
                  "(.*)"
                )
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
             '''),
            ('cpu_peak', '''
                label_replace(
                  max_over_time(
                    sum by (cluster, instance) (
                      rate(node_cpu_seconds_total{job="node-exporter",mode!="idle",mode!="iowait",mode!="steal"}[5m])
                    )[1w:]
                  ),
                  "node",
                  "$1",
                  "instance",
                  "(.*)"
                )
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
            '''),
            # 内存使用率指标
            ('mem_avg', '''
                label_replace(
                  avg_over_time(
                    sum by (cluster, instance) (
                        1
                      -
                        (
                            (
                                node_memory_MemAvailable_bytes{job="node-exporter"}
                              or
                                (
                                      node_memory_Buffers_bytes{job="node-exporter"} + node_memory_Cached_bytes{job="node-exporter"}
                                    +
                                      node_memory_MemFree_bytes{job="node-exporter"}
                                  +
                                    node_memory_Slab_bytes{job="node-exporter"}
                                )
                            )
                          /
                            node_memory_MemTotal_bytes{job="node-exporter"}
                        )
                    )[1w:]
                  ),
                  "node",
                  "$1",
                  "instance",
                  "(.*)"
                )
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
            '''),
            ('mem_peak', '''
                label_replace(
                  max_over_time(
                    sum by (cluster, instance) (
                        1
                      -
                        (
                            (
                                node_memory_MemAvailable_bytes{job="node-exporter"}
                              or
                                (
                                      node_memory_Buffers_bytes{job="node-exporter"} + node_memory_Cached_bytes{job="node-exporter"}
                                    +
                                      node_memory_MemFree_bytes{job="node-exporter"}
                                  +
                                    node_memory_Slab_bytes{job="node-exporter"}
                                )
                            )
                          /
                            node_memory_MemTotal_bytes{job="node-exporter"}
                        )
                    )[1w:]
                  ),
                  "node",
                  "$1",
                  "instance",
                  "(.*)"
                )
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
            '''),
            # 分配率指标
            ('cpu_alloc', '''
                sum by (cluster, node) (
                  kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu"}
                * on (namespace, pod, cluster) group_left ()
                  max by (namespace, pod, cluster) ((kube_pod_status_phase{phase=~"Pending|Running"} == 1))
                )
                /
                sum by (cluster, node) (kube_node_status_allocatable{resource="cpu"})
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
            '''),
            ('mem_alloc', '''
                sum by (cluster, node) (
                  kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory"}
                * on (namespace, pod, cluster) group_left ()
                  max by (namespace, pod, cluster) ((kube_pod_status_phase{phase=~"Pending|Running"} == 1))
                )
                /
                sum by (cluster, node) (kube_node_status_allocatable{resource="memory"})
                * on (cluster, node) group_left (internal_ip) max by (cluster, node, internal_ip) (kube_node_info)
            ''')
        ]
        
        for metric_type, query in queries:
            try:
                # 使用 custom_query 而非 custom_query_range
                data = self.prom.custom_query(query)
                self._process_metric(metric_type, data)
            except Exception as e:
                print(f"查询 {metric_type} 失败: {str(e)}")

    def _process_metric(self, metric_type, results):
        """处理单个指标结果"""
        for item in results:  # 直接遍历结果列表
            try:
                labels = item['metric']
                key = (labels.get('cluster', 'default'), 
                      labels.get('node', 'unknown'))
                
                # 更新节点元数据（带错误处理）
                self.nodes[key].update({
                    'cluster': labels.get('cluster', 'default'),
                    'node': labels.get('node', 'unknown'),
                    'internal_ip': labels.get('internal_ip', 'N/A')
                })
                
                # 指标值处理（带类型转换保护）
                value = float(item['value'][1]) * 100  # 转换成百分比
                self.nodes[key][metric_type] = round(value, 2)
            except KeyError as e:
                print(f"数据字段缺失: {str(e)}")
            except (IndexError, ValueError) as e:
                print(f"数值转换错误: {str(e)}")

    def generate_report(self, filename):
        """生成排序报告"""
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda x: (x['cluster'], x['node'])
        )
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '集群', '节点名称', '节点IP',
                '近7天CPU使用率平均值(%)', '近7天CPU使用率峰值(%)',
                '近7天内存使用率平均值(%)', '近7天内存使用率峰值(%)',
                'CPU分配率(%)', '内存分配率(%)'
            ])
            writer.writeheader()
            
            for node in sorted_nodes:
                writer.writerow({
                    '集群': node['cluster'],
                    '节点名称': node['node'],
                    '节点IP': node['internal_ip'],
                    '近7天CPU使用率平均值(%)': node['cpu_avg'],
                    '近7天CPU使用率峰值(%)': node['cpu_peak'],
                    '近7天内存使用率平均值(%)': node['mem_avg'],
                    '近7天内存使用率峰值(%)': node['mem_peak'],
                    'CPU分配率(%)': node['cpu_alloc'],
                    '内存分配率(%)': node['mem_alloc']
                })

if __name__ == "__main__":
    # 使用示例
    reporter = ClusterReporter("http://172.31.19.4:30990")
    reporter.execute_queries()
    reporter.generate_report("cluster_report.csv")
