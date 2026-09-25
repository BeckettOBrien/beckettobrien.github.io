---
name: RTL8139 driver and network stack
short: NIC
org: Chickadee teaching OS · Harvard CS 161
period:
status: shipped
weight: 4
tags: [C++, x86 assembly, Device drivers, Networking, Operating systems]
note: Source is private — course policy on publishing solutions. Happy to walk through the design.
---

A network interface driver written from scratch against the hardware registers, plus
the stack running on top of it.

- Wrote a driver for the RTL8139 NIC in C++ and x86 assembly for the Chickadee teaching
  operating system, working directly against the device's registers and DMA ring buffers.
- Implemented ARP and UDP on top of it, so the kernel could talk to a network it had no
  stack for.
