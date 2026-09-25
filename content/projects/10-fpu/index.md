---
name: Reduced-precision floating-point units
short: FPU
org: Architecture, Circuits & Compilers Group, Harvard SEAS
role: Undergraduate Research Assistant
period: Jun 2026 – Present
status: active
weight: 5
tags: [SystemVerilog, Verilog, SystemC, cocotb, Vivado, Yosys, Catapult, Python]
---

Arithmetic hardware for edge AI inference, built across four number formats and
measured against each other for accuracy, area, timing, and power.

- Implemented FP16, BF16, NVFP4, and MXFP4 floating-point units in Verilog and
  SystemVerilog, with system-level models in SystemC, then quantified what each format
  actually costs in numerical error and PPA.
- Verify designs with cocotb testbenches against reference models; synthesize and
  deploy to FPGA in Vivado, and estimate ASIC characteristics with Yosys and Catapult.
- Selected units are targeted for tapeout in the lab's AI accelerator on a TSMC process.
- Also investigating agentic AI for hardware design, using LLM agents to generate and
  iterate on FPU RTL and benchmarking the results against hand-written implementations.
