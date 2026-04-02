# a001

<!-- document_mode: ocr -->

<!-- page 1 mode: hybrid_paper -->

CMPE 286 – LAB – 1

Name: Siddhant Abhijit Raje

Student ID: 018179954

Part 2:
HTTP Traffic:

![Figure 1 on Page 1](a001_assets/figures/a001_page_1_fig_1.png)

---

<!-- page 2 mode: ocr -->

<!-- OCR page 2 -->

![OCR Page 2](a001_page_2.png)

---

<!-- page 3 mode: ocr -->

<!-- OCR page 3 -->

![OCR Page 3](a001_page_3.png)

---

<!-- page 4 mode: hybrid_paper -->

Part 3: Identify HTTP Requests and Responses:

- Filter for HTTP packets and identify GET and POST requests (any one request is fine).

- Click on a packet and expand the Hypertext Transfer Protocol section to see details of the request (like

the URL, Host, and User-Agent).

Normal browsing instantly produces DNS lookups, then TCP/TLS or UDP/QUIC connections, followed by application data. Background traffic (e.g., mDNS, DHCPv6, ARP/ND) is typical on LANs and may appear even when you aren’t actively browsing.

![Figure 1 on Page 4](a001_assets/figures/a001_page_4_fig_1.png)

---

<!-- page 5 mode: ocr -->

<!-- OCR page 5 -->

![OCR Page 5](a001_page_5.png)

---

<!-- page 6 mode: ocr -->

<!-- OCR page 6 -->

![OCR Page 6](a001_page_6.png)

---

<!-- page 7 mode: ocr -->

<!-- OCR page 7 -->

![OCR Page 7](a001_page_7.png)

---

<!-- page 8 mode: ocr -->

<!-- OCR page 8 -->

![OCR Page 8](a001_page_8.png)

---

<!-- page 9 mode: hybrid_paper -->

MIT Pings:

Part 6: Delay and Jitter
Hosts selected:
1. Harvard.edu 2. Mit.edu 3. Utexas.edu 4. www.ust.hk 5. Ethz.ch

![Figure 1 on Page 9](a001_assets/figures/a001_page_9_fig_1.png)

---

<!-- page 10 mode: ocr -->

<!-- OCR page 10 -->

![OCR Page 10](a001_page_10.png)

---

<!-- page 11 mode: ocr -->

<!-- OCR page 11 -->

![OCR Page 11](a001_page_11.png)

---

<!-- page 12 mode: ocr -->

<!-- OCR page 12 -->

![OCR Page 12](a001_page_12.png)

---

<!-- page 13 mode: ocr -->

<!-- OCR page 13 -->

![OCR Page 13](a001_page_13.png)

---

<!-- page 14 mode: ocr -->

<!-- OCR page 14 -->

![OCR Page 14](a001_page_14.png)

---

<!-- page 15 mode: ocr -->

<!-- OCR page 15 -->

![OCR Page 15](a001_page_15.png)

---

<!-- page 16 mode: hybrid_paper -->

![Figure 1 on Page 16](a001_assets/figures/a001_page_16_fig_1.png)

Observation: U.S. destinations generally have lower RTTs than overseas ones; transoceanic links produce the largest hop-to-hop increases in traceroute. Wireless links and last-mile congestion raise jitter. Larger ICMP payloads may slightly increase RTT and variability due to serialization time and buffering.

---

<!-- page 17 mode: hybrid_paper -->

Time between SYN and SYN, ACK: 0.025380

Time between SYN, ACK and ACK: 0.000256

(Changed the time view as: Set View -> Time Display Format -> Seconds Since Previous Displayed Packet)

Final Observations:

### 1. Protocol mix & encryption. The capture shows a contemporary web stack where

1st Entry : SYN
2nd Entry: SYN, ACK
3rd Entry: ACK

![Figure 1 on Page 17](a001_assets/figures/a001_page_17_fig_1.png)

encryption and UDP-based transports are first-class: DNS to map names to IPs, then either TLS over TCP (HTTPS) or QUIC over UDP (HTTP/3). QUIC’s presence

---

<!-- page 18 mode: simple_text -->

under the generic udp filter explains why DNS and QUIC co-appear; protocol hierarchy confirms their relative shares.

### 2. Name resolution precedes data flows. For each site, DNS queries precede

connection establishment. Cached domains reduce or eliminate network DNS lookups. Where DNS is slow or fails, application flows stall, a reminder that name resolution is on the critical path.

### 3. Latency, jitter, and paths. Repeated 100-ping batches reveal that where the server is

(and when you measure) matters: nearby U.S. hosts exhibit low median RTTs and tight dispersion, while overseas hosts have higher medians with larger tails.

Traceroute highlights the longest link(s)-often a transoceanic or inter-regional backbone, and occasional path changes across runs.

### 4. TCP handshake timing. The SYN->SYN,ACK interval aligns with end-to-end RTT;

SYN,ACK->ACK is almost entirely host processing. ECN flags (ECE/CWR) may appear during handshake on networks that negotiate congestion-experienced signaling.

### 5. Practical analysis aids. Custom columns for ports and HTTP fields, plus simple

coloring rules, significantly speed up triage-particularly when QUIC, DNS, and TLS traffic interleave. Protocol Hierarchy and “Follow TCP Stream” provide fast summaries and per-flow clarity, respectively.

---