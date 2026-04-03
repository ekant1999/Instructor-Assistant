---
title: "CMPE 286 - LAB - 1"
paper_id: 565476836086
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/Assignment1.pdf"
generated_at: "2026-04-03T22:15:32.024945+00:00"
num_figures: 0
num_tables: 0
num_equations: 0
---

Name: Siddhant Abhijit Raje

Student ID: 018179954

Part 1: Installation

Part 2:

HTTP Traffic:

DNS Traffic:

TCP Traffic:

UDP Traffic:

Normal browsing instantly produces DNS lookups, then TCP/TLS or UDP/QUIC connections, followed by application data. Background traffic (e.g., mDNS, DHCPv6, ARP/ND) is typical on LANs and may appear even when you aren’t actively browsing.

Part 3: Identify HTTP Requests and Responses:

- Filter for HTTP packets and identify GET and POST requests (any one request is fine).

- Click on a packet and expand the Hypertext Transfer Protocol section to see details of the request (like

the URL, Host, and User-Agent).

Analyze DNS Packets:

Part 4: Custom Columns:

Custom Coloring rules:

HTTP:

DNS:

Part 5: Advanced Analysis

Protocol Hierarchy:

TCP Stream:

Part 6: Delay and Jitter

Hosts selected:

## Harvard.edu

MIT Pings:

UTexas Pings:

Histogram of RTT:

Mit.edu:

Utexas.edu:

UST:

Ethz:

Observation: U.S. destinations generally have lower RTTs than overseas ones; transoceanic links produce the largest hop-to-hop increases in traceroute. Wireless links and last-mile congestion raise jitter. Larger ICMP payloads may slightly increase RTT and variability due to serialization time and buffering.

Part 7: TCP 3-Way Handshake and Packet Timing

## rd Entry: ACK

Time between SYN and SYN, ACK: 0.025380

Time between SYN, ACK and ACK: 0.000256

(Changed the time view as: Set View -> Time Display Format -> Seconds Since Previous
Displayed Packet)

Final Observations:

## Protocol mix &

1. Protocol mix & encryption. The capture shows a contemporary web stack where

encryption and UDP-based transports are first-class: DNS to map names to IPs, then either TLS over TCP (HTTPS) or QUIC over UDP (HTTP/3). QUIC’s presence

under the generic udp filter explains why DNS and QUIC co-appear; protocol hierarchy confirms their relative shares.

## Name resolution

2. Name resolution precedes data flows. For each site, DNS queries precede

connection establishment. Cached domains reduce or eliminate network DNS lookups. Where DNS is slow or fails, application flows stall, a reminder that name resolution is on the critical path.

## Latency, jitter, and

3. Latency, jitter, and paths. Repeated 100-ping batches reveal that where the server is

(and when you measure) matters: nearby U.S. hosts exhibit low median RTTs and tight dispersion, while overseas hosts have higher medians with larger tails. Traceroute highlights the longest link(s)-often a transoceanic or inter-regional backbone, and occasional path changes across runs.

SYN,ACK->ACK is almost entirely host processing. ECN flags (ECE/CWR) may appear during handshake on networks that negotiate congestion-experienced signaling.

5. Practical analysis aids. Custom columns for ports and HTTP fields, plus simple

coloring rules, significantly speed up triage-particularly when QUIC, DNS, and TLS traffic interleave. Protocol Hierarchy and “Follow TCP Stream” provide fast summaries and per-flow clarity, respectively.
