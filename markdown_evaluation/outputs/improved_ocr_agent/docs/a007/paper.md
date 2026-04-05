# CS 249 – Assignment: VM Resource Monitoring and

<!-- document_mode: hybrid_paper -->

<!-- page 1 mode: hybrid_paper -->

Benchmarking

Name: Mina Alvarez | Student ID: 017904118

Generated sample submission with dummy data, tables, and figures for PDF extraction evaluation.

This sample report summarizes a synthetic benchmarking exercise on a Linux virtual machine. The write-up includes console screenshots, generated charts, and summary tables to emulate a realistic systems assignment.

## Test Environment

•
Ubuntu 22.04 VM with 4 vCPUs and 8 GB RAM

•
Python service exposed on localhost:8080

•
Load driver issuing mixed read/write requests for 15 minutes

•
Monitoring via htop, vmstat, and custom latency logs

![Figure 1](a007_assets/figures/page_001_img_001.png)

_Figure 1: Mock terminal output during the load test._

---

<!-- page 2 mode: hybrid_paper -->

## Benchmark Figures

![Figure 2](a007_assets/figures/page_002_img_001.png)

_Figure 2: CPU and memory utilization observed across the benchmark._

![Figure 3](a007_assets/figures/page_002_img_002.png)

_Figure 3: Throughput and tail-latency progression across the test._

---

<!-- page 3 mode: hybrid_paper -->

## Summary Table and Findings

> Table JSON: `a007_assets/tables/table_0001.json`
> Table 1: 3. Summary Table and Findings

1. The cache-enabled scenario produced the highest throughput without exhausting CPU or memory

headroom.

2. Tail latency increased sharply during the write-burst phase, which is consistent with queue buildup inside

the Python service.

3. Reducing worker count lowered resource usage slightly but pushed response times beyond the acceptable

threshold.

4. A mix of console screenshots, charts, and compact summary tables makes this document useful for PDF

extraction testing.

---
