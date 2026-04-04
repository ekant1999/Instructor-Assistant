---
title: "CMPE 286 - LAB - 3: Web Traffic Inspection and RTT Study"
paper_id: 504252236656
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/Hybrid/Assignment5.pdf"
generated_at: "2026-04-04T22:55:05.213900+00:00"
num_figures: 6
num_tables: 1
num_equations: 0
---

CMPE 286 – LAB – 3: Web Traffic Inspection and RTT

Study

Name: Alex Morgan | Student ID: 019845672

Generated sample submission with dummy data, tables, and figures for PDF extraction evaluation.

Objective: Capture normal browser activity and inspect HTTP, DNS, TCP, and UDP traffic using a packet analyzer. The report also summarizes delay, jitter, and handshake timing using dummy measurements.

## Part 1: Environment Setup

A fresh capture profile was created with custom columns for source port, destination port, host, and URI. The tool was configured to save traces in .pcapng format so that multiple protocol filters could be evaluated later.

![Figure 1](assets/figures/page_001_img_001.png)

_Figure 1: Mock packet-analyzer workspace with a saved capture profile._

## Part 2: Protocol Filters

![Figure 2](assets/figures/page_002_img_001.png)

_Figure 2: HTTP filter results showing request and response entries._

![Figure 3](assets/figures/page_002_img_002.png)

_Figure 3: DNS queries and responses captured during page load._

![Figure 4](assets/figures/page_003_img_001.png)

_Figure 4: TCP/TLS packets associated with the same browsing session._

![Figure 5](assets/figures/page_003_img_002.png)

_Figure 5: UDP and QUIC packets that appeared alongside DNS traffic._

## Part 3: HTTP Request Summary

The following table summarizes sample requests identified from the filtered capture. All values below are fabricated for benchmarking purposes but follow realistic web-traffic patterns.

## Part 4: Delay and Jitter

![Figure 6](assets/figures/page_004_vec_001.png)

_Figure 6: RTT histogram from three fabricated destination groups._

## Part 5: TCP 3-Way Handshake and Observations

> Table JSON: `assets/tables/table_0001.json`
> Table 1: A single connection was isolated and the time display was changed to “Seconds Since Previous Displayed Packet.” The sample handshake timings are shown below.

1. Name resolution appeared before every application flow, reinforcing that DNS latency is on the critical path.
2. The TCP and TLS filters highlighted the same sessions that later carried HTTP payloads.
3. Domestic destinations showed tighter RTT distributions than overseas destinations, while long-tail spikes

were more visible in the remote host sample.

4. Custom columns for ports, host, and URI made triage substantially faster when multiple protocols

interleaved in the same capture.
