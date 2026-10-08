#!/bin/bash
# Compile and run the VisionAid FPGA testbench with Icarus Verilog (simulation only).
cd "$(dirname "$0")"
EDA=../../tools/eda.sh
mkdir -p sim
"$EDA" iverilog -g2012 -Wall -o sim/tb.vvp tb/tb_visionaid.v rtl/*.v && \
"$EDA" vvp -n sim/tb.vvp | tee sim/sim_results.log
