---
name: Competition rover control system
short: ROVER
org: Harvard Undergraduate Robotics Club
role: Software Team Lead · Electrical Team Co-Lead
period: Sep 2024 – Present
status: active
weight: 4
tags: [C++, ROS2, CANopen, Embedded Linux, Teensy, PCB design, Docker]
links:
  - Repository | https://github.com/BeckettOBrien/rover
cover: rover.jpeg
---

The compute, control, and electrical stack for a Mars-analog rover built for the
University Rover Challenge.

- Architected the rover's distributed compute over ROS2 and a CANopen motor network,
  spanning a Jetson, Teensy microcontrollers, and a ZED stereo camera.
- Wrote a cyclic synchronous position controller running a hard 1 kHz loop, with a
  custom Linux driver streaming interpolated setpoints over UART with message integrity
  checks and error recovery.
- Drive a 6-DOF arm through complex motion profiles with live sensor and motor feedback.
- Designed power distribution, sensor, and communication PCBs.
